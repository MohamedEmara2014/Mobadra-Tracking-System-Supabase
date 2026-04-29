import streamlit as st
import pandas as pd
from supabase import create_client
import io
from datetime import datetime

# --- 1. الاتصال بقاعدة البيانات ---
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

# --- 2. إدارة الجلسة ---
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

    # --- أ. واجهة المدير العام ---
    if st.session_state.role == "admin":
        st.title("📊 لوحة تحكم المدير العام")
        full_df = get_data_fresh()
        
        if not full_df.empty:
            if 'updated_at' in full_df.columns:
                full_df['updated_at_formatted'] = pd.to_datetime(full_df['updated_at']).dt.tz_convert('Asia/Riyadh').dt.strftime('%Y-%m-%d %I:%M %p')
            
            tabs = st.tabs(all_sections + ["📋 الجدول المجمع الشامل"])
            
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    sec_data = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                    if not sec_data.empty:
                        last_up = sec_data['updated_at_formatted'].iloc[0] if 'updated_at_formatted' in sec_data.columns else "غير مسجل"
                        st.markdown(f"### 📑 بيانات قسم {sec_name} <span style='font-size: 0.7em; color: #1E88E5;'> (آخر تحديث: {last_up})</span>", unsafe_allow_html=True)
                        
                        sec_data["المشروع"] = sec_data["projects"].apply(lambda x: x["name"])
                        
                        if sec_name == "الحسابات":
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        display_df = sec_data.rename(columns=map_dict)[cols]
                        edited_adm = st.data_editor(display_df, column_config={"المشروع": st.column_config.TextColumn(disabled=True), "توجيه المدير": st.column_config.TextColumn("📝 إضافة توجيه", width="large")}, hide_index=True, use_container_width=True, key=f"adm_ed_{sec_name}")
                        
                        if st.button(f"💾 حفظ توجيهات {sec_name}", key=f"btn_save_{sec_name}", type="primary"):
                            updates = [{"id": int(sec_data.iloc[idx]["id"]), "section_name": sec_name, "action_note": str(edited_adm.iloc[idx].get("توجيه المدير", ""))} for idx in range(len(edited_adm))]
                            try:
                                supabase.table("project_data").upsert(updates).execute()
                                st.success(f"✅ تم حفظ توجيهات قسم {sec_name}")
                                st.toast("تم الحفظ بنجاح")
                            except Exception as e:
                                st.error(f"خطأ في الحفظ: {e}")

            # --- التقرير المجمع الشامل (الأعمدة الكاملة) ---
            with tabs[-1]:
                st.subheader("📋 التقرير المجمع التفصيلي (كافة البيانات)")
                p_names = sorted(full_df["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]) if " " in x else 0)
                
                summary_rows = []
                for p in p_names:
                    row = {"المشروع": p}
                    for s in all_sections:
                        sub = full_df[(full_df["projects"].apply(lambda x: x["name"]) == p) & (full_df["section_name"] == s)]
                        if not sub.empty:
                            target = sub.iloc[0]
                            if s == "الحسابات":
                                row[f"{s}: وارد العملاء"] = target["col1"]
                                row[f"{s}: صادر العملاء"] = target["col2"]
                                row[f"{s}: وارد التنفيذ"] = target["col3"]
                                row[f"{s}: صادر التنفيذ"] = target["col4"]
                                row[f"{s}: الرصيد"] = target["col5"]
                            else:
                                row[f"{s}: ما تم إنجازه"] = target["col1"]
                                row[f"{s}: المعوقات"] = target["col2"]
                                row[f"{s}: الحالة"] = target["col3"]
                            
                            row[f"{s}: ملاحظات القسم"] = target["comment"]
                            row[f"{s}: توجيه المدير"] = target["action_note"]
                    summary_rows.append(row)
                
                final_summary_df = pd.DataFrame(summary_rows)
                st.dataframe(final_summary_df, hide_index=True, use_container_width=True)
                
                # زر التحميل
                buffer = io.BytesIO()
                final_summary_df.to_excel(buffer, index=False)
                st.download_button(
                    label="📥 تحميل التقرير المجمع الشامل (Excel)",
                    data=buffer.getvalue(),
                    file_name=f"التقرير_المجمع_الشامل_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                    mime="application/vnd.ms-excel",
                    type="primary"
                )

    # --- ب. واجهة الأقسام ---
    else:
        sec = st.session_state.user_section
        st.title(f"🏗️ إدارة بيانات قسم: {sec}")
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
            status_options = ["🟢 مكتمل", "🔵 قيد التنفيذ", "🟠 بانتظار مستندات", "🔴 متوقف / معلق"]
            
            edited_staff = st.data_editor(display_df, column_config={"المشروع": st.column_config.TextColumn(disabled=True), "🚩 توجيه المدير": st.column_config.TextColumn(disabled=True), "حالة المشروع": st.column_config.SelectboxColumn("حالة المشروع", options=status_options) if sec != "الحسابات" else None}, hide_index=True, use_container_width=True, key="staff_editor")

            if st.button("🚀 حفظ البيانات النهائية", type="primary", use_container_width=True):
                updates = []
                now = datetime.now().isoformat()
                for idx in range(len(edited_staff)):
                    row = edited_staff.iloc[idx]
                    payload = {
                        "id": int(db_df.iloc[idx]["id"]), "section_name": sec,
                        "col1": str(row.get(map_dict["col1"], "")), "col2": str(row.get(map_dict["col2"], "")),
                        "col3": str(row.get(map_dict["col3"], "")), "comment": str(row.get(map_dict["comment"], "")),
                        "updated_at": now
                    }
                    if sec == "الحسابات":
                        payload.update({"col4": str(row.get("صادر التنفيذ", "")), "col5": str(row.get("الرصيد", ""))})
                    updates.append(payload)
                
                try:
                    supabase.table("project_data").upsert(updates).execute()
                    st.balloons()
                    st.success(f"✅ تم حفظ بيانات قسم {sec} بنجاح!")
                    st.toast("تم التحديث")
                except Exception as e:
                    st.error(f"خطأ في الحفظ: {e}")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
