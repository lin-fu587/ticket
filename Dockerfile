# 使用 Playwright 官方包含 Python 與所有瀏覽器依賴的影像
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# 複製專案檔案
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright 瀏覽器
RUN playwright install chromium

COPY . .

# 開放連接埠
EXPOSE 5000

# 啟動應用程式
CMD ["python", "app.py"]