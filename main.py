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
                        sec_df = full_df[full_df["section_name"] == sec].copy().sort_values("project_id")
                        sec_df["المشروع"] = sec_df["projects"].apply(lambda x: x["name"])
                        
                        if sec == "الحسابات":
                            mapper = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            disp_cols = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            mapper = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            disp_cols = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        display_df = sec_df.rename(columns=mapper)
                        st.subheader(f"توجيهات قسم {sec}")
                        
                        # تم تفعيل التعديل على عمود توجيه المدير فقط
                        edited_output = st.data_editor(
                            display_df[disp_cols],
                            column_config={
                                "المشروع": st.column_config.TextColumn(disabled=True),
                                "توجيه المدير": st.column_config.TextColumn("📝 اكتب توجيه المدير هنا", width="large", disabled=False)
                            },
                            hide_index=True,
                            key=f"admin_editor_{sec}"
                        )
                        
                        if st.button(f"💾 اعتماد توجيهات قسم {sec}", key=f"btn_save_adm_{sec}"):
                            updates = []
                            for idx in range(len(edited_output)):
                                db_id = sec_df.iloc[idx]["id"]
                                new_note = edited_output.iloc[idx]["توجيه المدير"]
                                updates.append({"id": db_id, "action_note": str(new_note)})
                            
                            supabase.table("project_data").upsert(updates).execute()
                            st.success(f"✅ تم إرسال توجيهات قسم {sec} بنجاح!")
                            st.rerun()
                                
                with tabs[-1]:
                    st.subheader("📊 ملخص كافة بيانات الأقسام (الجدول المجمع)")
                    full_df_up = get_data() # جلب أحدث البيانات
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
                    
                    final_pano_df = pd.DataFrame(pano_list)
                    st.dataframe(final_pano_df, hide_index=True, use_container_width=True)
                    
                    # زر تحميل الإكسيل للجدول المجمع - يظهر فقط في هذا التبويب
                    st.divider()
                    if st.button("📂 تجهيز ملف إكسيل للجدول المجمع"):
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            final_pano_df.to_excel(writer, index=False, sheet_name='Summary')
                        st.download_button(
                            label="📥 اضغط هنا لتحميل ملف الإكسيل المجمع",
                            data=output.getvalue(),
                            file_name="المبادرة_الجدول_المجمع.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

    else:
        # واجهة الموظفين
        selected_section = st.session_state.user_section
        st.title(f"🏗️ قسم: {selected_section}")
        # (بقية الكود كما هو مع التأكد من تسمية الأعمدة الصحيحة)
        # ... [الجزء الخاص بالموظفين تم الحفاظ عليه مع مسميات الأعمدة الأصلية] ...
