import streamlit as st
import json
import os
from pathlib import Path

# --- 頁面設定 ---
# 使用寬版頁面，讓內容有更多空間伸展
st.set_page_config(layout="wide", page_title="法務文件摘要系統")

# --- 資料載入 ---
# 使用 @st.cache_data 快取資料，加速 App 回應速度
@st.cache_data
def load_all_json_data(data_folder):
    """從指定資料夾載入所有 JSON 檔案"""
    json_files = sorted(list(Path(data_folder).glob("*.json"))) # 排序檔案
    all_data = []
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # 將檔案名稱也存入，方便除錯
                data['filename'] = file_path.name
                all_data.append(data)
            except json.JSONDecodeError:
                st.error(f"檔案 {file_path.name} 格式錯誤，無法解析。")
    return all_data

# --- 主程式 ---
# 假設您的 JSON 檔案都放在名為 'data' 的資料夾中
DATA_FOLDER = "corpus/summary" 

# 檢查資料夾是否存在
if not os.path.exists(DATA_FOLDER) or not os.listdir(DATA_FOLDER):
    st.error(f"錯誤：找不到資料夾 '{DATA_FOLDER}' 或資料夾為空。請建立此資料夾並將您的 JSON 檔案放入其中。")
    # 為了讓 App 能在沒有資料夾時也能預覽，我們建立一個假的範例資料
    st.info("正在使用範例資料進行預覽...")
    all_cases_data = [{
      "case_number": "114年度破抗字第2號 (範例)",
      "url": "https://law.judicial.gov.tw/FJUD/default.aspx", # 加上範例 URL
      "case_reason": "宣告破產",
      "summary": "抗告人旺締開發建設有限公司因無力支付營運管銷及所積欠之債務，現已停止營業，無繼續性收入可清償債務，且因積欠銀行債務未清償，屬信用不良狀態，無法再融通資金周轉，已陷於無支付能力。原裁定認定抗告人之財產價值高於債務額，而駁回抗告人之聲請，抗告人提起抗告。本院認為原裁定未見及抗告人目前資產狀況已無法清償債務，符合不能清償債務之情，尚非全然無據，故將原裁定廢棄，發回臺灣高雄地方法院。",
      "factual_issues": [
        "抗告人旺締開發建設有限公司因無力支付營運管銷及所積欠之債務，現已停止營業，無繼續性收入可清償債務。",
        "因積欠銀行債務未清償，屬信用不良狀態，無法再融通資金周轉，已陷於無支付能力。",
        "原裁定認定抗告人之財產價值高於債務額，而駁回抗告人之聲請。"
      ],
      "legal_holdings": [{
          "category": "破產法",
          "granularity": "上位階法律原則",
          "text": "破產，對債務人不能清償債務者宣告之；對於破產之聲請，在裁定前，法院得依職權為必要之調查，並傳訊債務人、債權人及其他關係人，破產法第57條、第63條第2項分別定有明文。"
        },{
          "category": "破產法",
          "granularity": "實務見解",
          "text": "法院就破產之聲請，應依職權為必要之調查，倘債務人確係毫無財產可構成破產財團，或債務人之財產不敷清償破產財團之費用及財團之債務，而無從依破產程序清理其債務時，始得以無宣告破產之實益，裁定駁回聲請。"
        }]
    }]
else:
    all_cases_data = load_all_json_data(DATA_FOLDER)

# --- 側邊欄 (Sidebar) ---
st.sidebar.title("案件列表")
st.sidebar.markdown(f"共找到 **{len(all_cases_data)}** 筆案件")

# 【需求1】建立一個以 "案號" 為選項的條列式清單
case_numbers = [case.get("case_number", "未知案號") for case in all_cases_data]
# 使用 st.radio 來建立一個不能收合的選擇列表
selected_case_number = st.sidebar.radio(
    "請選擇要檢視的案件：", 
    options=case_numbers,
    label_visibility="collapsed" # 隱藏 radio 上方的標籤，讓版面更乾淨
)

# 根據選擇的案號，找到對應的完整資料
selected_case_data = next((case for case in all_cases_data if case.get("case_number") == selected_case_number), None)


# --- 主畫面 (Main Panel) ---
if selected_case_data:
    # 【需求4】將案件標題加上 URL
    case_number_display = selected_case_data.get('case_number', '')
    case_url = selected_case_data.get('url')
    if case_url:
        st.header(f"案件詳情：[{case_number_display}]({case_url})", divider='rainbow')
    else:
        st.header(f"案件詳情：{case_number_display}", divider='rainbow')
    
    # 【需求2】刪除裁判日期，只顯示案由
    st.metric(label="案由", value=selected_case_data.get('case_reason', 'N/A'))
    
    st.divider()

    # 顯示案件摘要 (使用 expander 讓使用者可以展開或收合)
    with st.expander("案件摘要", expanded=True):
        st.write(selected_case_data.get('summary', '無摘要資訊'))

    # 顯示事實爭點
    st.subheader("事實爭點")
    factual_issues = selected_case_data.get('factual_issues', [])
    if factual_issues:
        for issue in factual_issues:
            st.markdown(f"- {issue}")
    else:
        st.info("此案件無事實爭點資訊。")
    
    st.divider()

    # 【需求3】法律見解的欄位變小，類似事實爭點
    st.subheader("法律見解")
    legal_holdings = selected_case_data.get('legal_holdings', [])
    if legal_holdings:
        for holding in legal_holdings:
            category = holding.get('category', '無分類')
            granularity = holding.get('granularity', '無位階')
            text = holding.get('text', '無內容')
            # 將所有資訊用 markdown 格式化成一行，更簡潔
            st.markdown(f"- **【{category} - {granularity}】** {text}")
    else:
        st.info("此案件無法律見解資訊。")

else:
    st.info("請從左側側邊欄選擇一個案件以檢視其詳細資訊。")

