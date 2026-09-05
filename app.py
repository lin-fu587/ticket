import os
import sqlite3
import time
import threading
import requests
from flask import Flask, render_template

app = Flask(__name__)
DB_NAME = "tickets.db"

# 填入你申請到的 Google API 金鑰與 CX ID (也可以設定在 Render 的 Environment Variables)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT UNIQUE,
            title TEXT,
            content TEXT,
            user_handle TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def fetch_via_google():
    """透過 Google Custom Search 全域搜尋 Threads (絕不封號、無阻擋)"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": "site:threads.net QWER (讓票 OR 卖票 OR VIP OR 票)",
        "num": 10
    }
    
    print(f"\n==================== [{time.strftime('%H:%M:%S')}] 開始執行 Google 檢索 Threads ====================", flush=True)
    try:
        res = requests.get(url, params=params, timeout=10)
        print(f"1. HTTP 狀態碼: {res.status_code}", flush=True)
        
        if res.status_code == 200:
            data = res.json()
            items = data.get("items", [])
            print(f"2. 找到 {len(items)} 筆搜尋結果", flush=True)
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            inserted_count = 0
            
            for item in items:
                link = item.get("link", "")
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                
                # 從網址解析出使用者名稱 (例如 https://www.threads.net/@user/post/xxx)
                user_handle = "Threads用戶"
                if "@" in link:
                    user_handle = link.split("@")[1].split("/")[0]

                cursor.execute('''
                    INSERT OR IGNORE INTO posts (post_url, title, content, user_handle)
                    VALUES (?, ?, ?, ?)
                ''', (link, title, snippet, user_handle))
                
                if cursor.rowcount > 0:
                    inserted_count += 1
                    
            conn.commit()
            conn.close()
            print(f"3. 成功新增 {inserted_count} 筆新讓票文章至 SQLite。", flush=True)
        else:
            print(f"❌ Google API 請求失敗，狀態碼: {res.status_code}，訊息: {res.text[:200]}", flush=True)

    except Exception as e:
        print(f"❌ 檢索時發生未預期錯誤: {e}", flush=True)
    print("========================================================================\n", flush=True)

def run_scraper():
    while True:
        fetch_via_google()
        # Google API 免費額度每天 100 次，設定 15 分鐘（900秒）檢查一次剛好不會超過額度
        time.sleep(900)

@app.route("/")
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_handle, content, post_url, created_at FROM posts ORDER BY id DESC LIMIT 50")
    data = cursor.fetchall()
    conn.close()
    return render_template("index.html", posts=data)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_scraper, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)