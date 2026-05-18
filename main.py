import streamlit as st
import pandas as pd
from supabase import create_client
import io
from datetime import datetime
import time

# --- 1. إعدادات الاتصال وقاعدة البيانات ---
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

PROJECT_LOCATIONS = [
    "الشروق", "الشروق", "العبور", "القاهرة الجديدة (بيت الوطن)", "النرجس الجديدة", 
    "بدر", "العاشر", "العاشر", "شمال الرحاب", "شمال الرحاب", "النرجس الجديدة", 
    "النورس هاوس", "شمال الرحاب", "القاهرة الجديدة (بيت الوطن)", "العاشر", 
    "العبور الجديدة", "شمال الرحاب", "النورس هاوس", "النرجس الجديدة", 
    "القاهرة الجديدة (بيت الوطن)", "العاشر", "هليوبوليس الجديدة", "الزقازيق", 
    "الزقازيق", "هليوبوليس الجديدة", "الأوركيد", "الزقازيق", "العاشر", 
    "شمال الرحاب", "القاهرة الجديدة (بيت الوطن)", "العاشر", "العبور الجديدة", 
    "العبور الجديدة", "الزقازيق", "هليوبوليس الجديدة", "الزقازيق", 
    "هليوبوليس الجديدة", "هليوبوليس الجديدة"
]

# خيارات الشئون القانونية
LEGAL_CHECKS = ["✅ تم لجميع الأعضاء", "⚠️ تم لبعض الأعضاء", "❌ لم يسلم أحد"]
LEGAL_POWERS = ["✅ تم لجميع الأعضاء", "⚠️ تم لبعض الأعضاء", "❌ لم يسلم أحد"]
LEGAL_CONTRACTS = ["✅ تم لجميع الأعضاء", "⚠️ تم لبعض الأعضاء", "❌ لم يوقع أحد"]

# خيارات المكتب الفني
TECH_OFFICE_STATUS = ["🔴 لم تبدأ", "🟡 جاري العمل", "🟢 تم الإنتهاء"]
TECH_SCHEDULE_STATUS = ["✅ تم العرض على المجموعة", "❌ لم يتم العرض على المجموعة"]

def add_location_column(df):
    if not df.empty and 'project_id' in df.columns:
        df['الموقع'] = df['project_id'].apply(
            lambda x: PROJECT_LOCATIONS[int(x)-1] if 0 < int(x) <= len(PROJECT_LOCATIONS) else "غير محدد"
        )
    return df

def get_mapped_df_for_summary(df, sec_name):
    if sec_name == "الحسابات":
        m = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات الحسابات"}
    elif sec_name == "الجدول الزمني":
        m = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات الجدول"}
    elif sec_name == "أقساط الجهاز":
        m = {"col1": "اخر قسط تم دفعه", "col2": "القسط التالي", "comment": "ملاحظات الأقساط"}
    elif sec_name == "الشئون القانونية":
        m = {"col1": "تسليم الشيكات", "col2": "التوكيلات", "col3": "العقود", "comment": "ملاحظات قانونية"}
    elif sec_name == "المكتب الفني":
        m = {"col1": "الرسومات المعمارية", "col2": "الرسومات الإنشائية", "col3": "المعمارية التنفيذية", "col4": "الإنشائية التنفيذية", "col5": "الجدول الزمني", "comment": "ملاحظات المكتب الفني"}
    else:
        m = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": f"ملاحظات {sec_name}"}
    
    available_cols = ["project_id"]
    rename_dict = {}
    for db_col, target_name in m.items():
        if db_col in df.columns:
            available_cols.append(db_col)
            rename_dict[db_col] = target_name
    if "action_note" in df.columns:
        available_cols.append("action_note"); rename_dict["action_note"] = f"توجيه {sec_name}"
    return df[available_cols].copy().rename(columns=rename_dict)

# --- 2. نظام تسجيل الدخول ---
if "auth" not in st.session_state:
    st.session_state.auth, st.session_state.role, st.session_state.user_section = False, None, None

