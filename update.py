from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta

TARGET_URL = "https://fortnitetracker.com/events"

# 🎯 時間計算を大幅に強化した関数
def calculate_time(status_text, fallback_days, region):
    now = datetime.utcnow()
    
    # 各地域ごとの「よくある開始時間」をUTC（世界標準時）で設定
    # ASIAは日本時間18:00（UTC09:00）をデフォルトにする
    region_utc_hours = {
        "ASIA": 9,   # JST 18:00
        "OCE": 8,    # AEST 18:00
        "ME": 15,    # AST 18:00
        "EU": 17,    # CET 18:00
        "BR": 21,    # BRT 18:00
        "NAE": 23,   # EST 18:00
        "NAC": 0,    # CST 18:00 (UTCだと翌日の0時)
        "NAW": 2,    # PST 18:00 (UTCだと翌日の2時)
        "ALL": 9     # 指定がない場合は日本時間18時
    }
    
    num_match = re.search(r'\d+', status_text)
    if num_match:
        num = int(num_match.group())
        text_lower = status_text.lower()
        
        if "hr" in text_lower or "hour" in text_lower:
            # 「○時間後」と書かれている場合は、今の時間から正確に足し算
            return now + timedelta(hours=num)
        elif "min" in text_lower:
            return now + timedelta(minutes=num)
        elif "day" in text_lower:
            # 「○日後」という大雑把な表記の場合は、日付だけ足して、時間は強制的に地域の18:00に合わせる
            target_date = now + timedelta(days=num)
            target_hour = region_utc_hours.get(region.upper(), 9)
            
            # NACやNAWなど、UTC基準だと翌日になってしまう地域の微調整
            if target_hour < 6:
                target_date += timedelta(days=1)
                
            return target_date.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    
    # 日時が不明な場合の保険
    target_date = now + timedelta(days=fallback_days)
    target_hour = region_utc_hours.get(region.upper(), 9)
    if target_hour < 6:
        target_date += timedelta(days=1)
    return target_date.replace(hour=target_hour, minute=0, second=0, microsecond=0)

def scrape_tournaments():
    print(f"[{datetime.now()}] Playwrightでスクレイピングを開始します: {TARGET_URL}")
    
    html = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="ja-JP"
            )
            
            page = context.new_page()
            print("ページにアクセスしています...")
            try:
                page.goto(TARGET_URL, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"⚠️ 読み込み遅延。強制突破します: {e}")
            
            page.wait_for_timeout(10000) 
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        processed_events = []
        event_elements = soup.select('.fne-poster') 
        
        for idx, event_html in enumerate(event_elements):
            try:
                name_elem = event_html.select_one('.fne-poster__title')
                name = name_elem.text.strip() if name_elem else f"不明な大会 {idx}"
                is_pr = any(keyword in name.lower() for keyword in ['cup', 'fncs', 'cash', 'major', 'pr'])
                
                item_elements = event_html.select('.fne-poster__items .fne-poster__item')
                
                if item_elements:
                    # Multi大会（全地域）の処理
                    for item in item_elements:
                        region_label = item.select_one('.fne-poster__item-label')
                        if not region_label: continue
                        
                        reg_text = region_label.text.strip().upper()
                        if "EUROPE" in reg_text: reg = "EU"
                        elif "ASIA" in reg_text: reg = "ASIA"
                        elif "CENTRAL" in reg_text: reg = "NAC"
                        elif "WEST" in reg_text: reg = "NAW"
                        elif "EAST" in reg_text: reg = "NAE"
                        elif "MIDDLE" in reg_text: reg = "ME"
                        elif "OCEANIA" in reg_text: reg = "OCE"
                        elif "BRAZIL" in reg_text: reg = "BR"
                        else: reg = reg_text
                        
                        status_elem = item.select_one('.fne-status')
                        status_text = status_elem.text.strip() if status_elem else ""
                        if "ended" in status_text.lower() or "終了" in status_text: continue
                        
                        # 地域(reg)を渡して、その地域に合った正確な時間を計算！
                        begin_time = calculate_time(status_text, idx, reg)
                        end_time = begin_time + timedelta(hours=3)
                        
                        processed_events.append({
                            "id": f"{idx}-{reg}", "name": name, "region": reg,
                            "platformsStr": "all", "originalPlatforms": "全機種",
                            "beginTime": begin_time.isoformat() + "Z",
                            "endTime": end_time.isoformat() + "Z",
                            "isPR": is_pr, "condition": "Trackerまたはゲーム内で確認"
                        })
                else:
                    # 単一地域の大会の処理
                    region_elem = event_html.select_one('.fne-poster__region')
                    reg_text = region_elem.text.strip().upper() if region_elem else "ASIA"
                    reg = "ALL" if "MULTI" in reg_text else reg_text
                    
                    status_elem = event_html.select_one('.fne-poster__status')
                    status_text = status_elem.text.strip() if status_elem else ""
                    if "ended" in status_text.lower() or "終了" in status_text: continue
                        
                    # 地域(reg)を渡して正確な時間を計算！
                    begin_time = calculate_time(status_text, idx, reg)
                    end_time = begin_time + timedelta(hours=3)
                    
                    processed_events.append({
                        "id": str(idx), "name": name, "region": reg,
                        "platformsStr": "all", "originalPlatforms": "全機種",
                        "beginTime": begin_time.isoformat() + "Z",
                        "endTime": end_time.isoformat() + "Z",
                        "isPR": is_pr, "condition": "Trackerまたはゲーム内で確認"
                    })
            except Exception as e:
                pass

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！")

    except Exception as e:
        print(f"❌ 致命的なエラー: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
