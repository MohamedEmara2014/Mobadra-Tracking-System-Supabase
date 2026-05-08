import streamlit as st
import pandas as pd
from supabase import create_client
import io
from datetime import datetime

# --- 1. إعدادات الاتصال وقاعدة البيانات ---
SUPABASE_URL = "https://rsyyhhpjnzkgnhzuekij.supabase.co"
SUPABASE_KEY = "sb_publishable_RwP_c4ZDnF0rOuY3y33sdw_NyyZAfZt"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def get_data_fresh():
    try:
        res = supabase.table("project_data").select("*, projects(name)").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"خطأ في جلب البيانات: {e}")
        return pd.DataFrame()

PROJECT_LOCATIONS = [
    "الشروق", "الشروق", "العبور", "القاهرة الجديدة (بيت الوطن)", "النرجس الجديدة", 
    "بدر", "العاشر", "العاشر", "شمال الرحاب", "شمال الرحاب", "النرجس الجديدة", 
    "النورس هاوس", "شمال الرحاب", "القاهرة الجديدة (بيت الوطن)", "العاشر", 
    "العبور الجديدة", "شمال الرحاب", "النورس هاوس", "النرجس الجديدة", 
    "القاهرة الجديدة (بيت الوطن)", "العاشر", "هليوبوليس الجديدة", "الزقازيق", 
    "الزقازيق", "هليوبوليس الجديدة", "الأوركيد", "الزقازيق", "العاشر", 
    "شمال الرحاب", "القاهرة الجديدة (بيت الوطن)", "العاشر", "العبور الجديدة", 
    "العبور الجديدة", "الزقازيق", "هليوبوليس الجديدة", "الزقازيق", 
    "هليوبوليس الجديدة", "هليوبوليس الجديدة"
]

def add_location_column(df):
    if not df.empty and 'project_id' in df.columns:
        df['الموقع'] = df['project_id'].apply(
            lambda x: PROJECT_LOCATIONS[int(x)-1] if 0 < int(x) <= len(PROJECT_LOCATIONS) else "غير محدد"
        )
    return df

def get_mapped_df_for_summary(df, sec_name):
    if sec_name == "الحسابات":
        m = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات الحسابات"}
    elif sec_name == "الجدول الزمني":
        m = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات الجدول"}
    elif sec_name == "أقساط الجهاز":
        m = {"col1": "اخر قسط تم دفعه", "col2": "القسط التالي", "comment": "ملاحظات الأقساط"}
    else:
        m = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": f"ملاحظات {sec_name}"}
    
    available_cols = ["project_id"]
    rename_dict = {}
    for db_col, target_name in m.items():
        if db_col in df.columns:
            available_cols.append(db_col)
            rename_dict[db_col] = target_name
    if "action_note" in df.columns:
        available_cols.append("action_note"); rename_dict["action_note"] = f"توجيه {sec_name}"
    return df[available_cols].copy().rename(columns=rename_dict)

