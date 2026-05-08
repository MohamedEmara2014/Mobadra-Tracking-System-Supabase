# --- داخل جزء واجهة المدير العام - تبويب التقرير المجمع ---

with tabs[-1]:
    st.subheader("📋 تقرير المتابعة الشامل (كافة الأقسام الملونة)")
    
    # 1. تجميع البيانات
    projects_list = full_df[["project_id", "المشروع", "الموقع"]].drop_duplicates().sort_values("project_id")
    final_combined = projects_list.copy()
    
    # تعريف رموز الألوان لكل قسم للتمييز البصري
    sec_emojis = {
        "التنفيذ": "🏗️", "الجدول الزمني": "📅", "المكتب الفني": "📐", 
        "التراخيص": "📜", "الحسابات": "💰", "الشئون القانونية": "⚖️", 
        "أقساط الجهاز": "📠", "خدمة العملاء": "🤝"
    }

    for s_name in all_sections:
        sec_subset = full_df[full_df["section_name"] == s_name]
        if not sec_subset.empty:
            mapped = get_mapped_df(sec_subset, s_name)
            
            # إضافة رمز القسم لكل عمود لتمييزه بصرياً
            prefix = sec_emojis.get(s_name, "")
            new_names = {col: f"{prefix} {col}" for col in mapped.columns if col not in ["project_id", "المشروع", "الموقع"]}
            mapped = mapped.rename(columns=new_names)
            
            mapped = mapped.drop(columns=["المشروع", "الموقع"])
            final_combined = pd.merge(final_combined, mapped, on="project_id", how="left")

    # 2. تحسين مظهر الجدول باستخدام Pandas Styler
    def color_columns(df):
        # مصفوفة ألوان خفيفة للخلفيات (اختياري)
        return df.style.set_properties(**{
            'background-color': '#f9f9f9',
            'color': 'black',
            'border-color': 'white'
        })

    # 3. عرض الجدول مع تثبيت الأعمدة الأساسية
    st.data_editor(
        final_combined.drop(columns=["project_id"]),
        column_config={
            "المشروع": st.column_config.TextColumn(pinned=True, width="medium"),
            "الموقع": st.column_config.TextColumn(pinned=True, width="small"),
        },
        disabled=True,
        hide_index=True,
        use_container_width=False 
    )
    
    # زر لتحميل التقرير المجمع كملف Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        final_combined.to_excel(writer, index=False, sheet_name='التقرير المجمع')
    
    st.download_button(
        label="📥 تحميل التقرير المجمع (Excel)",
        data=buffer,
        file_name=f"التقرير_المجمع_{datetime.now().date()}.xlsx",
        mime="application/vnd.ms-excel"
    )
