# 使用輕量級的 Python 官方影像
FROM python:3.11-slim

WORKDIR /app

# 複製並安裝套件 (只需要 flask 與 requests)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案所有檔案
COPY . .

# 開放連接埠
EXPOSE 5000

# 啟動應用程式
CMD ["python", "app.py"]