import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# --- 設定 ---

# 包含所有網址的檔案名稱
URL_FILE = 'url.txt'

# 儲存結果的資料夾名稱
OUTPUT_DIR = 'selenium_scraped_txt' # 資料夾名稱改為 _txt 以示區別

# 您指定的 XPath
XPATH_SELECTOR = '/html/body/form/div[3]/div[3]/div[1]' 

# 每個頁面載入後等待的秒數
WAIT_SECONDS = 2


def download_with_selenium():
    """
    主執行函式：使用 Selenium 讀取網址，抓取網址與指定區塊的HTML，並儲存為 TXT 檔案。
    """
    # 檢查 url.txt 是否存在
    if not os.path.exists(URL_FILE):
        print(f"錯誤：找不到檔案 '{URL_FILE}'。請檢查檔案是否存在於目前目錄。")
        return

    # 建立儲存結果的資料夾
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"所有抓取到的內容將會儲存在 '{OUTPUT_DIR}' 資料夾中。")

    # 讀取所有網址
    with open(URL_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"從 '{URL_FILE}' 中讀取到 {len(urls)} 個網址。")
    
    # 初始化 Chrome 瀏覽器
    driver = webdriver.Chrome()
    print("Chrome 瀏覽器已啟動...")
    print("-" * 20)

    try:
        # 迴圈處理每一個網址
        for i, url in enumerate(urls):
            print(f"正在處理第 {i+1}/{len(urls)} 個網址: {url}")

            # 瀏覽器前往目標網址
            driver.get(url)

            # 等待幾秒讓動態內容渲染
            print(f"頁面載入，等待 {WAIT_SECONDS} 秒...")
            time.sleep(WAIT_SECONDS)

            try:
                # 使用 XPath 尋找指定的元素
                content_element = driver.find_element(By.XPATH, XPATH_SELECTOR)
                
                # 提取該元素的完整 HTML
                content_html = content_element.get_attribute('innerText')

                # 建立輸出檔案名稱，副檔名改回 .txt
                output_filename = os.path.join(OUTPUT_DIR, f'content_{i+1}.txt')

                # --- 【修改點】---
                # 將網址和 HTML 內容寫入同一個 txt 檔案
                with open(output_filename, 'w', encoding='utf-8') as outfile:
                    # 第一行寫入來源網址
                    outfile.write(f"{url}\n")
                    # 第二行寫入分隔線
                    outfile.write("---\n")
                    # 接著寫入完整的 HTML 內容
                    outfile.write(content_html)

                print(f"成功提取資料並儲存至 '{output_filename}'\n")

            except NoSuchElementException:
                print(f"警告：在此網址上找不到指定的 XPath 元素: {url}\n")
            
    finally:
        # 無論程式是否出錯，最後都確保關閉瀏覽器
        print("所有網址處理完畢，關閉瀏覽器。")
        driver.quit()

# 當這個檔案被直接執行時，才執行主函式
if __name__ == "__main__":
    download_with_selenium()