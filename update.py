from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta

TARGET_URL = "https://fortnitetracker.com/events"

def calculate_time(status_text, fallback_days, region):
    now = datetime.utcnow()
    region_utc_hours = {
        "ASIA": 9, "OCE": 8, "ME": 15, "EU": 17, 
        "BR": 21, "NAE": 23, "NAC": 0, "NAW": 2, "ALL": 9
    }
    
    num_match = re.search(r'\d+', status_text)
    if num_match:
        num = int(num_match.group())
        text_lower = status_text.lower()
        if "hr" in text_lower or "hour" in text_lower:
            return now + timedelta(hours=num)
        elif "min" in text_lower:
            return now + timedelta(minutes=num)
        elif "day" in text_lower:
            target_date = now + timedelta(days=num)
            target_hour = region_utc_hours.get(region.upper(), 9)
            if target_hour < 6:
                target_date += timedelta(days=1)
            return target_date.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    
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
                pass
            
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
                name_lower = name.lower()
                
                # PRの判定
                pr_keywords = ['fncs', 'cash cup', 'victory cup', 'major', 'grand']
                non_pr_keywords = ['ranked', 'evaluation', 'mix-up', 'community', 'mobile series', 'lightning', 'playstation', 'xbox', 'console']
                is_pr = any(k in name_lower for k in pr_keywords)
                if any(k in name_lower for k in non_pr_keywords):
                    is_pr = False
                if "fncs" in name_lower and "community" not in name_lower:
                    is_pr = True

                # 🎮 ここが新機能！大会名から「機種」を推測する
                platforms_str = "all"
                original_platforms = "全機種"
                
                if "mobile" in name_lower or "switch" in name_lower or "touch" in name_lower:
                    platforms_str = "mobile, switch"
                    original_platforms = "モバイル/Switch"
                elif "console" in name_lower or "playstation" in name_lower or "xbox" in name_lower or "ps4" in name_lower or "ps5" in name_lower:
                    platforms_str = "console, ps, xbox"
                    original_platforms = "コンソール (PS/Xbox)"
                elif re.search(r'\bpc\b', name_lower): # 「PC」という単語が含まれているか
                    platforms_str = "pc"
                    original_platforms = "PC"

                item_elements = event_html.select('.fne-poster__items .fne-poster__item')
                
                if item_elements:
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
                        
                        begin_time = calculate_time(status_text, idx, reg)
                        end_time = begin_time + timedelta(hours=3)
                        
                        processed_events.append({
                            "id": f"{idx}-{reg}", "name": name, "region": reg,
                            "platformsStr": platforms_str, # 推測した機種をセット
                            "originalPlatforms": original_platforms,
                            "beginTime": begin_time.isoformat() + "Z",
                            "endTime": end_time.isoformat() + "Z",
                            "isPR": is_pr, "condition": "Trackerまたはゲーム内で確認"
                        })
                else:
                    region_elem = event_html.select_one('.fne-poster__region')
                    reg_text = region_elem.text.strip().upper() if region_elem else "ASIA"
                    reg = "ALL" if "MULTI" in reg_text else reg_text
                    
                    status_elem = event_html.select_one('.fne-poster__status')
                    status_text = status_elem.text.strip() if status_elem else ""
                    if "ended" in status_text.lower() or "終了" in status_text: continue
                        
                    begin_time = calculate_time(status_text, idx, reg)
                    end_time = begin_time + timedelta(hours=3)
                    
                    processed_events.append({
                        "id": str(idx), "name": name, "region": reg,
                        "platformsStr": platforms_str, # 推測した機種をセット
                        "originalPlatforms": original_platforms,
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
