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
    st.set_page_config(page_title="نظام المبادرة المطور", layout="wide")
    all_sections = ["التنفيذ", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز"]

    if st.session_state.role == "admin":
        mode = st.sidebar.radio("🎮 لوحة التحكم:", ["التقرير المجمع الشامل", "تحديث بيانات الأقسام"])
        
        if mode == "التقرير المجمع الشامل":
            st.title("📊 التقرير المجمع الشامل")
            full_df = get_data()
            
            if not full_df.empty:
                tabs = st.tabs(all_sections + ["📋 الجدول المجمع"])
                
                for i, sec in enumerate(all_sections):
                    with tabs[i]:
                        # تصفية البيانات للقسم الحالي
                        sec_df = full_df[full_df["section_name"] == sec].copy()
                        sec_df["المشروع"] = sec_df["projects"].apply(lambda x: x["name"])
                        
                        # إعادة تسمية الأعمدة حسب الاتفاق السابق
                        if sec == "الحسابات":
                            mapper = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            disp_cols = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            mapper = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            disp_cols = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        # تجهيز الجدول للعرض مع الحفاظ على عمود الـ ID مخفياً ولكن متاحاً
                        display_df = sec_df.rename(columns=mapper)
                        
                        st.subheader(f"توجيهات قسم {sec}")
                        
                        # محرّر البيانات
                        edited_output = st.data_editor(
                            display_df[disp_cols],
                            column_config={
                                "المشروع": st.column_config.TextColumn(disabled=True),
                                "توجيه المدير": st.column_config.TextColumn("📝 اكتب توجيه المدير هنا", width="large")
                            },
                            hide_index=True,
                            key=f"admin_ed_{sec}"
                        )
                        
                        if st.button(f"💾 حفظ توجيهات {sec}", key=f"btn_admin_{sec}"):
                            with st.spinner("جاري حفظ التوجيهات..."):
                                updates = []
                                # نستخدم الفهرس من display_df للوصول إلى ID الأصلي في sec_df
                                for idx in range(len(edited_output)):
                                    db_id = sec_df.iloc[idx]["id"]
                                    new_note = edited_output.iloc[idx]["توجيه المدير"]
                                    updates.append({"id": db_id, "action_note": str(new_note)})
                                
                                supabase.table("project_data").upsert(updates).execute()
                                st.success(f"✅ تم تحديث توجيهات قسم {sec} بنجاح!")
                                st.toast("تم إرسال التوجيهات")
                                st.rerun()
                                
                with tabs[-1]:
                    st.subheader("📊 ملخص كافة بيانات الأقسام")
                    full_df_up = get_data()
                    p_names = sorted(full_df_up["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]))
                    pano_list = []
                    for p_name in p_names:
                        row = {"المشروع": p_name}
                        for s in all_sections:
                            r_rec = full_df_up[(full_df_up["projects"].apply(lambda x: x["name"]) == p_name) & (full_df_up["section_name"] == s)]
                            if not r_rec.empty:
                                r = r_rec.iloc[0]
                                row[f"{s}: إنجاز/وارد"] = r["col1"]
                                row[f"{s}: حالة/رصيد"] = r["col3"] if s != "الحسابات" else r["col5"]
                        pano_list.append(row)
                    st.dataframe(pd.DataFrame(pano_list), hide_index=True, use_container_width=True)

    else:
        # واجهة الموظفين (رؤية قسمه فقط)
        selected_section = st.session_state.user_section
        st.title(f"🏗️ قسم: {selected_section}")
        
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", selected_section).order("project_id").execute()
        if res.data:
            df = pd.DataFrame([{
                "ID": r["project_id"], "المشروع": r["projects"]["name"],
                "col1": r["col1"] or "", "col2": r["col2"] or "", "col3": r["col3"] or "",
                "col4": r["col4"] or "", "col5": r["col5"] or "", 
                "comment": r["comment"] or "", "action_note": r["action_note"] or "لا توجد توجيهات"
            } for r in res.data])

            if selected_section == "الحسابات":
                mapper = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                display_cols = ["المشروع", "توجيه المدير", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم"]
            else:
                mapper = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                display_cols = ["المشروع", "توجيه المدير", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم"]

            st.subheader(f"📍 سجل بيانات: {selected_section}")
            config = {
                "المشروع": st.column_config.TextColumn("المشروع", disabled=True),
                "توجيه المدير": st.column_config.TextColumn("🚩 توجيهات الإدارة", disabled=True),
                "ما تم انجازه": st.column_config.TextColumn("ما تم انجازه"),
                "المعوقات والمشاكل": st.column_config.TextColumn("المعوقات والمشاكل"),
                "حالة المشروع": st.column_config.SelectboxColumn("حالة المشروع", options=["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]) if selected_section != "الحسابات" else None
            }
            
            # عرض وتعديل
            edited_staff = st.data_editor(df.rename(columns=mapper)[display_cols], column_config=config, hide_index=True, use_container_width=True)

            if st.button(f"🚀 حفظ بيانات {selected_section}", type="primary", use_container_width=True):
                with st.spinner("جاري الحفظ..."):
                    updates = []
                    for idx in range(len(edited_staff)):
                        p_id = int(df.iloc[idx]["ID"])
                        row = edited_staff.iloc[idx]
                        payload = {
                            "project_id": p_id, 
                            "section_name": selected_section,
                            "col1": str(row.get("ما تم انجازه" if selected_section != "الحسابات" else "وارد العملاء", "")),
                            "col2": str(row.get("المعوقات والمشاكل" if selected_section != "الحسابات" else "صادر العملاء", "")),
                            "col3": str(row.get("حالة المشروع" if selected_section != "الحسابات" else "وارد التنفيذ", "")),
                            "comment": str(row.get("ملاحظات القسم", ""))
                        }
                        if selected_section == "الحسابات":
                            payload.update({"col4": str(row.get("صادر التنفيذ", "")), "col5": str(row.get("الرصيد", ""))})
                        updates.append(payload)
                    supabase.table("project_data").upsert(updates, on_conflict="project_id, section_name").execute()
                    st.success("✅ تم تحديث بياناتك بنجاح")
                    st.toast("تم الحفظ")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
