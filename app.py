import streamlit as st
import pandas as pd
from pypdf import PdfReader
import google.generativeai as genai
import io
import re

# Page configuration
st.set_page_config(
    page_title="土地登記簿等調査表 自動抽出システム",
    page_icon="📄",
    layout="wide"
)

st.title("📄 土地登記簿等調査表 自動抽出アプリ")
st.markdown("登記事項要約書（申請地・隣接地）のPDFをアップロードすると、10項目の規格通りに自動抽出し、Excel形式でダウンロードできます。")

# Sidebar for API Key input
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key を入力", type="password")
    st.info("APIキーを入力すると、AIによる高精度なデータ抽出が実行されます。")

uploaded_files = st.file_uploader(
    "PDFファイルをドラッグ＆ドロップまたは選択してください (複数選択可)",
    type=["pdf"],
    accept_multiple_files=True
)

def extract_text_from_pdfs(files):
    combined_text = ""
    for file in files:
        reader = PdfReader(file)
        combined_text += f"\n--- File: {file.name} ---\n"
        for i, page in enumerate(reader.pages):
            combined_text += f" Page {i+1}:\n" + (page.extract_text() or "")
    return combined_text

def process_with_gemini(text, key):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    あなたは土地登記簿等調査表のデータ抽出専門AIです。
    以下のテキストデータから【当該地】および【隣接地】の情報を抽出し、各列をTSV形式（タブ区切り）で出力してください。

    【抽出項目（10列）】
    1. 字
    2. 地番
    3. 地目
    4. 地積㎡
    5. 所有者住所
    6. 登記名義人
    7. 現所有者
    8. 抵当権其他の権利関係内容（※必ず空欄にすること）
    9. 備考
    10. 地積測量図の有無（※「無」とする）

    【適用ルール】
    ・「備考」欄は、日付を必ず先頭に配置すること（例：「平成14年7月18日 国土調査による成果」）。
    ・地積の右側（原因及びその日付）にある③等の記号や、下段に記載されている変更履歴（例：「平成27年4月20日 地目変更登記」）も漏れなく抽出して「備考」に結合すること。
    ・「抵当権其他の権利関係内容」は常に完全な空欄（タブのみ）とすること。
    ・出力は純粋なTSVデータ（ヘッダー付き）のみを出力し、余計な説明文は含めないでください。

    対象テキスト:
    {text}
    """
    
    response = model.generate_content(prompt)
    return response.text

if uploaded_files:
    if not api_key:
        st.warning("⚠️ 画面左側のサイドバーに Gemini API Key を入力してください。")
    else:
        with st.spinner("PDFデータを解析・抽出中..."):
            try:
                raw_text = extract_text_from_pdfs(uploaded_files)
                tsv_result = process_with_gemini(raw_text, api_key)
                
                # Clean code blocks if present in response
                cleaned_tsv = re.sub(r'```tsv|```', '', tsv_result).strip()
                
                # Load into DataFrame
                df = pd.read_csv(io.StringIO(cleaned_tsv), sep='\t')
                
                st.success("✅ 抽出が完了しました！")
                st.subheader("📊 抽出結果プレビュー")
                st.dataframe(df, use_container_width=True)
                
                # Convert to Excel
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='土地登記簿等調査表')
                
                st.download_button(
                    label="📥 Excelファイル (.xlsx) をダウンロード",
                    data=excel_buffer.getvalue(),
                    file_name="土地登記簿等調査表_抽出結果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")