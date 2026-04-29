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

# دالة جلب البيانات مع تخطي الكاش لضمان رؤية آخر التحديثات
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

    # --- واجهة المدير ---
    if st.session_state.role == "admin":
        st.title("📊 لوحة تحكم المدير العام")
        full_df = get_data_fresh()
        
        if not full_df.empty:
            tabs = st.tabs(all_sections + ["📋 الجدول المجمع الشامل"])
            
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    st.subheader(f"بيانات قسم {sec_name}")
                    # تصفية البيانات للقسم الحالي فقط
                    sec_data = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                    
                    if not sec_data.empty:
                        sec_data["المشروع"] = sec_data["projects"].apply(lambda x: x["name"])
                        
                        # تعريف مسميات الأعمدة بناءً على نوع القسم
                        if sec_name == "الحسابات":
                            map_dict = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols_to_show = ["المشروع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد", "ملاحظات القسم", "توجيه المدير"]
                        else:
                            map_dict = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه المدير"}
                            cols_to_show = ["المشروع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه المدير"]
                        
                        display_df = sec_data.rename(columns=map_dict)
                        
                        # محرر البيانات للمدير - التركيز على "توجيه المدير"
                        edited_adm = st.data_editor(
                            display_df[cols_to_show],
                            column_config={
                                "المشروع": st.column_config.TextColumn(disabled=True),
                                "توجيه المدير": st.column_config.TextColumn("📝 اكتب التوجيه هنا", width="large")
                            },
                            hide_index=True,
                            key=f"editor_tab_{sec_name}"
                        )
                        
                        # زر الحفظ لكل قسم لضمان الدقة
                        if st.button(f"💾 حفظ واعتماد توجيهات {sec_name}", key=f"btn_save_{sec_name}"):
                            updates = []
                            for idx in range(len(edited_adm)):
                                row_id = int(sec_data.iloc[idx]["id"])
                                new_note = str(edited_adm.iloc[idx]["توجيه المدير"])
                                updates.append({"id": row_id, "action_note": new_note})
                            
                            supabase.table("project_data").upsert(updates).execute()
                            st.success(f"✅ تم تحديث توجيهات قسم {sec_name}")
                            st.rerun()
                    else:
                        st.warning(f"لا توجد بيانات مسجلة لهذا القسم حالياً.")

            # التبويب المجمع (الحل الجذري)
            with tabs[-1]:
                st.subheader("📋 ملخص كافة المشروعات (38 مشروع)")
                p_names = sorted(full_df["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1] if len(x.split()) > 1 else 0))
                
                pano_list = []
                for p_name in p_names:
                    row = {"المشروع": p_name}
                    for s in all_sections:
                        r = full_df[(full_df["projects"].apply(lambda x: x["name"]) == p_name) & (full_df["section_name"] == s)]
                        if not r.empty:
                            row[f"{s}: إنجاز/وارد"] = r.iloc[0]["col1"]
                            row[f"{s}: حالة/رصيد"] = r.iloc[0]["col3"] if s != "الحسابات" else r.iloc[0]["col5"]
                    pano_list.append(row)
                
                final_pano_df = pd.DataFrame(pano_list)
                st.dataframe(final_pano_df, hide_index=True, use_container_width=True)
                
                # زر تحميل الإكسيل المجمع
                buf = io.BytesIO()
                final_pano_df.to_excel(buf, index=False)
                st.download_button("📥 تحميل التقرير المجمع (Excel)", buf.getvalue(), "المبادرة_المجمع.xlsx", type="primary")

    # --- واجهة الأقسام (Staff) ---
    else:
        # واجهة الأقسام كما في الكود السابق مع تفعيل "توجيه المدير" كعمود للقراءة فقط
        pass

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
