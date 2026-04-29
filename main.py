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
        st.title("📊 لوحة تحكم المدير العام (38 مشروع)")
        full_df = get_data_fresh()
        
        if not full_df.empty:
            tabs = st.tabs(all_sections + ["📋 الجدول المجمع الشامل"])
            
            # حل مشكلة بيانات الأقسام للمدير
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    st.subheader(f"بيانات وتوجيهات قسم: {sec_name}")
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
                        
                        edited_adm = st.data_editor(
                            display_df, 
                            column_config={"المشروع": st.column_config.TextColumn(disabled=True), "توجيه المدير": st.column_config.TextColumn("📝 التوجيه", width="large")},
                            hide_index=True, key=f"adm_ed_key_{sec_name}"
                        )
                        
                        # حل مشكلة APIError: نرسل فقط الـ ID والـ action_note
                        if st.button(f"💾 اعتماد توجيهات {sec_name}", key=f"btn_save_adm_{sec_name}"):
                            updates = []
                            for idx in range(len(edited_adm)):
                                row_id = int(sec_data.iloc[idx]["id"])
                                note_val = str(edited_adm.iloc[idx].get("توجيه المدير", ""))
                                updates.append({"id": row_id, "action_note": note_val})
                            
                            try:
                                supabase.table("project_data").upsert(updates).execute()
                                st.success(f"✅ تم حفظ توجيهات {sec_name} بنجاح!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"فشل الحفظ: تأكد من أن البيانات صحيحة. {e}")
                    else:
                        st.info(f"لا توجد بيانات حالية لقسم {sec_name}")

            # حل مشكلة الجدول المجمع (يظهر الآن بشكل صحيح)
            with tabs[-1]:
                st.subheader("📋 ملخص كافة الأقسام لكافة المشروعات")
                all_projects = sorted(full_df["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]) if " " in x else 0)
                
                summary_data = []
                for p in all_projects:
                    row = {"المشروع": p}
                    for s in all_sections:
                        sub = full_df[(full_df["projects"].apply(lambda x: x["name"]) == p) & (full_df["section_name"] == s)]
                        if not sub.empty:
                            row[f"{s}: إنجاز/وارد"] = sub.iloc[0]["col1"]
                            row[f"{s}: حالة/رصيد"] = sub.iloc[0]["col3"] if s != "الحسابات" else sub.iloc[0]["col5"]
                    summary_data.append(row)
                
                final_summary_df = pd.DataFrame(summary_data)
                st.dataframe(final_summary_df, hide_index=True, use_container_width=True)
                
                # تحميل الإكسيل المجمع
                excel_buf = io.BytesIO()
                final_summary_df.to_excel(excel_buf, index=False)
                st.download_button("📥 تحميل التقرير المجمع (Excel)", excel_buf.getvalue(), "المجمع_الشامل.xlsx", type="primary")

    # --- ب. واجهة الأقسام (Staff) ---
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

            # ميزة التحميل والرفع
            st.markdown("### 📑 تحديث البيانات")
            c1, c2 = st.columns(2)
            with c1:
                # تحميل الملف كنموذج
                tmp_buf = io.BytesIO()
                display_df.to_excel(tmp_buf, index=False)
                st.download_button("📥 تحميل نموذج القسم (Excel)", tmp_buf.getvalue(), f"نموذج_{sec}.xlsx", use_container_width=True)
            with c2:
                up_file = st.file_uploader("📤 ارفع الملف بعد التعديل:", type=["xlsx"])
                if up_file:
                    up_df = pd.read_excel(up_file)
                    for c in display_df.columns:
                        if c in up_df.columns and c not in ["المشروع", "🚩 توجيه المدير"]:
                            display_df[c] = up_df[c].values[:len(display_df)]
                    st.success("✅ تم استيراد البيانات، راجع الجدول ثم اضغط حفظ.")

            # الجدول
            edited_staff = st.data_editor(
                display_df,
                column_config={"المشروع": st.column_config.TextColumn(disabled=True), "🚩 توجيه المدير": st.column_config.TextColumn(disabled=True)},
                hide_index=True, use_container_width=True, key=f"staff_editor_final"
            )

            if st.button("🚀 حفظ البيانات في قاعدة البيانات", type="primary"):
                updates = []
                for idx in range(len(edited_staff)):
                    row = edited_staff.iloc[idx]
                    payload = {
                        "id": int(db_df.iloc[idx]["id"]),
                        "col1": str(row.get(map_dict["col1"], "")),
                        "col2": str(row.get(map_dict["col2"], "")),
                        "col3": str(row.get(map_dict["col3"], "")),
                        "comment": str(row.get(map_dict["comment"], ""))
                    }
                    if sec == "الحسابات":
                        payload.update({"col4": str(row.get("صادر التنفيذ", "")), "col5": str(row.get("الرصيد", ""))})
                    updates.append(payload)
                
                try:
                    supabase.table("project_data").upsert(updates).execute()
                    st.success("✅ تم تحديث البيانات بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ أثناء الحفظ: {e}")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
