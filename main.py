import streamlit as st
import pandas as pd
from supabase import create_client
import io

# --- 1. الإعدادات والاتصال ---
SUPABASE_URL = "https://rsyyhhpjnzkgnhzuekij.supabase.co"
SUPABASE_KEY = "sb_publishable_RwP_c4ZDnF0rOuY3y33sdw_NyyZAfZt"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def get_data():
    res = supabase.table("project_data").select("*, projects(name)").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- 2. إدارة الجلسة والدخول ---
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None
    st.session_state.user_section = None

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔐 نظام متابعة مشروعات المبادرة (38 اتحاد)")
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
        mode = st.sidebar.radio("🎮 لوحة التحكم:", ["التقرير المجمع الشامل", "تحديث بيانات الأقسام"])
        
        if mode == "التقرير المجمع الشامل":
            st.title("📊 التقرير المجمع وتوجيهات المدير")
            full_df = get_data()
            if not full_df.empty:
                tabs = st.tabs(all_sections + ["📋 الجدول المجمع"])
                for i, sec_name in enumerate(all_sections):
                    with tabs[i]:
                        sec_df = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                        sec_df["المشروع"] = sec_df["projects"].apply(lambda x: x["name"])
                        
                        # مسميات الأعمدة الموحدة
                        if sec_name == "الحسابات":
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        display_df = sec_df.rename(columns=map_dict)
                        st.subheader(f"توجيهات قسم {sec_name}")
                        edited_adm = st.data_editor(display_df[cols], column_config={"المشروع": st.column_config.TextColumn(disabled=True), "توجيه المدير": st.column_config.TextColumn("📝 توجيه المدير", width="large")}, hide_index=True, key=f"adm_ed_{sec_name}")
                        
                        if st.button(f"💾 حفظ توجيهات {sec_name}", key=f"btn_adm_{sec_name}"):
                            updates = [{"id": sec_df.iloc[idx]["id"], "action_note": str(edited_adm.iloc[idx]["توجيه المدير"])} for idx in range(len(edited_adm))]
                            supabase.table("project_data").upsert(updates).execute()
                            st.success(f"✅ تم إرسال التوجيهات لقسم {sec_name}")
                            st.rerun()

                with tabs[-1]:
                    st.subheader("📋 الجدول المجمع لـ 38 اتحاد")
                    # عرض الجدول المجمع (نفس منطق التجميع السابق)
                    # ...

    # --- ب. واجهة الأقسام (Staff) ---
    else:
        sec = st.session_state.user_section
        st.title(f"🏗️ إدارة بيانات قسم: {sec}")
        
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", sec).order("project_id").execute()
        if res.data:
            db_df = pd.DataFrame(res.data)
            db_df["المشروع"] = db_df["projects"].apply(lambda x: x["name"])
            
            # مسميات الأعمدة الموحدة (يجب أن تتطابق مع المدير)
            if sec == "الحسابات":
                map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه المدير"}
                cols = ["المشروع", "🚩 توجيه المدير", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم"]
            else:
                map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "🚩 توجيه المدير"}
                cols = ["المشروع", "🚩 توجيه المدير", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم"]

            display_df = db_df.rename(columns=map_dict)[cols]

            # 1. خيار رفع الإكسيل
            st.info("💡 يمكنك ملء الجدول يدوياً أو رفع ملف إكسيل تم ملؤه مسبقاً بنفس أسماء الأعمدة.")
            uploaded_file = st.file_uploader("📂 ارفع ملف إكسيل لتعبئة الجدول تلقائياً:", type=["xlsx"])
            
            if uploaded_file:
                up_df = pd.read_excel(uploaded_file)
                for c in display_df.columns:
                    if c in up_df.columns and c not in ["المشروع", "🚩 توجيه المدير"]:
                        display_df[c] = up_df[c].values[:len(display_df)]
                st.success("✅ تم استيراد البيانات من الملف")

            # 2. محرر البيانات
            edited_staff = st.data_editor(
                display_df,
                column_config={
                    "المشروع": st.column_config.TextColumn(disabled=True),
                    "🚩 توجيه المدير": st.column_config.TextColumn(disabled=True),
                    "حالة المشروع": st.column_config.SelectboxColumn("حالة المشروع", options=["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]) if sec != "الحسابات" else None
                },
                hide_index=True, use_container_width=True, key=f"staff_editor_{sec}"
            )

            # 3. أزرار الحفظ والتحميل
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 حفظ واعتماد البيانات", type="primary", use_container_width=True):
                    updates = []
                    for idx in range(len(edited_staff)):
                        row = edited_staff.iloc[idx]
                        payload = {
                            "id": db_df.iloc[idx]["id"],
                            "col1": str(row.get(map_dict["col1"], "")),
                            "col2": str(row.get(map_dict["col2"], "")),
                            "col3": str(row.get(map_dict["col3"], "")),
                            "comment": str(row.get(map_dict["comment"], ""))
                        }
                        if sec == "الحسابات":
                            payload.update({"col4": str(row.get("صادر التنفيذ", "")), "col5": str(row.get("الرصيد", ""))})
                        updates.append(payload)
                    supabase.table("project_data").upsert(updates).execute()
                    st.success("✅ تم تحديث قاعدة البيانات بنجاح")
                    st.balloons()

            with c2:
                buf = io.BytesIO()
                edited_staff.to_excel(buf, index=False)
                st.download_button("📂 تحميل نموذج القسم (Excel)", buf.getvalue(), f"نموذج_{sec}.xlsx", use_container_width=True)

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
