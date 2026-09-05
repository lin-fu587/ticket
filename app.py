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
    """模擬 Threads 前端搜尋 API 抓取資料（含詳細 Debug 日誌）"""
    search_url = "https://www.threads.net/api/v1/search/serp/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-IG-App-ID": "238260118697367",  # Threads 網頁版的 App ID
        "Accept": "*/*"
    }
    
    params = {
        "query": "QWER 讓票",
        "search_surface": "default"
    }

    print(f"\n==================== [{time.strftime('%H:%M:%S')}] 開始執行 API 檢索 ====================")
    try:
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        print(f"1. HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as json_err:
                print(f"❌ JSON 解析失敗，可能回傳了 HTML 錯誤頁面。前 200 字內容：\n{response.text[:200]}")
                return

            # 查看頂層 Key 結構
            print(f"2. API 成功回傳 JSON，頂層 Key 有: {list(data.keys())}")
            
            # 解析 Threads 回傳的 JSON 階層
            search_results = data.get("data", {}).get("searchResults", {})
            sections = search_results.get("edges", [])
            print(f"3. 找到 {len(sections)} 筆 edges (搜尋結果個數)")

            if len(sections) == 0:
                print(f"⚠️ 注意：edges 為空！Threads 回傳的 JSON 結構內容前 300 字為：\n{str(data)[:300]}")

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
                    
                    print(f"   [掃描到的內文預覽]: {text[:30]}...")

                    # 關鍵字二次過濾
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
            print(f"4. 總共掃描 {scanned_posts} 則貼文，成功新增 {inserted_count} 筆新資料至 SQLite。")
        else:
            print(f"❌ API 請求失敗，狀態碼不是 200。回傳內容：\n{response.text[:300]}")

    except Exception as e:
        print(f"❌ API 抓取時發生未預期錯誤: {e}")
    print("========================================================================\n")

def run_scraper():
    while True:
        fetch_threads_via_api()
        # 每 5 分鐘執行一次
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
    # 啟動時先手動抓一次
    threading.Thread(target=run_scraper, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)