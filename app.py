import streamlit as st
import pandas as pd
from pypdf import PdfReader
import google.generativeai as genai
import io
import re

# Page configuration
st.set_page_config(
    page_title="Land Registry Data Extractor",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Land Registry Survey Data Extractor")
st.markdown("Upload target and adjacent land registry PDF files into their respective sections below. The application will extract and structure data into the standard 10-column schema.")

# Sidebar for API Key input
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Entering your API key enables high-accuracy data extraction via Gemini.")

# Two separate upload sections side-by-side
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. 当該地 (Target Land) PDFs")
    target_files = st.file_uploader(
        "Upload Target Land files",
        type=["pdf"],
        accept_multiple_files=True,
        key="target"
    )

with col2:
    st.subheader("2. 隣接地 (Adjacent Land) PDFs")
    adjacent_files = st.file_uploader(
        "Upload Adjacent Land files",
        type=["pdf"],
        accept_multiple_files=True,
        key="adjacent"
    )

def extract_text_from_pdfs(files):
    text = ""
    if files:
        for file in files:
            reader = PdfReader(file)
            text += f"\n--- File: {file.name} ---\n"
            for i, page in enumerate(reader.pages):
                text += f" Page {i+1}:\n" + (page.extract_text() or "")
    return text

def process_with_gemini(target_text, adjacent_text, key):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are an automated data extraction assistant for Japanese land registry survey tables (土地登記簿等調査表).
    Process the provided text and output raw TSV (Tab-Separated Values).

    【Input Data Categorization】
    - Target Land Data (【当該地】):
    {target_text if target_text else "None provided"}

    - Adjacent Land Data (【隣接地】):
    {adjacent_text if adjacent_text else "None provided"}

    【Required Schema (10 Columns)】
    1. 字
    2. 地番
    3. 地目
    4. 地積㎡
    5. 所有者住所
    6. 登記名義人
    7. 現所有者
    8. 抵当権其他の権利関係内容 (MUST be completely blank)
    9. 備考
    10. 地積測量図の有無 (Default to "無")

    【Strict Rules】
    - Categorize and list Target Land lots (【当該地】) first, followed by Adjacent Land lots (【隣接地】).
    - In the "備考" column: Place the DATE FIRST followed by the event details (e.g., "平成14年7月18日 国土調査による成果").
    - Multi-line & Symbol Checks: Check the right side of 地積㎡ for indicators like ③, and extract all matching registration change entries below it (e.g., "平成27年4月20日 地目変更登記").
    - The "抵当権其他の権利関係内容" column MUST remain completely empty (tab delimiter only).
    - Output ONLY the raw TSV data with the header row. Do not include introductory text or explanations.
    """
    
    response = model.generate_content(prompt)
    return response.text

# Process button and extraction logic
if target_files or adjacent_files:
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the left sidebar.")
    else:
        if st.button("🚀 Process Data", type="primary"):
            with st.spinner("Processing PDF data... Please wait."):
                try:
                    target_text = extract_text_from_pdfs(target_files)
                    adjacent_text = extract_text_from_pdfs(adjacent_files)
                    
                    tsv_result = process_with_gemini(target_text, adjacent_text, api_key)
                    
                    # Clean markdown code blocks from response
                    cleaned_tsv = re.sub(r'```tsv|```', '', tsv_result).strip()
                    
                    # Parse TSV into pandas DataFrame
                    df = pd.read_csv(io.StringIO(cleaned_tsv), sep='\t')
                    
                    st.success("✅ Extraction completed successfully!")
                    st.subheader("📊 Extracted Data Preview")
                    st.dataframe(df, use_container_width=True)
                    
                    # Create in-memory Excel file
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Land Registry Survey Table')
                    
                    st.download_button(
                        label="📥 Download Excel File (.xlsx)",
                        data=excel_buffer.getvalue(),
                        file_name="land_registry_survey_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"An error occurred during extraction: {str(e)}")
                    