if not st.session_state.auth:
    st.set_page_config(page_title="تسجيل الدخول", layout="centered")
    st.title("🔐 نظام متابعة مشروعات المبادرة")
    with st.form("login_form"):
        pwd = st.text_input("أدخل كلمة المرور:", type="password")
        if st.form_submit_button("دخول"):
            passwords = {"Admin38": "admin", "Exec123": "التنفيذ", "Time123": "الجدول الزمني", "Tech123": "المكتب الفني", "Lic123": "التراخيص", "Acc123": "الحسابات", "Legal123": "الشئون القانونية", "Install123": "أقساط الجهاز", "Cust123": "خدمة العملاء"}
            if pwd in passwords:
                st.session_state.auth, val = True, passwords[pwd]
                st.session_state.role = "admin" if val == "admin" else "staff"
                st.session_state.user_section = val if val != "admin" else None
                st.rerun()
            else: st.error("❌ كلمة المرور غير صحيحة")
else:
    st.set_page_config(page_title="نظام المبادرة", layout="wide")
    all_sections = ["التنفيذ", "الجدول الزمني", "المكتب الفني", "التراخيص", "الحسابات", "الشئون القانونية", "أقساط الجهاز", "خدمة العملاء"]
    sec_emojis = {"التنفيذ": "🏗️", "الجدول الزمني": "📅", "المكتب الفني": "📐", "التراخيص": "📜", "الحسابات": "💰", "الشئون القانونية": "⚖️", "أقساط الجهاز": "📠", "خدمة العملاء": "🤝"}
    TIME_STATUS_OPTIONS = ["✅ متوافق", "🚀 متقدم", "⚠️ متأخر"]

    if st.session_state.role == "admin":
        st.title("📊 لوحة تحكم المدير العام")
        full_df = add_location_column(get_data_fresh())
        if not full_df.empty:
            full_df['updated_at'] = pd.to_datetime(full_df['updated_at'])
            full_df["المشروع"] = full_df["projects"].apply(lambda x: x["name"] if x else "غير معروف")
            tabs = st.tabs(all_sections + ["📋 التقرير المجمع الشامل"])
            
            for i, sec_name in enumerate(all_sections):
                with tabs[i]:
                    sec_data = full_df[full_df["section_name"] == sec_name].copy().sort_values("project_id")
                    if not sec_data.empty:
                        st.info(f"🕒 آخر تحديث لهذا القسم: {sec_data['updated_at'].max().strftime('%Y-%m-%d | %I:%M %p')}")
                        if sec_name == "الحسابات": m_dict, cols = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات القسم", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد المتاح", "ملاحظات القسم", "توجيه الإدارة"]
                        elif sec_name == "الجدول الزمني": m_dict, cols = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "الربع", "الحالة بالنسبة للجدول الزمني", "أخر تصفية", "أخر مستخلص", "ملاحظات", "توجيه الإدارة"]
                        elif sec_name == "أقساط الجهاز": m_dict, cols = {"col1": "اخر قسط تم دفعه", "col2": "القسط التالي", "comment": "ملاحظات", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "اخر قسط تم دفعه", "القسط التالي", "ملاحظات", "توجيه الإدارة"]
                        elif sec_name == "الشئون القانونية": m_dict, cols = {"col1": "تسليم الشيكات", "col2": "التوكيلات", "col3": "العقود", "comment": "ملاحظات قانونية", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "تسليم الشيكات", "التوكيلات", "العقود", "ملاحظات قانونية", "توجيه الإدارة"]
                        elif sec_name == "المكتب الفني": m_dict, cols = {"col1": "الرسومات المعمارية", "col2": "الرسومات الإنشائية", "col3": "المعمارية التنفيذية", "col4": "الإنشائية التنفيذية", "col5": "الجدول الزمني", "comment": "ملاحظات المكتب الفني", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "الرسومات المعمارية", "الرسومات الإنشائية", "المعمارية التنفيذية", "الإنشائية التنفيذية", "الجدول الزمني", "ملاحظات المكتب الفني", "توجيه الإدارة"]
                        else: m_dict, cols = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "توجيه الإدارة"}, ["المشروع", "الموقع", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم", "توجيه الإدارة"]
                        
                        adm_configs = {
                            "المشروع": st.column_config.TextColumn(disabled=True, pinned=True),
                            "الموقع": st.column_config.TextColumn(disabled=True, pinned=True),
                            "توجيه الإدارة": st.column_config.TextColumn(disabled=False, help="اكتب هنا التوجيه واضغط زر الحفظ بالأسفل", width="large"),
                        }
                        
                        adm_edited = st.data_editor(sec_data.rename(columns=m_dict)[cols], column_config=adm_configs, hide_index=True, use_container_width=True, key=f"adm_edit_{sec_name}")
                        
                        if st.button(f"💾 حفظ توجيهات قسم {sec_name}", key=f"btn_save_adm_{sec_name}"):
                            try:
                                adm_updates = []
                                for idx in range(len(adm_edited)):
                                    row = adm_edited.iloc[idx]
                                    adm_updates.append({
                                        "id": int(sec_data.iloc[idx]["id"]),
                                        "section_name": str(sec_name),
                                        "project_id": int(sec_data.iloc[idx]["project_id"]),
                                        "col1": str(sec_data.iloc[idx].get("col1", "")) if pd.notnull(sec_data.iloc[idx].get("col1", "")) else "",
                                        "col2": str(sec_data.iloc[idx].get("col2", "")) if pd.notnull(sec_data.iloc[idx].get("col2", "")) else "",
                                        "col3": str(sec_data.iloc[idx].get("col3", "")) if pd.notnull(sec_data.iloc[idx].get("col3", "")) else "",
                                        "col4": str(sec_data.iloc[idx].get("col4", "")) if pd.notnull(sec_data.iloc[idx].get("col4", "")) else "",
                                        "col5": str(sec_data.iloc[idx].get("col5", "")) if pd.notnull(sec_data.iloc[idx].get("col5", "")) else "",
                                        "comment": str(sec_data.iloc[idx].get("comment", "")) if pd.notnull(sec_data.iloc[idx].get("comment", "")) else "",
                                        "action_note": str(row.get("توجيه الإدارة", "")) if pd.notnull(row.get("توجيه الإدارة", "")) else "",
                                        "updated_at": datetime.now().isoformat()
                                    })
                                if adm_updates:
                                    supabase.table("project_data").upsert(adm_updates).execute()
                                    st.success(f"✅ تم حفظ وإرسال توجيهات قسم {sec_name} بنجاح.")
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"حدث خطأ أثناء حفظ التوجيهات: {e}")

            with tabs[-1]:
                projects_base = full_df[["project_id", "المشروع", "الموقع"]].drop_duplicates().sort_values("project_id")
                combined_final = projects_base.copy()
                for s_name in all_sections:
                    sec_subset = full_df[full_df["section_name"] == s_name]
                    if not sec_subset.empty:
                        mapped = get_mapped_df_for_summary(sec_subset, s_name)
                        new_cols = {c: f"{sec_emojis.get(s_name, '')} {c}" for c in mapped.columns if c != "project_id"}
                        combined_final = pd.merge(combined_final, mapped.rename(columns=new_cols), on="project_id", how="left")
                
                st.subheader("📋 التقرير المجمع لكافة الأقسام")
                output_all = io.BytesIO()
                with pd.ExcelWriter(output_all, engine='xlsxwriter') as writer:
                    combined_final.drop(columns=["project_id"]).to_excel(writer, index=False, sheet_name='التقرير الشامل')
                st.download_button(label="📥 تحميل التقرير المجمع (Excel)", data=output_all.getvalue(), file_name=f"التقرير_المجمع_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.ms-excel")
                
                st.data_editor(combined_final.drop(columns=["project_id"]), column_config={"المشروع": st.column_config.TextColumn(pinned=True), "الموقع": st.column_config.TextColumn(pinned=True)}, disabled=True, hide_index=True)

    else:
        sec = st.session_state.user_section
        st.title(f"{sec_emojis.get(sec, '🏗️')} إدارة بيانات قسم: {sec}")
        
        res = supabase.table("project_data").select("*, projects(name)").eq("section_name", sec).order("project_id").execute()
        if res.data:
            db_df = add_location_column(pd.DataFrame(res.data))
            db_df["المشروع"] = db_df["projects"].apply(lambda x: x["name"])
            
            if sec == "الحسابات": m_dict, cols = {"col1": "وارد العملاء", "col2": "صادر العملاء", "col3": "وارد التنفيذ", "col4": "صادر التنفيذ", "col5": "الرصيد المتاح", "comment": "ملاحظات القسم", "action_note": "🚨 توجيه الإدارة"}, ["المشروع", "الموقع", "🚨 توجيه الإدارة", "وارد العملاء", "صادر العملاء", "وارد التنفيذ", "صادر التنفيذ", "الرصيد المتاح", "ملاحظات القسم"]
            elif sec == "الجدول الزمني": m_dict, cols = {"col1": "الربع", "col2": "الحالة بالنسبة للجدول الزمني", "col3": "أخر تصفية", "col4": "أخر مستخلص", "comment": "ملاحظات", "action_note": "🚨 توجيه الإدارة"}, ["المشروع", "الموقع", "🚨 توجيه الإدارة", "الربع", "الحالة بالنسبة للجدول الزمني", "أخر تصفية", "أخر مستخلص", "ملاحظات"]
            elif sec == "أقساط الجهاز": m_dict, cols = {"col1": "اخر قسط تم دفعه", "col2": "القسط التالي", "comment": "ملاحظات", "action_note": "🚨 توجيه الإدارة"}, ["المشروع", "الموقع", "🚨 توجيه الإدارة", "اخر قسط تم دفعه", "القسط التالي", "ملاحظات"]
            elif sec == "الشئون القانونية": m_dict, cols = {"col1": "تسليم الشيكات", "col2": "التوكيلات", "col3": "العقود", "comment": "ملاحظات قانونية", "action_note": "🚨 توجيه الإدارة"}, ["المشروع", "الموقع", "🚨 توجيه الإدارة", "تسليم الشيكات", "التوكيلات", "العقود", "ملاحظات قانونية"]
            elif sec == "المكتب الفني": m_dict, cols = {"col1": "الرسومات المعمارية", "col2": "الرسومات الإنشائية", "col3": "المعمارية التنفيذية", "col4": "الإنشائية التنفيذية", "col5": "الالجدول الزمني", "comment": "ملاحظات المكتب الفني", "action_note": "🚨 توجيه الإدارة"}, ["المشروع", "الموقع", "🚨 توجيه الإدارة", "الرسومات المعمارية", "الرسومات الإنشائية", "المعمارية التنفيذية", "الإنشائية التنفيذية", "الالجدول الزمني", "ملاحظات المكتب الفني"]
            else: m_dict, cols = {"col1": "ما تم انجازه", "col2": "المعوقات والمشاكل", "col3": "حالة المشروع", "comment": "ملاحظات القسم", "action_note": "🚨 توجيه الإدارة"}, ["المشروع", "الموقع", "🚨 توجيه الإدارة", "ما تم انجازه", "المعوقات والمشاكل", "حالة المشروع", "ملاحظات القسم"]

            # 🚨 إبراز لافت للنظر وتلوين فوري لخلفية التوجيهات من خلال لوحة تنبيه علوية جذابة جداً
            st.markdown(
                """
                <div style="background-color: #ff4b4b; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #ffffff; margin-bottom: 20px;">
                    <h3 style="color: white; margin: 0; font-weight: bold;">🚨 انتباه لجميع رؤساء الأقسام 🚨</h3>
                    <p style="color: white; font-size: 16px; margin: 5px 0 0 0;">تم تحديث وإبراز عمود <b>(🚩 توجيه الإدارة)</b> أدناه بلون خط داكن وخلفية عريضة ممتدة لرؤية التعليمات الصادرة فوراً.</p>
                </div>
                """, 
                unsafe_allow_html=True
            )

            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                template_df = db_df.rename(columns=m_dict)[cols]
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    template_df.to_excel(writer, index=False, sheet_name='Sheet1')
                st.download_button(label="📥 تحميل نموذج Excel لتعبئته", data=output.getvalue(), file_name=f"نموذج_{sec}.xlsx", mime="application/vnd.ms-excel")
            
            with col_ex2:
                uploaded_file = st.file_uploader("📤 رفع ملف Excel لتحديث البيانات", type=["xlsx"])
                up_df = None
                if uploaded_file:
                    up_df = pd.read_excel(uploaded_file).fillna("")

            display_df = up_df if up_df is not None else db_df.rename(columns=m_dict)[cols]
            
            # تخصيص عمود التوجيهات ليكون عريضاً جداً ومميزاً بشكل يلفت النظر
            col_configs = {
                "المشروع": st.column_config.TextColumn(disabled=True, pinned=True),
                "الموقع": st.column_config.TextColumn(disabled=True, pinned=True),
                "🚩 توجيه الإدارة": st.column_config.TextColumn(
                    disabled=True, 
                    width="large", 
                    help="⚠️ تنبيه: هذه تعليمات إلزامية مباشرة من المدير العام"
                ),
            }
            if sec == "الشئون القانونية":
                col_configs.update({
                    "تسليم الشيكات": st.column_config.SelectboxColumn("تسليم الشيكات", options=LEGAL_CHECKS, required=True),
                    "التوكيلات": st.column_config.SelectboxColumn("التوكيلات", options=LEGAL_POWERS, required=True),
                    "العقود": st.column_config.SelectboxColumn("العقود", options=LEGAL_CONTRACTS, required=True),
                })
            elif sec == "المكتب الفني":
                col_configs.update({
                    "الرسومات المعمارية": st.column_config.SelectboxColumn("الرسومات المعمارية", options=TECH_OFFICE_STATUS, required=True),
                    "الرسومات الإنشائية": st.column_config.SelectboxColumn("الرسومات الإنشائية", options=TECH_OFFICE_STATUS, required=True),
                    "المعمارية التنفيذية": st.column_config.SelectboxColumn("المعمارية التنفيذية", options=TECH_OFFICE_STATUS, required=True),
                    "الإنشائية التنفيذية": st.column_config.SelectboxColumn("الإنشائية التنفيذية", options=TECH_OFFICE_STATUS, required=True),
                    "الالجدول الزمني": st.column_config.SelectboxColumn("الجدول الزمني", options=TECH_SCHEDULE_STATUS, required=True),
                })
            elif sec == "الجدول الزمني":
                col_configs["الحالة بالنسبة للجدول الزمني"] = st.column_config.SelectboxColumn("الحالة بالنسبة للجدول الزمني", options=TIME_STATUS_OPTIONS)

            edited_df = st.data_editor(display_df, column_config=col_configs, hide_index=True, use_container_width=True)
            
            if st.button("🚀 حفظ كافة التعديلات", type="primary", use_container_width=True):
                updates, now = [], datetime.now().isoformat()
                def clean(val): return str(val) if pd.notnull(val) and str(val).strip() != "" else ""

                try:
                    for idx in range(len(edited_df)):
                        row = edited_df.iloc[idx]
                        updates.append({
                            "id": int(db_df.iloc[idx]["id"]),
                            "section_name": str(sec),
                            "project_id": int(db_df.iloc[idx]["project_id"]),
                            "col1": clean(row.get(m_dict.get("col1"), "")),
                            "col2": clean(row.get(m_dict.get("col2"), "")),
                            "col3": clean(row.get(m_dict.get("col3"), "")),
                            "col4": clean(row.get(m_dict.get("col4"), "")),
                            "col5": clean(row.get(m_dict.get("col5"), "")),
                            "comment": clean(row.get(m_dict.get("comment"), "")),
                            "action_note": clean(db_df.iloc[idx].get("action_note", "")), 
                            "updated_at": now
                        })
                    
                    if updates:
                        supabase.table("project_data").upsert(updates).execute()
                        st.success("✅ تم حفظ وتحديث كافة البيانات بنجاح.")
                        time.sleep(1.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء الحفظ: {e}")

    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state.auth = False
        st.rerun()
