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
        # 人間の代わりにChromeブラウザを裏側で起動する
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 人間が使っているようなブラウザ情報をセット
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            
            print("ページにアクセスしています...")
            page.goto(TARGET_URL, timeout=60000)
            
            # ページ内のデータ（JavaScript）が読み込まれるのを5秒待つ
            page.wait_for_timeout(5000) 
            
            # 読み込み終わった画面のHTML（裏側のコード）をすべて取得
            html = page.content()
            browser.close()
            print("ページの取得に成功しました！解析を開始します。")

        # BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(html, 'html.parser')
        processed_events = []
        
        # 大会情報のブロックを探す（※サイトの仕様に合わせて今後修正が必要な箇所）
        event_elements = soup.select('.event-card, .trn-card') 
        
        for idx, event_html in enumerate(event_elements):
            try:
                name_elem = event_html.select_one('.event-title, .name, h3')
                name = name_elem.text.strip() if name_elem else f"不明な大会 {idx}"
                
                # 日時は仮のものを生成（実際のサイトの構造に合わせて抽出するロジックが必要）
                begin_time = (datetime.utcnow() + timedelta(days=idx)).isoformat() + "Z"
                end_time = (datetime.utcnow() + timedelta(days=idx, hours=3)).isoformat() + "Z"
                
                is_pr = any(keyword in name.lower() for keyword in ['cup', 'fncs', 'cash', 'major', 'pr'])
                
                processed_events.append({
                    "id": str(idx),
                    "name": name,
                    "region": "ASIA",
                    "platformsStr": "all",
                    "originalPlatforms": "全機種",
                    "beginTime": begin_time,
                    "endTime": end_time,
                    "isPR": is_pr,
                    "condition": "公式サイトやTrackerで確認してください"
                })
            except Exception as e:
                print(f"カードの解析中にエラー: {e}")

        if len(processed_events) == 0:
            print("⚠️ ページは取得できましたが、大会データが見つかりませんでした。HTMLのクラス名が変わった可能性があります。")

        # データを保存
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！取得件数:", len(processed_events))

    except Exception as e:
        print(f"❌ Playwright実行中にエラーが発生しました: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
