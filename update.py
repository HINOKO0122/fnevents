import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta

# ターゲットにする大会情報サイトのURL（例としてFortnite Trackerのイベントページなどを想定）
# ※実際のサイトURLに変更してください
TARGET_URL = "https://fortnitetracker.com/events"

# ボットとして弾かれないように、普通のブラウザ（Chrome）を装うためのヘッダー
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

def scrape_tournaments():
    print(f"[{datetime.now()}] スクレイピングを開始します: {TARGET_URL}")
    
    try:
        # WebサイトのHTMLを取得
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=10)
        response.raise_for_status() # エラーがあればここでストップ
        
        # BeautifulSoupでHTMLを解析（料理）しやすい状態にする
        soup = BeautifulSoup(response.text, 'html.parser')
        
        processed_events = []
        
        # =========================================================
        # ⚠️ ここがスクレイピングの心臓部（職人技）です ⚠️
        # 相手サイトのHTMLを見て、大会情報が入っているブロックを探します。
        # 例：<div class="event-card"> のような要素をすべて取得
        # =========================================================
        
        # 仮のセレクタ（実際のサイトに合わせてデベロッパーツールで調査して書き換えます）
        event_elements = soup.select('.event-card, .trn-card') 
        
        for idx, event_html in enumerate(event_elements):
            try:
                # ① 大会名を取得（例：<h3 class="event-title">大会名</h3>）
                name_elem = event_html.select_one('.event-title, .name')
                name = name_elem.text.strip() if name_elem else f"不明な大会 {idx}"
                
                # ② 日時を取得して変換（ここはサイトの日付表記に合わせて調整が必要）
                # 今回は仮に現在時刻から数日後のダミー日時を生成するロジックにしておきます
                begin_time = (datetime.utcnow() + timedelta(days=idx)).isoformat() + "Z"
                end_time = (datetime.utcnow() + timedelta(days=idx, hours=3)).isoformat() + "Z"
                
                # ③ PR大会かどうかの判定（タイトルに特定の文字が含まれるか）
                is_pr = any(keyword in name.lower() for keyword in ['cup', 'fncs', 'cash', 'major', 'pr'])
                
                processed_events.append({
                    "id": str(idx),
                    "name": name,
                    "region": "ASIA", # サイトから取得できればそれに置き換える
                    "platformsStr": "all",
                    "originalPlatforms": "全機種",
                    "beginTime": begin_time,
                    "endTime": end_time,
                    "isPR": is_pr,
                    "condition": "公式サイトやTrackerで確認してください"
                })
            except Exception as e:
                print(f"カードの解析中にエラー（スキップします）: {e}")

        # もしサイトの仕様変更等で1件も取れなかった場合の保険（空にしない）
        if len(processed_events) == 0:
            print("⚠️ 大会データが見つかりませんでした。HTMLの構造が変わった可能性があります。")

        # 抽出したデータをJSONとして保存
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(processed_events, f, ensure_ascii=False, indent=2)
            print("data.json の更新が完了しました！取得件数:", len(processed_events))

    except Exception as e:
        print(f"❌ 通信または解析エラーが発生しました: {e}")
        exit(1)

if __name__ == "__main__":
    scrape_tournaments()
