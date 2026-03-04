from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta

TARGET_URL = "https://fortnitetracker.com/events"

# 時間を計算する専用の関数
def calculate_time(status_text, fallback_days):
    begin_time = datetime.utcnow()
    num_match = re.search(r'\d+', status_text)
    if num_match:
        num = int(num_match.group())
        text_lower = status_text.lower()
        if "hr" in text_lower or "hour" in text_lower:
            begin_time += timedelta(hours=num)
        elif "day" in text_lower:
            begin_time += timedelta(days=num)
        elif "min" in text_lower:
            begin_time += timedelta(minutes=num)
    else:
        begin_time += timedelta(days=fallback_days)
    return begin_time

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
                
                # 🎯 ここが新機能！地域ごとの詳細リストがあるかチェック
                item_elements = event_html.select('.fne-poster__items .fne-poster__item')
                
                if item_elements:
                    # Multi大会の場合：地域ごとに分割して個別の大会として保存する
                    for item in item_elements:
                        region_label = item.select_one('.fne-poster__item-label')
                        if not region_label:
                            continue
                        
                        reg_text = region_label.text.strip().upper()
                        # サイトの長い表記を、フィルター用の短い表記（ASIA, EU, NAC...）に翻訳
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
                        
                        if "ended" in status_text.lower() or "終了" in status_text:
                            continue
                        
                        # その地域専用の時間を計算
                        begin_time = calculate_time(status_text, idx)
                        end_time = begin_time + timedelta(hours=3)
                        
                        processed_events.append({
                            "id": f"{idx}-{reg}",
                            "name": name,
                            "region": reg,
                            "platformsStr": "all",
                            "originalPlatforms": "全機種",
                            "beginTime": begin_time.isoformat() + "Z",
                            "endTime": end_time.isoformat() + "Z",
                            "isPR": is_pr,
                            "condition": "Trackerまたはゲーム内で確認"
                        })
                else:
                    # 単一地域の大会の場合は今まで通り
                    region_elem = event_html.select_one('.fne-poster__region')
                    reg_text = region_elem.text.strip().upper() if region_elem else "ASIA"
                    reg = "ALL" if "MULTI" in reg_text else reg_text
                    
                    status_elem = event_html.select_one('.fne-poster__status')
                    status_text = status_elem.text.strip() if status_elem else ""
                    
                    if "ended" in status_text.lower() or "終了" in status_text:
                        continue
                        
                    begin_time = calculate_time(status_text, idx)
                    end_time = begin_time + timedelta(hours=3)
                    
                    processed_events.append({
                        "id": str(idx),
                        "name": name,
                        "region": reg,
                        "platformsStr": "all",
                        "originalPlatforms": "全機種",
                        "beginTime": begin_time.isoformat() + "Z",
                        "endTime": end_time.isoformat() + "Z",
                        "isPR": is_pr,
                        "condition": "Trackerまたはゲーム内で確認"
                    })
            except Exception as e:
                pass

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！取得件数:", len(processed_events))

    except Exception as e:
        print(f"❌ 致命的なエラーが発生しました: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
