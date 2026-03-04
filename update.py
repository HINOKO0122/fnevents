from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import os
import re
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
        
        # あなたが教えてくれた正しいクラス名
        event_elements = soup.select('.fne-poster') 
        
        for idx, event_html in enumerate(event_elements):
            try:
                # ① 大会名の取得
                name_elem = event_html.select_one('.fne-poster__title')
                name = name_elem.text.strip() if name_elem else f"不明な大会 {idx}"
                
                # ② 地域の取得
                region_elem = event_html.select_one('.fne-poster__region')
                region_text = region_elem.text.strip() if region_elem else "ASIA"
                region = "all" if "multi" in region_text.lower() else region_text.upper()

                # ③ 開催状況と日時の計算
                status_elem = event_html.select_one('.fne-poster__status')
                status_text = status_elem.text.strip() if status_elem else ""
                
                # すでに終了している大会（Ended）はスキップする
                if "ended" in status_text.lower() or "終了" in status_text:
                    continue
                
                # 日時を計算する（基準は今の時間）
                begin_time = datetime.utcnow()
                
                # 「In 5 Hrs」や「In 2 Days」の数字だけを抜き出して足し算する
                num_match = re.search(r'\d+', status_text)
                if num_match:
                    num = int(num_match.group())
                    if "Hr" in status_text or "hr" in status_text.lower():
                        begin_time += timedelta(hours=num)
                    elif "Day" in status_text or "day" in status_text.lower():
                        begin_time += timedelta(days=num)
                    elif "Min" in status_text or "min" in status_text.lower():
                        begin_time += timedelta(minutes=num)
                else:
                    # 時間が書いていない場合は順番に少しずつズラす（仮置き）
                    begin_time += timedelta(days=idx)

                # 終了時間は開始時間から「3時間後」と仮定してセット
                end_time = begin_time + timedelta(hours=3)
                
                # PR大会かどうかの判定
                is_pr = any(keyword in name.lower() for keyword in ['cup', 'fncs', 'cash', 'major', 'pr'])
                
                processed_events.append({
                    "id": str(idx),
                    "name": name,
                    "region": region,
                    "platformsStr": "all",
                    "originalPlatforms": "全機種",
                    "beginTime": begin_time.isoformat() + "Z",
                    "endTime": end_time.isoformat() + "Z",
                    "isPR": is_pr,
                    "condition": "Trackerまたはゲーム内で確認"
                })
            except Exception as e:
                print(f"カード解析エラー: {e}")

        # データを保存
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！取得件数:", len(processed_events))

    except Exception as e:
        print(f"❌ 致命的なエラーが発生しました: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
