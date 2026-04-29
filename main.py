import streamlit as st
import pandas as pd
from supabase import create_client
import io
from openpyxl import Workbook

# --- 1. الإعدادات والاتصال ---
SUPABASE_URL = "https://rsyyhhpjnzkgnhzuekij.supabase.co"
SUPABASE_KEY = "sb_publishable_RwP_c4ZDnF0rOuY3y33sdw_NyyZAfZt"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- 2. إدارة الجلسة والدخول ---
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔐 نظام متابعة مشروعات المبادرة")
    with st.form("login_form"):
        pwd = st.text_input("أدخل كلمة المرور:", type="password")
        submit = st.form_submit_button("دخول")
        if submit:
            if pwd == "Admin38": 
                st.session_state.auth = True
                st.session_state.role = "admin"
                st.rerun()
            elif pwd == "Staff123": 
                st.session_state.auth = True
                st.session_state.role = "staff"
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
else:
    st.set_page_config(page_title="نظام المبادرة المطور", layout="wide")
    sections = ["التنفيذ", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز"]

    if st.session_state.role == "admin":
        mode = st.sidebar.radio("🎮 لوحة التحكم الإدارية:", ["التقرير المجمع الشامل", "تحديث بيانات الأقسام"])
    else:
        mode = "تحديث بيانات الأقسام"

    # --- 3. وضع تحديث البيانات (رؤساء الأقسام) ---
    if mode == "تحديث بيانات الأقسام":
        st.title("🏗️ تحديث بيانات الأقسام")
        selected_section = st.sidebar.selectbox("اختر القسم المختص:", sections)
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

            with st.sidebar:
                st.divider()
                if st.button("📊 تجهيز ملف إكسيل للتحميل"):
                    tmp_df = df[display_cols].rename(columns=mapper)
                    export_buffer = io.BytesIO()
                    tmp_df.to_excel(export_buffer, index=False)
                    st.download_button("✅ تأكيد وتحميل الملف", export_buffer.getvalue(), f"{selected_section}.xlsx")

            st.subheader(f"📍 سجل بيانات: {selected_section}")
            config = {
                "المشروع": st.column_config.TextColumn("المشروع", disabled=True),
                "action_note": st.column_config.TextColumn("🚩 توجيهات الإدارة", disabled=True),
                "col1": mapper.get("col1"), "col2": mapper.get("col2"),
                "col3": st.column_config.SelectboxColumn(mapper.get("col3"), options=["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]) if selected_section != "الحسابات" else mapper.get("col3"),
                "col4": mapper.get("col4"), "col5": mapper.get("col5"), "comment": mapper.get("comment")
            }
            edited_df = st.data_editor(df[display_cols], column_config=config, hide_index=True, use_container_width=True)

            if st.button(f"🚀 حفظ بيانات {selected_section}", type="primary"):
                updates = []
                for i, row in edited_df.iterrows():
                    p_id = int(df.iloc[i]["ID"])
                    payload = {"project_id": p_id, "section_name": selected_section, "col1": str(row.get("col1", "")), "col2": str(row.get("col2", "")), "col3": str(row.get("col3", "")), "comment": str(row.get("comment", ""))}
                    if selected_section == "الحسابات": payload.update({"col4": str(row.get("col4", "")), "col5": str(row.get("col5", ""))})
                    updates.append(payload)
                supabase.table("project_data").upsert(updates, on_conflict="project_id, section_name").execute()
                st.success("✅ تم الحفظ بنجاح")

    # --- 4. وضع التقرير المجمع (المدير) ---
    elif mode == "التقرير المجمع الشامل":
        st.title("📊 التقرير المجمع الشامل")
        all_res = supabase.table("project_data").select("*, projects(name)").execute()
        
        if all_res.data:
            full_df = pd.DataFrame(all_res.data)
            p_names = sorted(full_df["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]))
            tabs = st.tabs(sections + ["📋 الجدول المجمع"])
            
            # تبويبات الأقسام الفردية
            for i, sec in enumerate(sections):
                with tabs[i]:
                    sec_data = full_df[full_df["section_name"] == sec].copy().sort_values("project_id")
                    sec_data["المشروع"] = sec_data["projects"].apply(lambda x: x["name"])
                    
                    if sec == "الحسابات":
                        m_cols = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات", "action_note": "توجيه المدير"}
                        disp = ["المشروع", "col1", "col2", "col3", "col4", "col5", "comment", "action_note"]
                    else:
                        m_cols = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات", "action_note": "توجيه المدير"}
                        disp = ["المشروع", "col1", "col2", "col3", "comment", "action_note"]
                    
                    adm_edit = st.data_editor(sec_data[disp], column_config={k: v for k, v in m_cols.items()}, hide_index=True, key=f"ad_{sec}", use_container_width=True)
                    
                    if st.button(f"💾 حفظ توجيهات {sec}", key=f"btn_{sec}"):
                        updates = [{"id": sec_data.iloc[sec_data.index.get_loc(sec_data.index[idx])]["id"], "action_note": str(row["action_note"])} for idx, row in adm_edit.iterrows()]
                        supabase.table("project_data").upsert(updates).execute()
                        st.success(f"✅ تم الحفظ")

            # التبويب الأخير: الجدول المجمع
            with tabs[-1]:
                st.subheader("📊 ملخص كافة بيانات الأقسام")
                pano_list = []
                for p_name in p_names:
                    row = {"المشروع": p_name}
                    for sec in sections:
                        s_rec = full_df[(full_df["projects"].apply(lambda x: x["name"]) == p_name) & (full_df["section_name"] == sec)]
                        if not s_rec.empty:
                            r = s_rec.iloc[0]
                            if sec == "الحسابات":
                                row[f"{sec}: وارد عملاء"] = r["col1"]; row[f"{sec}: الرصيد"] = r["col5"]
                            else:
                                row[f"{sec}: انجاز"] = r["col1"]; row[f"{sec}: الحالة"] = r["col3"]
                    pano_list.append(row)
                
                pano_df = pd.DataFrame(pano_list)
                st.dataframe(pano_df, hide_index=True, use_container_width=True)
                
                st.divider()
                st.write("📂 **تصدير الجدول المجمع الحالي إلى إكسيل (للمدير فقط):**")
                
                # زر تجهيز التحميل اليدوي للجدول المجمع
                if st.button("📑 تجهيز ملف الجدول المجمع للتحميل"):
                    export_buffer = io.BytesIO()
                    pano_df.to_excel(export_buffer, index=False)
                    st.download_button(
                        label="📥 اضغط هنا لتأكيد تحميل الجدول المجمع",
                        data=export_buffer.getvalue(),
                        file_name="Global_Summary_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
