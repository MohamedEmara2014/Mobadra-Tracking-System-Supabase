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

# دالة جلب البيانات مع ضمان التحديث المستمر
def get_fresh_data():
    res = supabase.table("project_data").select("*, projects(name)").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- 2. نظام الدخول ---
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
                st.session_state.role = "admin" if passwords[pwd] == "admin" else "staff"
                st.session_state.user_section = passwords[pwd] if passwords[pwd] != "admin" else None
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
else:
    st.set_page_config(page_title="نظام المبادرة", layout="wide")
    all_sections = ["التنفيذ", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز"]

    # --- أ. واجهة المدير (Admin) ---
    if st.session_state.role == "admin":
        st.sidebar.title("🎮 لوحة المدير")
        mode = st.sidebar.radio("اختر العرض:", ["التقرير المجمع وتوجيهات المدير"])
        
        st.title("📊 التقرير المجمع وتوجيهات المدير")
        full_df = get_fresh_data()
        
        if not full_df.empty:
            # حل مشكلة عدم ظهور التبويبات أو البيانات للمدير
            tabs = st.tabs(all_sections + ["📋 الجدول المجمع"])
            
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    st.subheader(f"بيانات قسم {sec_name}")
                    sec_data = full_df[full_df["section_name"] == sec_name].copy()
                    if not sec_data.empty:
                        sec_data["المشروع"] = sec_data["projects"].apply(lambda x: x["name"])
                        
                        # توحيد المسميات
                        if sec_name == "الحسابات":
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        display_df = sec_data.rename(columns=map_dict)[cols]
                        
                        # محرر التوجيهات
                        edited_adm = st.data_editor(display_df, column_config={"المشروع": st.column_config.TextColumn(disabled=True), "توجيه المدير": st.column_config.TextColumn("📝 اكتب التوجيه هنا", width="large")}, hide_index=True, key=f"adm_edit_{sec_name}")
                        
                        if st.button(f"💾 حفظ توجيهات {sec_name}", key=f"btn_adm_{sec_name}"):
                            updates = [{"id": sec_data.iloc[idx]["id"], "action_note": str(edited_adm.iloc[idx]["توجيه المدير"])} for idx in range(len(edited_adm))]
                            supabase.table("project_data").upsert(updates).execute()
                            st.success(f"✅ تم حفظ توجيهات {sec_name}")
                            st.rerun()
                    else:
                        st.info(f"لا توجد بيانات حالية لقسم {sec_name}")

            # التبويب الأخير: الجدول المجمع (حل مشكلة عدم الظهور)
            with tabs[-1]:
                st.subheader("📋 الجدول المجمع الشامل لـ 38 اتحاد")
                p_names = sorted(full_df["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]))
                pano_list = []
                for p_name in p_names:
                    row = {"المشروع": p_name}
                    for s in all_sections:
                        r = full_df[(full_df["projects"].apply(lambda x: x["name"]) == p_name) & (full_df["section_name"] == s)]
                        if not r.empty:
                            row[f"{s}: إنجاز/وارد"] = r.iloc[0]["col1"]
                            row[f"{s}: حالة/رصيد"] = r.iloc[0]["col3"] if s != "الحسابات" else r.iloc[0]["col5"]
                    pano_list.append(row)
                
                summary_df = pd.DataFrame(pano_list)
                st.dataframe(summary_df, hide_index=True, use_container_width=True)
                
                # زر التحميل
                buf = io.BytesIO()
                summary_df.to_excel(buf, index=False)
                st.download_button("📥 تحميل الجدول المجمع (Excel)", buf.getvalue(), "المجمع_الشامل.xlsx", type="primary")

    # --- ب. واجهة الأقسام (Staff) ---
    else:
        sec = st.session_state.user_section
        st.title(f"🏗️ إدارة بيانات قسم: {sec}")
        
        # جلب البيانات لملء الجدول الابتدائي
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

            # --- ميزة تحميل إكسيل فارغ وإعادة رفعه ---
            st.markdown("### 📑 تحديث البيانات عبر الإكسيل")
            c1, c2 = st.columns(2)
            with c1:
                # تحميل الملف الحالي كنموذج
                template_buf = io.BytesIO()
                display_df.to_excel(template_buf, index=False)
                st.download_button("📥 1. تحميل نموذج القسم (فارغ/حالي)", template_buf.getvalue(), f"نموذج_{sec}.xlsx", help="قم بتحميل هذا الملف وملئه ثم ارفعه مجدداً")
            
            with c2:
                uploaded_file = st.file_uploader("📤 2. ارفع الملف بعد ملئه:", type=["xlsx"])
                if uploaded_file:
                    up_df = pd.read_excel(uploaded_file)
                    # مطابقة الأعمدة لتعبئة الجدول تلقائياً
                    for c in display_df.columns:
                        if c in up_df.columns and c not in ["المشروع", "🚩 توجيه المدير"]:
                            display_df[c] = up_df[c].values[:len(display_df)]
                    st.success("✅ تم تحديث الجدول أدناه من الملف المرفوع. يرجى الضغط على حفظ.")

            st.divider()
            
            # محرر البيانات اليدوي
            st.subheader("📝 مراجعة وتعديل البيانات")
            edited_staff = st.data_editor(display_df, column_config={"المشروع": st.column_config.TextColumn(disabled=True), "🚩 توجيه المدير": st.column_config.TextColumn(disabled=True)}, hide_index=True, use_container_width=True, key=f"staff_ed_{sec}")

            if st.button("🚀 حفظ البيانات النهائية في النظام", type="primary"):
                updates = []
                for idx in range(len(edited_staff)):
                    row = edited_staff.iloc[idx]
                    payload = {"id": db_df.iloc[idx]["id"],
                               "col1": str(row.get(map_dict["col1"], "")),
                               "col2": str(row.get(map_dict["col2"], "")),
                               "col3": str(row.get(map_dict["col3"], "")),
                               "comment": str(row.get(map_dict["comment"], ""))}
                    if sec == "الحسابات":
                        payload.update({"col4": str(row.get("صادر التنفيذ", "")), "col5": str(row.get("الرصيد", ""))})
                    updates.append(payload)
                supabase.table("project_data").upsert(updates).execute()
                st.success("✅ تم حفظ البيانات بنجاح!")
                st.rerun()

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
