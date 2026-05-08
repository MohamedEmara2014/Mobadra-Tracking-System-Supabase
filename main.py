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

# --- 2. نظام تسجيل الدخول ---
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None
    st.session_state.user_section = None

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔐 نظام متابعة مشروعات المبادرة")
    with st.form("login_form"):
        pwd = st.text_input("أدخل كلمة المرور:", type="password")
        submit = st.form_submit_button("دخول")
        if submit:
            passwords = {
                "Admin38": "admin", "Exec123": "التنفيذ", "Time123": "الجدول الزمني",
                "Tech123": "المكتب الفني", "Lic123": "التراخيص", "Acc123": "الحسابات", 
                "Legal123": "الشئون القانونية", "Install123": "أقساط الجهاز", "Cust123": "خدمة العملاء"
            }
            if pwd in passwords:
                st.session_state.auth = True
                val = passwords[pwd]
                st.session_state.role = "admin" if val == "admin" else "staff"
                st.session_state.user_section = val if val != "admin" else None
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
else:
    st.set_page_config(page_title="نظام المبادرة", layout="wide")
    all_sections = ["التنفيذ", "الجدول الزمني", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز", "خدمة العملاء"]

    # خيارات الحالة مع الرموز
    TIME_STATUS_OPTIONS = ["✅ متوافق", "🚀 متقدم", "⚠️ متأخر"]

    # --- أ. واجهة المدير العام ---
    if st.session_state.role == "admin":
        st.title("📊 لوحة تحكم المدير العام")
        full_df = get_data_fresh()
        full_df = add_location_column(full_df)
        
        if not full_df.empty:
            tabs = st.tabs(all_sections + ["📋 التقرير المجمع"])
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    sec_data = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                    if not sec_data.empty:
                        sec_data["المشروع"] = sec_data["projects"].apply(lambda x: x["name"])
                        
                        if sec_name == "الحسابات":
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات القسم", "action_note": "توجيه الإدارة"}
                            cols = ["المشروع", "الموقع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد المتاح", "ملاحظات القسم", "توجيه الإدارة"]
                        elif sec_name == "الجدول الزمني":
                            map_dict = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات", "action_note": "توجيه الإدارة"}
                            cols = ["المشروع", "الموقع", "الربع", "الحالة بالنسبة للجدول الزمني", "أخر تصفية", "أخر مستخلص", "ملاحظات", "توجيه الإدارة"]
                        else:
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه الإدارة"}
                            cols = ["المشروع", "الموقع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه الإدارة"]
                        
                        display_df = sec_data.rename(columns=map_dict)[cols]
                        
                        st.data_editor(
                            display_df, 
                            column_config={
                                "المشروع": st.column_config.TextColumn(disabled=True, pinned=True),
                                "الموقع": st.column_config.TextColumn(disabled=True, pinned=True),
                                "الحالة بالنسبة للجدول الزمني": st.column_config.TextColumn(disabled=True),
                                "توجيه الإدارة": st.column_config.TextColumn("📝 إضافة توجيه", width="large")
                            }, 
                            hide_index=True, use_container_width=True, key=f"adm_ed_{sec_name}"
                        )
                        if st.button(f"💾 حفظ توجيهات {sec_name}", key=f"btn_{sec_name}"):
                            # منطق الحفظ...
                            pass

    # --- ب. واجهة الأقسام (الموظفين) ---
    else:
        sec = st.session_state.user_section
        st.title(f"🏗️ إدارة بيانات قسم: {sec}")
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", sec).order("project_id").execute()
        
        if res.data:
            db_df = pd.DataFrame(res.data)
            db_df = add_location_column(db_df)
            db_df["المشروع"] = db_df["projects"].apply(lambda x: x["name"])
            
            if sec == "الحسابات":
                map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه الإدارة"}
                cols = ["المشروع", "الموقع", "🚩 توجيه الإدارة", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد المتاح", "ملاحظات القسم"]
            elif sec == "الجدول الزمني":
                map_dict = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات", "action_note": "🚩 توجيه الإدارة"}
                cols = ["المشروع", "الموقع", "🚩 توجيه الإدارة", "الربع", "الحالة بالنسبة للجدول الزمني", "أخر تصفية", "أخر مستخلص", "ملاحظات"]
            else:
                map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه الإدارة"}
                cols = ["المشروع", "الموقع", "🚩 توجيه الإدارة", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم"]

            display_df = db_df.rename(columns=map_dict)[cols]
            
            edited_staff = st.data_editor(
                display_df, 
                column_config={
                    "المشروع": st.column_config.TextColumn(disabled=True, pinned=True),
                    "الموقع": st.column_config.TextColumn(disabled=True, pinned=True),
                    "🚩 توجيه الإدارة": st.column_config.TextColumn(disabled=True, width="large"),
                    "الحالة بالنسبة للجدول الزمني": st.column_config.SelectboxColumn(
                        "الحالة بالنسبة للجدول الزمني", 
                        options=TIME_STATUS_OPTIONS,
                        required=True
                    ) if sec == "الجدول الزمني" else None,
                }, 
                hide_index=True, use_container_width=True, key="staff_editor"
            )

            if st.button("🚀 حفظ البيانات", type="primary", use_container_width=True):
                updates = []
                now = datetime.now().isoformat()
                for idx in range(len(edited_staff)):
                    row = edited_staff.iloc[idx]
                    updates.append({
                        "id": int(db_df.iloc[idx]["id"]),
                        "col1": str(row.get(map_dict.get("col1", ""), "")),
                        "col2": str(row.get(map_dict.get("col2", ""), "")),
                        "col3": str(row.get(map_dict.get("col3", ""), "")),
                        "col4": str(row.get(map_dict.get("col4", ""), "")),
                        "col5": str(row.get(map_dict.get("col5", ""), "")),
                        "comment": str(row.get(map_dict.get("comment", ""), "")),
                        "updated_at": now
                    })
                try:
                    supabase.table("project_data").upsert(updates).execute()
                    st.success("✅ تم التحديث بنجاح"); st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
