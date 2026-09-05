import sqlite3
import time
import threading
from flask import Flask, render_template
from playwright.sync_api import sync_playwright

app = Flask(__name__)
DB_NAME = "tickets.db"

# 1. 初始化資料庫
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 2. 爬蟲任務
def run_scraper():
    while True:
        print(f"[{time.strftime('%H:%M:%S')}] 開始抓取 Threads...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://www.threads.net/search?q=QWER%20讓票", wait_until="networkidle")
                time.sleep(3)
                
                posts = page.locator('div[data-pressable-container="true"]').all()
                
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                
                for post in posts[:10]:
                    text = post.inner_text().strip()
                    if any(k in text for k in ["讓票", "賣票", "VIP"]):
                        # 避免重複存入相同的貼文
                        cursor.execute("INSERT OR IGNORE INTO posts (content) VALUES (?)", (text,))
                
                conn.commit()
                conn.close()
                browser.close()
        except Exception as e:
            print(f"爬蟲發生錯誤: {e}")
            
        # 每 15 分鐘（900秒）執行一次
        time.sleep(900)

# 3. 網頁路由 (Home Page)
@app.route("/")
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 抓取最新的 30 則讓票貼文
    cursor.execute("SELECT content, created_at FROM posts ORDER BY id DESC LIMIT 30")
    data = cursor.fetchall()
    conn.close()
    return render_template("index.html", posts=data)

if __name__ == "__main__":
    init_db()
    # 開啟背景執行緒跑爬蟲，不干擾網頁服務
    threading.Thread(target=run_scraper, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)