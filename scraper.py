from playwright.sync_api import sync_playwright
import requests
import os

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://comp.wisereport.co.kr/wiseReport/summary/ReportSummary.aspx"
        page.goto(url)
        
        # 데이터가 로딩될 때까지 잠시 대기
        page.wait_for_timeout(5000)
        
        try:
            # 와이즈리포트의 첫 번째 리포트 요소 가져오기
            # 사이트 구조에 따라 선택자(Selector) 수정이 필요할 수 있습니다.
            first_row = page.locator("table tbody tr").first
            title = first_row.locator("td").nth(1).inner_text().strip()  # 두 번째 열(제목)
            analyst = first_row.locator("td").nth(2).inner_text().strip() # 세 번째 열(작성자)
            
            latest_info = f"{title} ({analyst})"
        except Exception as e:
            print(f"데이터 추출 실패: {e}")
            browser.close()
            return

        # 이전 기록 확인
        last_info = ""
        if os.path.exists("last_title.txt"):
            with open("last_title.txt", "r", encoding="utf-8") as f:
                last_info = f.read().strip()
                
        # 신규 업데이트가 있을 때만 알림
        if latest_info != last_info:
            msg = f"🚨 *와이즈리포트 신규 등록*\n\n📌 *제목:* {title}\n✍️ *작성:* {analyst}\n🔗 [바로가기]({url})"
            send_telegram_message(msg)
            
            # 새로운 정보로 업데이트
            with open("last_title.txt", "w", encoding="utf-8") as f:
                f.write(latest_info)
        else:
            print("새로운 업데이트가 없습니다.")
            
        browser.close()

if __name__ == "__main__":
    main()
