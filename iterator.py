import streamlit as st
import json
import uuid
import os
import openai
from dotenv import load_dotenv
from pydantic import BaseModel, create_model, ValidationError
from typing import List, Optional, Type

# --- 0. 環境設定與 OpenAI 初始化 ---
# 載入 .env 檔案中的環境變數
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 檢查 API 金鑰是否存在
IS_API_KEY_VALID = OPENAI_API_KEY is not None and OPENAI_API_KEY.startswith("sk-")

if IS_API_KEY_VALID:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
else:
    # 如果金鑰無效，先不建立 client，稍後在 UI 中顯示錯誤
    client = None

# 定義提示詞與文件範本的存檔路徑
SYSTEM_PROMPT_FILE_PATH = "system_prompt.txt"
USER_PROMPT_FILE_PATH = "user_prompt.txt"

# --- 1. 核心輔助函式 ---

def render_fields_recursively(fields_dict, path_prefix):
    """
    遞迴地渲染欄位。
    """
    for field_id, field_data in list(fields_dict.items()):
        unique_key_prefix = f"{path_prefix}_{field_id}"
        cols = st.columns([5, 4, 3, 1])
        field_data['name'] = cols[0].text_input("欄位名稱", value=field_data['name'], key=f"{unique_key_prefix}_name", label_visibility="collapsed")
        field_types_options = ['文字', '日期', '數字', '物件 (Object)']
        field_data['type'] = cols[1].selectbox("欄位類型", options=field_types_options, index=field_types_options.index(field_data['type']), key=f"{unique_key_prefix}_type", label_visibility="collapsed")
        is_object_type = field_data['type'] == '物件 (Object)'
        field_data['allow_multiple'] = cols[2].checkbox("允許多個值", value=field_data['allow_multiple'], key=f"{unique_key_prefix}_multi", help="勾選後，此欄位將被視為一個列表 (List)")
        if cols[3].button("❌", key=f"{unique_key_prefix}_del", help="刪除此欄位"):
            del fields_dict[field_id]
            st.rerun()
        if is_object_type:
            with st.container(border=True):
                st.markdown(f"📄 **'{field_data['name'] or '未命名物件'}'** 的子欄位結構")
                render_fields_recursively(field_data['sub_fields'], path_prefix=unique_key_prefix)
                if st.button("⊕ 新增子欄位", key=f"{unique_key_prefix}_add_sub", use_container_width=True):
                    new_sub_field_id = str(uuid.uuid4())
                    field_data['sub_fields'][new_sub_field_id] = {'id': new_sub_field_id, 'name': '', 'type': '文字', 'allow_multiple': False, 'sub_fields': {}}
                    st.rerun()

def generate_pydantic_model(model_name: str, schema_fields: dict) -> Type[BaseModel]:
    """
    從 UI 定義的 schema 字典，遞迴地動態生成一個 Pydantic 模型。
    """
    field_definitions = {}
    type_mapping = {'文字': str, '日期': str, '數字': int}
    for field_data in schema_fields.values():
        field_name = field_data.get('name')
        if not field_name: continue
        field_type_str = field_data['type']
        is_list = field_data.get('allow_multiple', False)
        if field_type_str == '物件 (Object)':
            nested_model_name = f"{model_name}_{field_name}"
            field_type = generate_pydantic_model(nested_model_name, field_data['sub_fields'])
        else:
            field_type = type_mapping.get(field_type_str, str)
        final_type = List[field_type] if is_list else field_type
        field_definitions[field_name] = (Optional[final_type], None)
    return create_model(model_name, **field_definitions)

def render_results_dynamically(data: dict):
    """
    優雅地呈現分析結果。
    """
    for key, value in data.items():
        st.subheader(f"🏷️ {key}")
        if isinstance(value, list):
            if not value: st.write("_(無資料)_")
            elif value and isinstance(value[0], dict): st.dataframe(value, use_container_width=True)
            else:
                for item in value: st.markdown(f"- {item}")
        elif isinstance(value, dict):
            with st.container(border=True): render_results_dynamically(value)
        else: st.write(value)

def load_from_file(file_path):
    """
    如果檔案存在則讀取，否則回傳 None。
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def save_to_file(file_path, content):
    """
    將內容儲存至檔案。
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    st.toast(f"已成功儲存至 {os.path.basename(file_path)}！")

# --- 2. 頁面設定與狀態初始化 ---
st.set_page_config(page_title="整合式法律文件分析器", layout="wide")
st.title("⚖️ 整合式法律文件分析器")

if not IS_API_KEY_VALID:
    st.error("⚠️ 找不到有效的 OpenAI API 金鑰！")
    st.info("請在專案目錄下建立一個名為 .env 的檔案，並在其中加入您的金鑰：`OPENAI_API_KEY='sk-...'`")
    st.stop()

st.info("請依序完成設定並輸入文件內容，然後點擊最下方的按鈕執行分析。")

