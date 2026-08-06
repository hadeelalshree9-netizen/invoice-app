import streamlit as st
import pandas as pd
from PIL import Image
import json
import io
from google import genai
from google.genai import types

st.set_page_config(page_title="مجمع الفواتير والطلبات", layout="wide")
st.title("📦 تطبيق قراءة وتجميع الفواتير")

api_key = st.sidebar.text_input("أدخل مفتاح Gemini API Key:", type="password")

if not api_key:
    st.warning("👈 في القائمة الجانبية، يرجى إدخال مفتاح API للبدء.")
    st.stop()

client = genai.Client(api_key=api_key)

uploaded_files = st.file_uploader("اختر صور الفواتير:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 بدء تحليل وتجميع الصور"):
        all_items = []
        progress_bar = st.progress(0)
        
        prompt = """
        استخرج عناصر الطلبية من هذه الصورة.
        أعد النتيجة على شكل JSON يحتوي على مصفوفة باسم "items".
        كل عنصر في "items" يجب أن يحتوي على الحقول التالية فقط:
        - "product": اسم المنتج/العجين/الفطيرة
        - "size": الحجم (كبير، وسط، صغير، أو "غير محدد")
        - "quantity": العدد/الكمية (رقم صحيح)
        """

        for index, file in enumerate(uploaded_files):
            st.write(f"جاري معالجة: {file.name}...")
            image = Image.open(file)
            
            try:
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[image, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                data = json.loads(response.text)
                if "items" in data:
                    all_items.extend(data["items"])
                elif isinstance(data, list):
                    all_items.extend(data)
            except Exception as e:
                st.error(f"حدث خطأ أثناء قراءة {file.name}: {e}")
                
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_items:
            df = pd.DataFrame(all_items)
            
            # التأكد من وجود الأعمدة المطلوبة
            if 'quantity' in df.columns and 'product' in df.columns:
                df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
                
                group_cols = [col for col in ['product', 'size'] if col in df.columns]
                summary_df = df.groupby(group_cols, as_index=False)['quantity'].sum()
                
                st.success("تم التجميع بنجاح!")
                st.subheader("📊 المجموع الكلي للطلبات")
                st.dataframe(summary_df, use_container_width=True)
                
                # إمكانية التصدير إلى Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    summary_df.to_excel(writer, index=False, sheet_name='Summary')
                
                st.download_button(
                    label="📥 تحميل التقرير بصيغة Excel",
                    data=output.getvalue(),
                    file_name="invoice_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("لم يتم العثور على بيانات واضحة للكميات والمنتجات.")
