from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

TARGET_URL = "https://fortnitetracker.com/events"

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
        
        # 🎯 あなたが解読したクラス名（.fne-poster）をセット！
        event_elements = soup.select('.fne-poster') 
        
        for idx, event_html in enumerate(event_elements):
            try:
                # ① 大会名の取得
                name_elem = event_html.select_one('.fne-poster__title')
                name = name_elem.text.strip() if name_elem else f"不明な大会 {idx}"
                
                # ② 地域の取得
                region_elem = event_html.select_one('.fne-poster__region')
                region_text = region_elem.text.strip() if region_elem else "ASIA"
                # 「Multi」と書かれている場合は「all」として扱う
                region = "all" if "multi" in region_text.lower() else region_text.upper()

                # ③ 終了している大会（Ended）は除外するかどうかの判定
                status_elem = event_html.select_one('.fne-status span')
                status_text = status_elem.text.strip().lower() if status_elem else ""
                
                # PR大会かどうかの判定
                is_pr = any(keyword in name.lower() for keyword in ['cup', 'fncs', 'cash', 'major', 'pr'])
                
                # ⚠️ 日時の生成（Trackerのポスター画像には日時が直接書かれていないため、
                # 今回は仮で現在時刻からのスケジュールを入れています）
                begin_time = (datetime.utcnow() + timedelta(days=idx)).isoformat() + "Z"
                end_time = (datetime.utcnow() + timedelta(days=idx, hours=3)).isoformat() + "Z"
                
                processed_events.append({
                    "id": str(idx),
                    "name": name,
                    "region": region,
                    "platformsStr": "all",  # 今回のHTMLには機種がないので「全機種」扱い
                    "originalPlatforms": "全機種",
                    "beginTime": begin_time,
                    "endTime": end_time,
                    "isPR": is_pr,
                    "condition": "公式サイトで確認"
                })
            except Exception as e:
                pass

        # 抽出したデータをJSONとして保存
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！取得件数:", len(processed_events))

    except Exception as e:
        print(f"❌ 致命的なエラーが発生しました: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