# --- 2. نظام تسجيل الدخول ---
if "auth" not in st.session_state:
    st.session_state.auth, st.session_state.role, st.session_state.user_section = False, None, None

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔐 نظام متابعة مشروعات المبادرة")
    with st.form("login_form"):
        pwd = st.text_input("أدخل كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            passwords = {"Admin38": "admin", "Exec123": "التنفيذ", "Time123": "الجدول الزمني", "Tech123": "المكتب الفني", "Lic123": "التراخيص", "Acc123": "الحسابات", "Legal123": "الشئون القانونية", "Install123": "أقساط الجهاز", "Cust123": "خدمة العملاء"}
            if pwd in passwords:
                st.session_state.auth, val = True, passwords[pwd]
                st.session_state.role = "admin" if val == "admin" else "staff"
                st.session_state.user_section = val if val != "admin" else None
                st.rerun()
            else: st.error("❌ كلمة المرور غير صحيحة")
else:
    st.set_page_config(page_title="نظام المبادرة", layout="wide")
    all_sections = ["التنفيذ", "الجدول الزمني", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز", "خدمة العملاء"]
    sec_emojis = {"التنفيذ": "🏗️", "الجدول الزمني": "📅", "المكتب الفني": "📐", "التراخيص": "📜", "الحسابات": "💰", "الشئون القانونية": "⚖️", "أقساط الجهاز": "📠", "خدمة العملاء": "🤝"}
    TIME_STATUS_OPTIONS = ["✅ متوافق", "🚀 متقدم", "⚠️ متأخر"]

    if st.session_state.role == "admin":
        st.title("📊 لوحة تحكم المدير العام")
        full_df = add_location_column(get_data_fresh())
        if not full_df.empty:
            full_df['updated_at'] = pd.to_datetime(full_df['updated_at'])
            full_df["المشروع"] = full_df["projects"].apply(lambda x: x["name"] if x else "غير معروف")
            tabs = st.tabs(all_sections + ["📋 التقرير المجمع الشامل"])
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    sec_data = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                    if not sec_data.empty:
                        st.info(f"🕒 آخر تحديث لهذا القسم: {sec_data['updated_at'].max().strftime('%Y-%m-%d | %I:%M %p')}")
                        if sec_name == "الحسابات": m_dict, cols = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات القسم", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد المتاح", "ملاحظات القسم", "توجيه الإدارة"]
                        elif sec_name == "الجدول الزمني": m_dict, cols = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "الربع", "الحالة بالنسبة للجدول الزمني", "أخر تصفية", "أخر مستخلص", "ملاحظات", "توجيه الإدارة"]
                        elif sec_name == "أقساط الجهاز": m_dict, cols = {"col1": "اخر قسط تم دفعه", "col2": "القسط التالي", "comment": "ملاحظات", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "اخر قسط تم دفعه", "القسط التالي", "ملاحظات", "توجيه الإدارة"]
                        else: m_dict, cols = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه الإدارة"]
                        st.data_editor(sec_data.rename(columns=m_dict)[cols], column_config={"المشروع": st.column_config.TextColumn(disabled=True, pinned=True), "الموقع": st.column_config.TextColumn(disabled=True, pinned=True)}, hide_index=True, use_container_width=True, key=f"adm_{sec_name}")

            with tabs[-1]:
                projects_base = full_df[["project_id", "المشروع", "الموقع"]].drop_duplicates().sort_values("project_id")
                combined_final = projects_base.copy()
                for s_name in all_sections:
                    sec_subset = full_df[full_df["section_name"] == s_name]
                    if not sec_subset.empty:
                        mapped = get_mapped_df_for_summary(sec_subset, s_name)
                        new_cols = {c: f"{sec_emojis.get(s_name, '')} {c}" for c in mapped.columns if c != "project_id"}
                        combined_final = pd.merge(combined_final, mapped.rename(columns=new_cols), on="project_id", how="left")
                st.data_editor(combined_final.drop(columns=["project_id"]), column_config={"المشروع": st.column_config.TextColumn(pinned=True), "الموقع": st.column_config.TextColumn(pinned=True)}, disabled=True, hide_index=True)

    else:
        sec = st.session_state.user_section
        st.title(f"{sec_emojis.get(sec, '🏗️')} إدارة بيانات قسم: {sec}")
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", sec).order("project_id").execute()
        if res.data:
            db_df = add_location_column(pd.DataFrame(res.data))
            db_df["المشروع"] = db_df["projects"].apply(lambda x: x["name"])
            
            if sec == "الحسابات": m_dict, cols = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه الإدارة"}, ["المشروع", "الموقع", "🚩 توجيه الإدارة", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد المتاح", "ملاحظات القسم"]
            elif sec == "الجدول الزمني": m_dict, cols = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات", "action_note": "🚩 توجيه الإدارة"}, ["المشروع", "الموقع", "🚩 توجيه الإدارة", "الربع", "الحالة بالنسبة للجدول الزمني", "أخر تصفية", "أخر مستخلص", "ملاحظات"]
            elif sec == "أقساط الجهاز": m_dict, cols = {"col1": "اخر قسط تم دفعه", "col2": "القسط التالي", "comment": "ملاحظات", "action_note": "🚩 توجيه الإدارة"}, ["المشروع", "الموقع", "🚩 توجيه الإدارة", "اخر قسط تم دفعه", "القسط التالي", "ملاحظات"]
            else: m_dict, cols = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه الإدارة"}, ["المشروع", "الموقع", "🚩 توجيه الإدارة", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم"]

            edited_df = st.data_editor(db_df.rename(columns=m_dict)[cols], column_config={"المشروع": st.column_config.TextColumn(disabled=True, pinned=True), "الموقع": st.column_config.TextColumn(disabled=True, pinned=True), "🚩 توجيه الإدارة": st.column_config.TextColumn(disabled=True), "الحالة بالنسبة للجدول الزمني": st.column_config.SelectboxColumn("الحالة بالنسبة للجدول الزمني", options=TIME_STATUS_OPTIONS)}, hide_index=True, use_container_width=True)
            
            if st.button("🚀 حفظ التعديلات", type="primary", use_container_width=True):
                updates, now = [], datetime.now().isoformat()
                for idx in range(len(edited_df)):
                    row = edited_df.iloc[idx]
                    updates.append({"id": int(db_df.iloc[idx]["id"]), "col1": str(row.get(m_dict.get("col1"), "")), "col2": str(row.get(m_dict.get("col2"), "")), "col3": str(row.get(m_dict.get("col3"), "")), "col4": str(row.get(m_dict.get("col4"), "")), "col5": str(row.get(m_dict.get("col5"), "")), "comment": str(row.get(m_dict.get("comment"), "")), "updated_at": now})
                supabase.table("project_data").upsert(updates).execute()
                st.success("✅ تم حفظ البيانات بنجاح وتحديث تاريخ التحديث للمدير."); st.rerun()

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
