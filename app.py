import os
import sqlite3
import time
import threading
import requests
from flask import Flask, render_template

app = Flask(__name__)
DB_NAME = "tickets.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            content TEXT,
            user_handle TEXT,
            post_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def fetch_threads_via_api():
    """模擬 Threads 前端 GraphQL 搜尋 API 抓取資料"""
    search_url = "https://www.threads.net/api/graphql/query"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-IG-App-ID": "238260118697367",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*"
    }
    
    payload = {
        "doc_id": "7032128800185348",
        "variables": f'{{"query":"QWER 讓票","meta_place_id":null}}'
    }

    print(f"\n==================== [{time.strftime('%H:%M:%S')}] 開始執行 API 檢索 ====================", flush=True)
    try:
        response = requests.post(search_url, headers=headers, data=payload, timeout=10)
        print(f"1. HTTP 狀態碼: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as json_err:
                print(f"❌ JSON 解析失敗，前 200 字內容：\n{response.text[:200]}", flush=True)
                return

            search_results = data.get("data", {}).get("searchResults", {}) or data.get("data", {}).get("searchResultsFeed", {})
            sections = search_results.get("edges", [])
            print(f"2. 找到 {len(sections)} 筆結果", flush=True)

            if len(sections) == 0:
                print(f"⚠️ 注意：edges 為空！回傳前 200 字為：\n{str(data)[:200]}", flush=True)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            inserted_count = 0
            scanned_posts = 0

            for edge in sections:
                node = edge.get("node", {})
                thread_items = node.get("thread", {}).get("thread_items", [])
                
                for item in thread_items:
                    scanned_posts += 1
                    post = item.get("post", {})
                    caption = post.get("caption", {})
                    text = caption.get("text", "") if caption else ""
                    
                    if text:
                        # 將換行替換抽到 f-string 外部避免 SyntaxError
                        preview_text = text[:30].replace("\n", " ")
                        print(f"   [掃描到的內文預覽]: {preview_text}...", flush=True)

                    if text and any(k in text for k in ["讓票", "賣票", "VIP", "換票", "QWER"]):
                        pid = post.get("id")
                        user = post.get("user", {}).get("username", "未知用戶")
                        code = post.get("code", "")
                        post_url = f"https://www.threads.net/@{user}/post/{code}" if code else ""
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO posts (post_id, content, user_handle, post_url)
                            VALUES (?, ?, ?, ?)
                        ''', (pid, text, user, post_url))
                        
                        if cursor.rowcount > 0:
                            inserted_count += 1

            conn.commit()
            conn.close()
            print(f"3. 總共掃描 {scanned_posts} 則貼文，成功新增 {inserted_count} 筆新資料至 SQLite。", flush=True)
        else:
            print(f"❌ API 請求失敗，狀態碼不是 200。回傳內容：\n{response.text[:200]}", flush=True)

    except Exception as e:
        print(f"❌ API 抓取時發生未預期錯誤: {e}", flush=True)
    print("========================================================================\n", flush=True)

def run_scraper():
    while True:
        fetch_threads_via_api()
        time.sleep(300)

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