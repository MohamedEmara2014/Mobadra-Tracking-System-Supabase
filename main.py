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
        mode = st.sidebar.radio("🎮 لوحة التحكم:", ["التقرير المجمع وتوجيهات المدير", "تحديث بيانات الأقسام"])
        
        if mode == "التقرير المجمع وتوجيهات المدير":
            st.title("📊 التقرير المجمع الشامل")
            full_df = get_data()
            if not full_df.empty:
                tabs = st.tabs(all_sections + ["📋 الجدول المجمع"])
                for i, sec in enumerate(all_sections):
                    with tabs[i]:
                        sec_df = full_df[full_df["section_name"] == sec].copy().sort_values("project_id")
                        sec_df["المشروع"] = sec_df["projects"].apply(lambda x: x["name"])
                        
                        # مسميات الأعمدة
                        if sec == "الحسابات":
                            cols = ["المشروع", "col1", "col2", "col3", "col4", "col5", "comment", "action_note"]
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                        else:
                            cols = ["المشروع", "col1", "col2", "col3", "comment", "action_note"]
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                        
                        # محرر التوجيهات للمدير
                        st.subheader(f"توجيهات قسم {sec}")
                        edited_adm = st.data_editor(sec_df[cols].rename(columns=map_dict), 
                                                    column_config={"المشروع": st.column_config.TextColumn(disabled=True),
                                                                   "توجيه المدير": st.column_config.TextColumn("توجيه المدير", width="large")},
                                                    hide_index=True, key=f"adm_ed_{sec}")
                        
                        if st.button(f"💾 حفظ توجيهات {sec}", key=f"btn_adm_{sec}"):
                            updates = [{"id": sec_df.iloc[idx]["id"], "action_note": str(edited_adm.iloc[idx]["توجيه المدير"])} for idx in range(len(edited_adm))]
                            supabase.table("project_data").upsert(updates).execute()
                            st.success("✅ تم الحفظ")
                            st.rerun()

                with tabs[-1]:
                    st.subheader("📋 ملخص المشروع بالكامل")
                    full_df_up = get_data()
                    p_names = sorted(full_df_up["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]))
                    pano_list = []
                    for p_name in p_names:
                        row = {"المشروع": p_name}
                        for s in all_sections:
                            r = full_df_up[(full_df_up["projects"].apply(lambda x: x["name"]) == p_name) & (full_df_up["section_name"] == s)]
                            if not r.empty:
                                row[f"{s}: إنجاز/وارد"] = r.iloc[0]["col1"]
                                row[f"{s}: حالة/رصيد"] = r.iloc[0]["col3"] if s != "الحسابات" else r.iloc[0]["col5"]
                        pano_list.append(row)
                    summary_df = pd.DataFrame(pano_list)
                    st.dataframe(summary_df, hide_index=True, use_container_width=True)
                    
                    if st.button("📂 تجهيز ملف إكسيل للمشروع كاملاً"):
                        buf = io.BytesIO()
                        summary_df.to_excel(buf, index=False)
                        st.download_button("📥 تحميل الإكسيل المجمع", buf.getvalue(), "المبادرة_المجمع.xlsx")

        elif mode == "تحديث بيانات الأقسام":
            st.title("🛠️ تعديل بيانات الأقسام (صلاحية المدير)")
            selected_sec = st.sidebar.selectbox("اختر القسم:", all_sections)
            # نفس منطق تعديل الموظف المذكور أدناه ولكن للمدير

    # --- ب. واجهة الأقسام (Staff) ---
    else:
        sec = st.session_state.user_section
        st.title(f"🏗️ قسم: {sec}")
        
        # جلب بيانات القسم فقط
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", sec).order("project_id").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df["المشروع"] = df["projects"].apply(lambda x: x["name"])
            
            if sec == "الحسابات":
                cols = ["المشروع", "action_note", "col1", "col2", "col3", "col4", "col5", "comment"]
                map_dict = {"action_note": "🚩 توجيه المدير", "col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم"}
            else:
                cols = ["المشروع", "action_note", "col1", "col2", "col3", "comment"]
                map_dict = {"action_note": "🚩 توجيه المدير", "col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم"}
            
            st.subheader(f"تحديث جدول بيانات {sec}")
            # محرر الموظف
            staff_ed = st.data_editor(df[cols].rename(columns=map_dict),
                                      column_config={"المشروع": st.column_config.TextColumn(disabled=True),
                                                     "🚩 توجيه المدير": st.column_config.TextColumn(disabled=True),
                                                     "حالة المشروع": st.column_config.SelectboxColumn("حالة المشروع", options=["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]) if sec != "الحسابات" else None},
                                      hide_index=True, use_container_width=True)

            # أزرار الحفظ والتحميل
            col_save, col_ex = st.columns(2)
            with col_save:
                if st.button(f"🚀 حفظ بيانات {sec}", type="primary", use_container_width=True):
                    updates = []
                    for idx in range(len(staff_ed)):
                        row = staff_ed.iloc[idx]
                        payload = {"id": df.iloc[idx]["id"],
                                   "col1": str(row.get(map_dict["col1"], "")),
                                   "col2": str(row.get(map_dict["col2"], "")),
                                   "col3": str(row.get(map_dict["col3"], "")),
                                   "comment": str(row.get(map_dict["comment"], ""))}
                        if sec == "الحسابات":
                            payload.update({"col4": str(row.get(map_dict["col4"], "")), "col5": str(row.get(map_dict["col5"], ""))})
                        updates.append(payload)
                    supabase.table("project_data").upsert(updates).execute()
                    st.success("✅ تم تحديث بيانات القسم بنجاح")
                    st.toast("تم الحفظ!")

            with col_ex:
                if st.button(f"📂 تجهيز إكسيل للقسم", use_container_width=True):
                    buf = io.BytesIO()
                    staff_ed.to_excel(buf, index=False)
                    st.download_button(f"📥 تحميل ملف {sec}", buf.getvalue(), f"{sec}.xlsx", use_container_width=True)

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
