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

# دالة جلب البيانات
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
                        
                        # تحديد الأعمدة للعرض
                        cols_to_show = ["المشروع", "col1", "col2", "col3", "comment", "action_note"]
                        if sec == "الحسابات":
                            cols_to_show = ["المشروع", "col1", "col2", "col3", "col4", "col5", "comment", "action_note"]
                        
                        st.subheader(f"توجيهات قسم {sec}")
                        
                        # تعديل التوجيهات
                        edited_df = st.data_editor(
                            sec_df[cols_to_show],
                            column_config={
                                "المشروع": st.column_config.TextColumn(disabled=True),
                                "action_note": st.column_config.TextColumn("📝 توجيه المدير (اكتب هنا)", width="large")
                            },
                            hide_index=True,
                            key=f"editor_tab_{sec}"
                        )
                        
                        # زر الحفظ الخاص بكل قسم
                        if st.button(f"💾 حفظ توجيهات {sec}", key=f"btn_save_{sec}"):
                            with st.spinner("جاري الحفظ..."):
                                updates = []
                                for idx, row in edited_df.iterrows():
                                    db_id = sec_df.iloc[idx]["id"]
                                    updates.append({"id": db_id, "action_note": str(row["action_note"])})
                                
                                # الحفظ في Supabase
                                supabase.table("project_data").upsert(updates).execute()
                                
                                # عرض رسالة نجاح واضحة جداً
                                st.success(f"✅ تم تحديث توجيهات قسم {sec} بنجاح!")
                                st.balloons() # تأثير بصري للنجاح
                                
                with tabs[-1]:
                    st.subheader("📊 ملخص كافة بيانات الأقسام")
                    # جلب البيانات مجدداً للتأكد من ظهور التحديثات
                    full_df_updated = get_data()
                    p_names = sorted(full_df_updated["projects"].apply(lambda x: x["name"]).unique(), key=lambda x: int(x.split()[1]))
                    pano_list = []
                    for p_name in p_names:
                        row = {"المشروع": p_name}
                        for sec in all_sections:
                            s_rec = full_df_updated[(full_df_updated["projects"].apply(lambda x: x["name"]) == p_name) & (full_df_updated["section_name"] == sec)]
                            if not s_rec.empty:
                                r = s_rec.iloc[0]
                                row[f"{sec}: إنجاز/وارد"] = r["col1"]
                                row[f"{sec}: حالة/رصيد"] = r["col3"] if sec != "الحسابات" else r["col5"]
                        pano_list.append(row)
                    st.dataframe(pd.DataFrame(pano_list), hide_index=True, use_container_width=True)

        else:
            # وضع تحديث البيانات (للمدير لتعديل بيانات القسم نفسه)
            selected_section = st.sidebar.selectbox("اختر القسم:", all_sections)
            # ... (بقية كود التحديث كما هو) ...

    else:
        # واجهة الموظف (رؤية قسمه فقط)
        selected_section = st.session_state.user_section
        st.title(f"🏗️ قسم: {selected_section}")
        # ... (بقية كود الموظف) ...
        # (نفس منطق الحفظ أعلاه مع st.success و st.balloons لضمان رؤية النتيجة)

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
