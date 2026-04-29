import streamlit as st
import pandas as pd
from supabase import create_client
import io

# --- 1. الاتصال بقاعدة البيانات ---
SUPABASE_URL = "https://rsyyhhpjnzkgnhzuekij.supabase.co"
SUPABASE_KEY = "sb_publishable_RwP_c4ZDnF0rOuY3y33sdw_NyyZAfZt"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def get_data_fresh():
    res = supabase.table("project_data").select("*, projects(name)").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- 2. إدارة الجلسة والدخول ---
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None
    st.session_state.user_section = None

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔐 نظام متابعة مشروعات المبادرة")
    with st.form("login_form"):
        pwd = st.text_input("أدخل كلمة المرور الخاصة بك:", type="password")
        submit = st.form_submit_button("دخول")
        if submit:
            passwords = {
                "Admin38": "admin", "Exec123": "التنفيذ", "Tech123": "المكتب الفني",
                "Lic123": "التراخيص", "Acc123": "الحسابات", "Legal123": "الشئون القانونية", "Install123": "أقساط الجهاز"
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
    all_sections = ["التنفيذ", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز"]

    # --- أ. واجهة المدير (Admin) ---
    if st.session_state.role == "admin":
        st.title("📊 لوحة تحكم المدير العام")
        full_df = get_data_fresh()
        if not full_df.empty:
            tabs = st.tabs(all_sections + ["📋 الجدول المجمع الشامل"])
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    sec_data = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                    if not sec_data.empty:
                        sec_data["المشروع"] = sec_data["projects"].apply(lambda x: x["name"])
                        if sec_name == "الحسابات":
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        display_df = sec_data.rename(columns=map_dict)[cols]
                        edited_adm = st.data_editor(display_df, column_config={"المشروع": st.column_config.TextColumn(disabled=True), "توجيه المدير": st.column_config.TextColumn("📝 التوجيه", width="large")}, hide_index=True, key=f"adm_ed_{sec_name}")
                        
                        if st.button(f"💾 حفظ توجيهات {sec_name}", key=f"btn_adm_{sec_name}"):
                            updates = [{"id": int(sec_data.iloc[idx]["id"]), "action_note": str(edited_adm.iloc[idx]["توجيه المدير"])} for idx in range(len(edited_adm))]
                            supabase.table("project_data").upsert(updates).execute()
                            st.success("✅ تم الحفظ")
                            st.rerun()
            with tabs[-1]:
                # كود الجدول المجمع كما في النسخ السابقة
                st.info("الجدول المجمع يتم إنشاؤه من بيانات الأقسام أعلاه.")

    # --- ب. واجهة الأقسام (Staff) - تم الإصلاح الجذري هنا ---
    else:
        sec = st.session_state.user_section
        st.title(f"🏗️ إدارة بيانات قسم: {sec}")
        
        # جلب بيانات هذا القسم تحديداً
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", sec).order("project_id").execute()
        
        if res.data:
            db_df = pd.DataFrame(res.data)
            db_df["المشروع"] = db_df["projects"].apply(lambda x: x["name"])
            
            if sec == "الحسابات":
                map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه المدير"}
                cols = ["المشروع", "🚩 توجيه المدير", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم"]
            else:
                map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه المدير"}
                cols = ["المشروع", "🚩 توجيه المدير", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم"]

            display_df = db_df.rename(columns=map_dict)[cols]

            # منطقة رفع وتحميل الإكسيل
            st.markdown("### 📑 تحديث عبر الإكسيل")
            col1, col2 = st.columns(2)
            with col1:
                buf = io.BytesIO()
                display_df.to_excel(buf, index=False)
                st.download_button("📥 تحميل نموذج القسم الحالي", buf.getvalue(), f"نموذج_{sec}.xlsx", use_container_width=True)
            with col2:
                uploaded = st.file_uploader("📤 ارفع الملف المعدل هنا:", type=["xlsx"])
                if uploaded:
                    up_df = pd.read_excel(uploaded)
                    for c in display_df.columns:
                        if c in up_df.columns and c not in ["المشروع", "🚩 توجيه المدير"]:
                            display_df[c] = up_df[c].values[:len(display_df)]
                    st.success("✅ تم تحديث الجدول بالأسفل من الملف المرفوع.")

            st.divider()

            # عرض الجدول للتعديل اليدوي أو المراجعة
            st.subheader("📝 مراجعة البيانات قبل الحفظ")
            edited_staff = st.data_editor(
                display_df,
                column_config={
                    "المشروع": st.column_config.TextColumn(disabled=True),
                    "🚩 توجيه المدير": st.column_config.TextColumn(disabled=True),
                    "حالة المشروع": st.column_config.SelectboxColumn("حالة المشروع", options=["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]) if sec != "الحسابات" else None
                },
                hide_index=True, use_container_width=True, key=f"staff_editor_final"
            )

            if st.button("🚀 حفظ البيانات النهائية", type="primary", use_container_width=True):
                updates = []
                for idx in range(len(edited_staff)):
                    row = edited_staff.iloc[idx]
                    up_data = {
                        "id": int(db_df.iloc[idx]["id"]),
                        "col1": str(row.get(map_dict["col1"], "")),
                        "col2": str(row.get(map_dict["col2"], "")),
                        "col3": str(row.get(map_dict["col3"], "")),
                        "comment": str(row.get(map_dict["comment"], ""))
                    }
                    if sec == "الحسابات":
                        up_data.update({"col4": str(row.get("صادر التنفيذ", "")), "col5": str(row.get("الرصيد", ""))})
                    updates.append(up_data)
                
                supabase.table("project_data").upsert(updates).execute()
                st.success("✅ تم الحفظ بنجاح!")
                st.rerun()
        else:
            st.error("⚠️ لم يتم العثور على بيانات لهذا القسم في قاعدة البيانات.")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
