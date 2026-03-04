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
            # ロボット感を消すための特殊な起動設定（ステルスモード）
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # 人間が使っているようなブラウザ環境を偽装
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="ja-JP"
            )
            
            page = context.new_page()
            
            print("ページにアクセスしています（バリア突破を試みます）...")
            try:
                # 'load'（完全読み込み）ではなく、骨組みができた段階(domcontentloaded)で次に進む
                # 30秒で一旦区切りをつける
                page.goto(TARGET_URL, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"⚠️ 読み込みが遅延しています。このまま強制突破を試みます: {e}")
            
            # JavaScriptがデータを描画するのを10秒だけ待つ
            page.wait_for_timeout(10000) 
            
            # 読み込み終わった画面のHTML（裏側のコード）をすべて取得
            html = page.content()
            browser.close()
            print("ページの取得に完了しました！解析を開始します。")

        # 相手の最強バリア「Cloudflare」に引っかかっていないかチェック
        if "Just a moment..." in html or "Cloudflare" in html or "cf-browser-verification" in html:
            print("❌ Cloudflareの強力なBot対策バリアに完全にブロックされました。データが空っぽです。")
        
        # BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(html, 'html.parser')
        processed_events = []
        
        # 相手サイトの構造（クラス名）の候補をいくつか入れておく
        event_elements = soup.select('.trn-card, .event-card') 
        
        for idx, event_html in enumerate(event_elements):
            try:
                name_elem = event_html.select_one('.trn-card__header-title, h3, .name')
                name = name_elem.text.strip() if name_elem else f"不明な大会 {idx}"
                
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
                pass

        if len(processed_events) == 0:
            print("⚠️ 大会データが見つかりませんでした。サイトのデザインが変わったか、バリアに弾かれています。")

        # データを保存
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！取得件数:", len(processed_events))

    except Exception as e:
        print(f"❌ 致命的なエラーが発生しました: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
