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

# دالة جلب البيانات مع إلغاء التخزين المؤقت لضمان حداثة البيانات
def get_fresh_data():
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
                "Admin38": "admin",
                "Exec123": "التنفيذ", "Tech123": "المكتب الفني",
                "Lic123": "التراخيص", "Acc123": "الحسابات",
                "Legal123": "الشئون القانونية", "Install123": "أقساط الجهاز"
            }
            if pwd in passwords:
                val = passwords[pwd]
                st.session_state.auth = True
                st.session_state.role = "admin" if val == "admin" else "staff"
                st.session_state.user_section = val if val != "admin" else None
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
else:
    st.set_page_config(page_title="نظام المبادرة المطور", layout="wide")
    all_sections = ["التنفيذ", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز"]

    if st.session_state.role == "admin":
        mode = st.sidebar.radio("🎮 لوحة التحكم الإدارية:", ["التقرير المجمع الشامل", "تحديث بيانات الأقسام"])
        
        if mode == "التقرير المجمع الشامل":
            st.title("📊 التقرير المجمع الشامل")
            
            # جلب البيانات
            full_df = get_fresh_data()
            
            if not full_df.empty:
                p_names = sorted(full_df["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]))
                tabs = st.tabs(all_sections + ["📋 الجدول المجمع"])
                
                for i, sec in enumerate(all_sections):
                    with tabs[i]:
                        sec_df = full_df[full_df["section_name"] == sec].copy().sort_values("project_id")
                        sec_df["المشروع"] = sec_df["projects"].apply(lambda x: x["name"])
                        
                        # تحديد الأعمدة
                        if sec == "الحسابات":
                            m_cols = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات", "action_note": "توجيه المدير"}
                            disp = ["المشروع", "col1", "col2", "col3", "col4", "col5", "comment", "action_note"]
                        else:
                            m_cols = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات", "action_note": "توجيه المدير"}
                            disp = ["المشروع", "col1", "col2", "col3", "comment", "action_note"]
                        
                        # إعدادات الأعمدة: الكل معطل ماعدا التوجيه
                        column_config = {k: st.column_config.TextColumn(v, disabled=True) for k, v in m_cols.items()}
                        column_config["action_note"] = st.column_config.TextColumn("📝 اكتب توجيه المدير هنا", disabled=False)
                        
                        # محرّر البيانات
                        edited_data = st.data_editor(
                            sec_df[disp], 
                            column_config=column_config, 
                            hide_index=True, 
                            key=f"editor_{sec}", 
                            use_container_width=True
                        )
                        
                        # زر الحفظ
                        if st.button(f"💾 اعتماد وإرسال توجيهات قسم {sec}", key=f"save_{sec}", type="primary"):
                            updates = []
                            for idx, row in edited_data.iterrows():
                                # نستخدم المعرف الحقيقي من قاعدة البيانات
                                db_id = sec_df.iloc[idx]["id"]
                                updates.append({"id": db_id, "action_note": str(row["action_note"])})
                            
                            if updates:
                                with st.spinner("جاري إرسال التوجيهات..."):
                                    supabase.table("project_data").upsert(updates).execute()
                                    st.success(f"✅ تم تحديث توجيهات قسم {sec} بنجاح!")
                                    st.toast("تم الحفظ!", icon="✅")
                                    # تأخير بسيط ثم إعادة تحميل لتحديث الجداول
                                    st.rerun()

                with tabs[-1]:
                    st.subheader("📊 ملخص كافة بيانات الأقسام")
                    pano_list = []
                    for p_name in p_names:
                        row = {"المشروع": p_name}
                        for sec in all_sections:
                            s_rec = full_df[(full_df["projects"].apply(lambda x: x["name"]) == p_name) & (full_df["section_name"] == sec)]
                            if not s_rec.empty:
                                r = s_rec.iloc[0]
                                if sec == "الحسابات": row[f"{sec}: وارد"] = r["col1"]; row[f"{sec}: رصيد"] = r["col5"]
                                else: row[f"{sec}: إنجاز"] = r["col1"]; row[f"{sec}: حالة"] = r["col3"]
                        pano_list.append(row)
                    st.dataframe(pd.DataFrame(pano_list), hide_index=True, use_container_width=True)

        selected_section = st.sidebar.selectbox("اختر القسم:", all_sections) if mode == "تحديث بيانات الأقسام" else None
    
    else:
        # واجهة الموظف
        selected_section = st.session_state.user_section
        st.title(f"🏗️ قسم: {selected_section}")

    if selected_section:
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", selected_section).order("project_id").execute()
        if res.data:
            df = pd.DataFrame([{
                "ID": r["project_id"], "المشروع": r["projects"]["name"],
                "col1": r["col1"] or "", "col2": r["col2"] or "", "col3": r["col3"] or "",
                "col4": r["col4"] or "", "col5": r["col5"] or "", 
                "comment": r["comment"] or "", "action_note": r["action_note"] or "لا توجد توجيهات"
            } for r in res.data])

            if selected_section == "الحسابات":
                mapper = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم"}
                display_cols = ["المشروع", "action_note", "col1", "col2", "col3", "col4", "col5", "comment"]
            else:
                mapper = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم"}
                display_cols = ["المشروع", "action_note", "col1", "col2", "col3", "comment"]

            st.subheader(f"📍 سجل بيانات: {selected_section}")
            config = {
                "المشروع": st.column_config.TextColumn("المشروع", disabled=True),
                "action_note": st.column_config.TextColumn("🚩 توجيهات الإدارة", disabled=True),
                "col1": mapper.get("col1"), "col2": mapper.get("col2"),
                "col3": st.column_config.SelectboxColumn(mapper.get("col3"), options=["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]) if selected_section != "الحسابات" else mapper.get("col3"),
                "col4": mapper.get("col4"), "col5": mapper.get("col5"), "comment": mapper.get("comment")
            }
            edited_df = st.data_editor(df[display_cols], column_config=config, hide_index=True, use_container_width=True)

            if st.button(f"🚀 حفظ بيانات {selected_section}", type="primary", use_container_width=True):
                updates = []
                for i, row in edited_df.iterrows():
                    p_id = int(df.iloc[i]["ID"])
                    payload = {"project_id": p_id, "section_name": selected_section, "col1": str(row.get("col1", "")), "col2": str(row.get("col2", "")), "col3": str(row.get("col3", "")), "comment": str(row.get("comment", ""))}
                    if selected_section == "الحسابات": payload.update({"col4": str(row.get("col4", "")), "col5": str(row.get("col5", ""))})
                    updates.append(payload)
                supabase.table("project_data").upsert(updates, on_conflict="project_id, section_name").execute()
                st.success("✅ تم التحديث بنجاح")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
