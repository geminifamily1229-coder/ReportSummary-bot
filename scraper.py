from playwright.sync_api import sync_playwright
import requests
import os

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": text, 
        "parse_mode": "HTML",
        "disable_web_page_preview": True 
    }
    response = requests.post(url, json=payload)
    # 텔레그램 서버가 보내온 응답을 로그에 강제로 출력합니다.
    print(f"▶ 텔레그램 서버 응답 코드: {response.status_code}")
    print(f"▶ 텔레그램 서버 응답 본문: {response.text}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://comp.wisereport.co.kr/wiseReport/summary/ReportSummary.aspx"
        page.goto(url)
        page.wait_for_timeout(5000)
        
        try:
            rows = page.locator("tr.itm_t1, tr.alt_t1").all()
            
            sent_list = []
            if os.path.exists("last_title.txt"):
                with open("last_title.txt", "r", encoding="utf-8") as f:
                    sent_list = f.read().splitlines()
            
            new_reports = []
            
            for row in rows:
                cols = row.locator("th, td")
                
                company_raw = cols.nth(0).inner_text().strip()
                company = company_raw.split('\n')[0].strip() if '\n' in company_raw else company_raw
                
                trend_elem = cols.nth(3).locator("div[title]").first
                trend_raw = trend_elem.get_attribute("title") if trend_elem.count() > 0 else "상태없음"
                trend = trend_raw.replace("목표주가 ", "")
                
                price = cols.nth(3).locator(".content04").inner_text().strip()
                title = cols.nth(5).inner_text().strip()
                
                unique_key = f"{company}::{title}"
                
                if unique_key not in sent_list:
                    new_reports.append({
                        "company": company,
                        "price": price,
                        "trend": trend,
                        "title": title,
                        "key": unique_key
                    })
                    
        except Exception as e:
            print(f"데이터 추출 실패: {e}")
            browser.close()
            return

        if not new_reports:
            print("새로운 업데이트가 없습니다.")
            browser.close()
            return
            
        grouped = {}
        for r in new_reports:
            c = r["company"]
            if c not in grouped:
                grouped[c] = []
            grouped[c].append(r)
            
        msg = "🚨 <b>와이즈리포트 신규 업데이트</b>\n\n"
        for comp, reports in grouped.items():
            count_str = f" ({len(reports)})" if len(reports) > 1 else ""
            msg += f"🏢 <b>{comp}</b>{count_str}\n"
            
            for rep in reports:
                msg += f" ├ 📌 {rep['title']}\n"
                msg += f" └ 🎯 {rep['price']}원 ({rep['trend']})\n"
            msg += "\n"
            
        msg += f"🔗 <a href='{url}'>와이즈리포트 전체 목록 보러가기</a>"
        
        # 알림 발송
        send_telegram_message(msg)
        
        all_keys = sent_list + [r["key"] for r in new_reports]
        with open("last_title.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_keys[-200:]))
            
        browser.close()

if __name__ == "__main__":
    main()
