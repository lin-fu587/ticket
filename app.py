import os
import sqlite3
import time
import threading
import feedparser
from flask import Flask, render_template

app = Flask(__name__)
DB_NAME = "tickets.db"

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

def fetch_threads_via_rss():
    """透過 RSS 抓取 Threads 搜尋結果 (免 API Key、免驗證、零被擋風險)"""
    rss_url = "https://rsshub.app/threads/search/QWER%20讓票"
    
    print(f"\n==================== [{time.strftime('%H:%M:%S')}] 開始執行 RSS 檢索 Threads ====================", flush=True)
    try:
        feed = feedparser.parse(rss_url)
        entries = feed.entries
        print(f"1. 成功讀取 RSS，找到 {len(entries)} 筆項目", flush=True)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        inserted_count = 0

        for entry in entries:
            link = entry.get("link", "")
            title = entry.get("title", "")
            summary = entry.get("summary", "")

            user_handle = "Threads用戶"
            if "@" in link:
                try:
                    user_handle = link.split("@")[1].split("/")[0]
                except Exception:
                    pass

            cursor.execute('''
                INSERT OR IGNORE INTO posts (post_url, title, content, user_handle)
                VALUES (?, ?, ?, ?)
            ''', (link, title, summary, user_handle))

            if cursor.rowcount > 0:
                inserted_count += 1

        conn.commit()
        conn.close()
        print(f"2. 成功新增 {inserted_count} 筆新讓票文章至 SQLite。", flush=True)

    except Exception as e:
        print(f"❌ RSS 檢索失敗: {e}", flush=True)
    print("========================================================================\n", flush=True)

def run_scraper():
    while True:
        fetch_threads_via_rss()
        # 每 10 分鐘（600秒）檢查一次
        time.sleep(600)

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