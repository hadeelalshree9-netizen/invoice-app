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
    st.warning("⚠️ يرجى إدخال مفتاح API في القائمة الجانبية للبدء.")
    st.stop()

client = genai.Client(api_key=api_key)

uploaded_files = st.file_uploader("اختر صور الفواتير:", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

def process_invoice(image: Image.Image) -> list:
    prompt = """
    أنت خبير في قراءة وتحليل جداول الفواتير والطلبات باللغة العربية.
    اقرأ الجدول الموجود في الصورة بدقة واستخرج جميع الأصناف التي تحتوي على كميات أكبر من 0.
    
    قم بإرجاع النتيجة على شكل قائمة JSON فقط دون أي نصوص إضافية، بالشكل التالي:
    [
      {
        "الصنف": "اسم الصنف",
        "حجم العجين": "حجم العجين",
        "نوع العجين": "نوع العجين",
        "الكمية": عدد_القطع
      }
    ]
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    try:
        return json.loads(response.text)
    except Exception as e:
        st.error(f"حدث خطأ أثناء تحليل الصورة: {e}")
        return []

if uploaded_files and st.button("🚀 بدء تحليل وتجميع الصور"):
    all_data = []
    progress_bar = st.progress(0)
    
    for index, uploaded_file in enumerate(uploaded_files):
        st.write(f"⏳ جاري معالجة: **{uploaded_file.name}**...")
        image = Image.open(uploaded_file)
        items = process_invoice(image)
        all_data.extend(items)
        progress_bar.progress((index + 1) / len(uploaded_files))
    
    st.success("✅ تمت معالجة جميع الصور بنجاح!")
    
    if all_data:
        df = pd.DataFrame(all_data)
        df['الكمية'] = pd.to_numeric(df['الكمية'], errors='coerce').fillna(0).astype(int)
        
        st.subheader("📋 البيانات المستخرجة تفصيلياً")
        st.dataframe(df, use_container_width=True)
        
        grouped_df = df.groupby(["الصنف", "حجم العجين", "نوع العجين"], as_index=False)["الكمية"].sum()
        grouped_df = grouped_df.sort_values(by="الكمية", ascending=False)
        
        st.subheader("📊 المجموع الإجمالي للطلبات")
        st.dataframe(grouped_df, use_container_width=True)
        
        total_items = grouped_df['الكمية'].sum()
        st.metric("إجمالي عدد القطع المطلوبة كلياً", total_items)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            grouped_df.to_excel(writer, sheet_name='المجموع_الإجمالي', index=False)
            df.to_excel(writer, sheet_name='التفاصيل', index=False)
        
        st.download_button(
            label="📥 تحميل التقرير كملف Excel",
            data=output.getvalue(),
            file_name="تقرير_الطلبات_المجمع.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