# 僅在 session_state 第一次初始化時執行
if 'initialized' not in st.session_state:
    # 嘗試從檔案載入，如果檔案不存在，則使用預設值
    system_prompt_content = load_from_file(SYSTEM_PROMPT_FILE_PATH)
    user_prompt_content = load_from_file(USER_PROMPT_FILE_PATH)
    st.session_state.system_prompt = system_prompt_content
    st.session_state.user_prompt = user_prompt_content
    st.session_state.selected_model = "gpt-4.1" # 您的預設模型
    st.session_state.fields = {
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '案號/案由', 'type': '文字', 'allow_multiple': False, 'sub_fields': {}},
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '判決日期', 'type': '日期', 'allow_multiple': False, 'sub_fields': {}},
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '當事人', 'type': '文字', 'allow_multiple': True, 'sub_fields': {}},
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '主文', 'type': '文字', 'allow_multiple': False, 'sub_fields': {}},
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '事實概要', 'type': '文字', 'allow_multiple': False, 'sub_fields': {}},
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '爭點', 'type': '文字', 'allow_multiple': True, 'sub_fields': {}},
        str(uuid.uuid4()): {'id': str(uuid.uuid4()), 'name': '判決理由', 'type': '文字', 'allow_multiple': False, 'sub_fields': {}},
    }
    st.session_state.initialized = True


# --- 3. 主渲染流程 ---

# 步驟 1: 系統與模型設定
st.header("1. 系統與模型設定")
system_prompt_input = st.text_area("系統提示詞 (System Prompt)", value=st.session_state.system_prompt, height=200, key="system_prompt_widget")
if st.button("💾 儲存提示詞", help=f"將目前的提示詞儲存至 {SYSTEM_PROMPT_FILE_PATH}"):
    save_to_file(SYSTEM_PROMPT_FILE_PATH, system_prompt_input)
    st.session_state.system_prompt = system_prompt_input # 更新 session state

# PRESERVED: 保留您指定的模型列表
model_options = ["gpt-4.1", "gpt-4o", "o4-mini"]
st.session_state.selected_model = st.selectbox("選擇 OpenAI 模型", options=model_options, index=model_options.index(st.session_state.selected_model))

# 步驟 2: 輸出結構設定
st.header("2. 輸出結構設定")
cols = st.columns([5, 4, 3, 1])
cols[0].markdown("**欄位名稱**")
cols[1].markdown("**欄位類型**")
cols[2].markdown("**允許多個值**")
cols[3].markdown("**刪除**")
render_fields_recursively(st.session_state.fields, path_prefix="root")
if st.button("➕ 新增欄位", use_container_width=True):
    new_field_id = str(uuid.uuid4())
    st.session_state.fields[new_field_id] = {'id': new_sub_field_id, 'name': '', 'type': '文字', 'allow_multiple': False, 'sub_fields': {}}
    st.rerun()

# 步驟 3: 法律文件內文
st.header("3. 法律文件內文 (User Prompt)")
user_prompt_input = st.text_area("貼上您的法律文件內容：", height=300, value=st.session_state.user_prompt, key="user_prompt_widget")
if st.button("💾 儲存文件範本", help=f"將目前的文件內容儲存為預設範本至 {USER_PROMPT_FILE_PATH}"):
    save_to_file(USER_PROMPT_FILE_PATH, user_prompt_input)
    st.session_state.user_prompt = user_prompt_input # 更新 session state

st.divider()

# 步驟 4: 執行與輸出
if st.button("🚀 執行分析", type="primary", use_container_width=True):
    with st.spinner(f"正在使用 `{st.session_state.selected_model}` 模型進行分析..."):
        try:
            # 從 session state 獲取最新值
            system_prompt = st.session_state.system_prompt
            raw_input_text = user_prompt_input # 從 widget 直接獲取當前值
            
            DynamicPydanticModel = generate_pydantic_model('DynamicOutputModel', st.session_state.fields)
            pydantic_schema = json.dumps(DynamicPydanticModel.model_json_schema(), ensure_ascii=False, indent=2)
            final_prompt = f"""
            這是需要分析的法律文件：
            ---文件開始---
            {raw_input_text}
            ---文件結束---

            請根據上述文件內容，嚴格按照以下 JSON Schema 格式提取資訊並回傳。
            你的回覆必須是一個格式完全正確的 JSON 物件，不要包含任何額外說明或 ```json ``` 標籤。

            JSON Schema:
            {pydantic_schema}
            """
            response = client.chat.completions.create(
                model=st.session_state.selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt}
                ],
                response_format={"type": "json_object"}
            )
            api_response_str = response.choices[0].message.content
            st.session_state.raw_json_output = json.loads(api_response_str)
            validated_data = DynamicPydanticModel(**st.session_state.raw_json_output)
            st.session_state.validated_pydantic_object = validated_data
            st.success("分析完成！")
        except openai.APIError as e: st.error(f"OpenAI API 錯誤: {e}")
        except json.JSONDecodeError: st.error("API 回傳的不是有效的 JSON 格式。"); st.code(api_response_str, language="text")
        except ValidationError as e:
            st.error("資料驗證失敗！AI 輸出的 JSON 與您的結構定義不符。")
            st.subheader("收到的 JSON 資料:"); st.json(st.session_state.get('raw_json_output', {}))
            st.subheader("Pydantic 驗證錯誤細節:"); st.text(str(e))
        except Exception as e: st.error(f"發生預期外的錯誤: {e}")

if 'validated_pydantic_object' in st.session_state:
    st.header("4. 分析輸出結果")
    render_results_dynamically(st.session_state.validated_pydantic_object.model_dump())
    with st.expander("點此查看原始 JSON 輸出"):
        st.json(st.session_state.get('raw_json_output', {}))
