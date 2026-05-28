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
    requests.post(url, json=payload)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://comp.wisereport.co.kr/wiseReport/summary/ReportSummary.aspx"
        page.goto(url)
        page.wait_for_timeout(5000) # 데이터 로딩 대기
        
        try:
            # 1. 리포트 테이블의 모든 데이터 행(Row) 가져오기
            rows = page.locator("tr.itm_t1, tr.alt_t1").all()
            
            # 이전에 보냈던 리포트 목록 불러오기 (중복 발송 방지용)
            sent_list = []
            if os.path.exists("last_title.txt"):
                with open("last_title.txt", "r", encoding="utf-8") as f:
                    sent_list = f.read().splitlines()
            
            new_reports = []
            
            # 2. 각 행을 순회하며 원하는 데이터 추출
            for row in rows:
                cols = row.locator("th, td")
                
                # 기업명 추출 (예: "포스코퓨처엠\n(003670)" -> "포스코퓨처엠" 만 잘라냄)
                company_raw = cols.nth(0).inner_text().strip()
                company = company_raw.split('\n')[0].strip() if '\n' in company_raw else company_raw
                
                # 목표주가 및 등락 여부 추출
                # html 구조상 4번째 열(nth(3))의 첫 번째 div에 '목표주가 상향', '변동없음' 등의 title 속성이 있음
                trend_elem = cols.nth(3).locator("div[title]").first
                trend_raw = trend_elem.get_attribute("title") if trend_elem.count() > 0 else "상태없음"
                trend = trend_raw.replace("목표주가 ", "") # "목표주가 상향" -> "상향" 으로 텍스트 다이어트
                
                price = cols.nth(3).locator(".content04").inner_text().strip()
                
                # 제목 추출 (6번째 열)
                title = cols.nth(5).inner_text().strip()
                
                # 중복 식별용 고유 키 (기업명 + 제목)
                unique_key = f"{company}::{title}"
                
                # 처음 보는 신규 리포트인 경우에만 추가
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

        # 3. 새로 업데이트된 내역이 없다면 조용히 종료
        if not new_reports:
            print("새로운 업데이트가 없습니다.")
            browser.close()
            return
            
        # 4. 신규 리포트가 있다면 기업별로 그룹화 (하루에 동일 기업 리포트가 여러 개일 경우 대비)
        grouped = {}
        for r in new_reports:
            c = r["company"]
            if c not in grouped:
                grouped[c] = []
            grouped[c].append(r)
            
        # 5. 텔레그램 메시지 조립
        msg = "🚨 <b>와이즈리포트 신규 업데이트</b>\n\n"
        for comp, reports in grouped.items():
            # 리포트가 2개 이상이면 기업명 옆에 (개수) 표기
            count_str = f" ({len(reports)})" if len(reports) > 1 else ""
            msg += f"🏢 <b>{comp}</b>{count_str}\n"
            
            for rep in reports:
                msg += f" ├ 📌 {rep['title']}\n"
                msg += f" └ 🎯 {rep['price']}원 ({rep['trend']})\n"
            msg += "\n"
            
        msg += f"🔗 <a href='{url}'>와이즈리포트 전체 목록 보러가기</a>"
        
        # 알림 발송
        send_telegram_message(msg)
        
        # 6. 다음 번 검사 때 중복 알림을 막기 위해 오늘 보낸 리스트 업데이트
        # 파일이 무한히 커지는 것을 막기 위해 최근 200개까지만 기억하도록 제한
        all_keys = sent_list + [r["key"] for r in new_reports]
        with open("last_title.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_keys[-200:]))
            
        browser.close()

if __name__ == "__main__":
    main()
