import os
import json
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
PROMPT_FILE_PATH = f"{os.getcwd()}/summarize.txt"


# --- Pydantic 模型定義 (與前一版相同，保持不變) ---

class LegalHoldingMVP(BaseModel):
    """(MVP版) 單一法律見解的極簡結構"""
    category: str = Field(..., description="LLM 建議的法律領域分類", example="證據法")
    granularity: str = Field(..., description="見解的顆粒度層級", example="具體見解")
    text: str = Field(..., description="獨立自足、去脈絡化的法律見解陳述句")

class AnalyzedDecisionMVP(BaseModel):
    """(MVP版) 一份判決書經 LLM 分析後的核心資料模型"""
    url: str = Field(..., description="該判決書的來源 URL")
    case_number: str = Field(..., description="案件的裁判字號")
    case_reason: str = Field(..., description="裁判案由")
    summary: str = Field(..., description="由 LLM 生成的案件摘要")
    factual_issues: List[str] = Field(..., description="從判決中提煉出的事實爭點列表")
    legal_holdings: List[LegalHoldingMVP] = Field(..., description="法律見解 (Headnotes) 列表")


# --- 輔助函數 ---

def get_openai_api_key() -> str:
    """從環境變數獲取 OpenAI API 金鑰"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("錯誤：請將您的 OpenAI API 金鑰設為環境變數 OPENAI_API_KEY")
    return api_key

def get_txt_files(folder: str) -> List[str]:
    """獲取指定文件夾中所有的 .txt 文件路徑"""
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.txt')]

def load_system_prompt(file_path: str) -> str:
    """從外部檔案載入 System Prompt"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"錯誤：System Prompt 檔案 '{file_path}' 不存在。請確認檔案路徑是否正確。")
        raise

def call_gpt4(client: OpenAI, content: str, system_prompt: str) -> Optional[str]:
    """使用載入的 System Prompt 呼叫 GPT-4"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"呼叫 OpenAI API 時發生錯誤：{e}")
        return None

# --- 主執行流程 ---

def main():
    try:
        api_key = get_openai_api_key()
        client = OpenAI(api_key=api_key)
        
        # 定義檔案路徑
        input_folder = "selenium_scraped_txt"
        output_folder = "corpus/summary"
        prompt_file_path = "summarize.txt" # 將 prompt 檔案路徑變數化
        
        # 在迴圈外一次性載入 System Prompt，提升效率
        print(f"從 '{prompt_file_path}' 載入 System Prompt...")
        system_prompt = load_system_prompt(prompt_file_path)
        
        os.makedirs(output_folder, exist_ok=True)
        txt_files = get_txt_files(input_folder)
        
        if not txt_files:
            print(f"警告：在資料夾 '{input_folder}' 中找不到任何 .txt 檔案。")
            return

        for txt_path in txt_files:
            print(f"--- 開始處理 {txt_path} ---")
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    url = f.readline().strip()
                    content = f.read()

                if not url or not content:
                    print(f"警告：{txt_path} 的 URL 或內容為空，跳過處理。")
                    continue

                gpt_output = call_gpt4(client, content, system_prompt)
                
                if not gpt_output:
                    print(f"錯誤：從 OpenAI 未收到回應，處理失敗。")
                    continue

                data = json.loads(gpt_output)
                data['url'] = url
                
                analyzed = AnalyzedDecisionMVP(**data)
                
                base_name = os.path.splitext(os.path.basename(txt_path))[0]
                out_path = os.path.join(output_folder, f"{base_name}.json")
                
                with open(out_path, "w", encoding="utf-8") as out_f:
                    out_f.write(analyzed.model_dump_json(indent=2))
                    
                print(f"成功儲存分析結果至 {out_path}")

            except json.JSONDecodeError as e:
                print(f"JSON 解析錯誤：{e}\n收到的原始輸出：\n{gpt_output}")
            except ValidationError as e:
                print(f"Pydantic 驗證錯誤：{e}")
            except Exception as e:
                print(f"處理檔案時發生未預期的錯誤：{e}")
            finally:
                print(f"--- 完成處理 {txt_path} ---\n")

    except ValueError as e:
        # 捕捉 API Key 或 Prompt 檔案不存在的錯誤
        print(e)
    except Exception as e:
        print(f"程式執行時發生嚴重錯誤：{e}")

if __name__ == "__main__":
    main()
