# LINE Bot 任務管理系統 - Render 部署版

這是一個專為 Render 平台設計的 LINE Bot 任務管理系統，幫助您管理日常任務、設定計畫、記錄反思。

## 部署到 Render 步驟

### 1. Fork 或克隆此存儲庫

首先，將此存儲庫 fork 到您自己的 GitHub 帳號，或直接下載所有代碼。

### 2. 在 Render 上設置

1. 註冊/登錄 [Render](https://render.com/)
2. 點擊 "New" > "Web Service"
3. 連接您的 GitHub 存儲庫
4. 填寫以下信息：
   - **Name**: 您選擇的服務名稱
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`

### 3. 配置環境變數

在 Render 的服務設置頁面上，添加以下環境變數：

- `LINE_CHANNEL_ACCESS_TOKEN`: 您的 LINE Channel Access Token
- `LINE_CHANNEL_SECRET`: 您的 LINE Channel Secret
- `USER_ID`: 您的 LINE 使用者 ID
- `PORT`: 設置為 `10000`

### 4. 部署服務

點擊 "Create Web Service" 開始部署。

### 5. 設置 LINE Bot Webhook URL

一旦服務部署完成，您將獲得一個格式為 `https://your-service-name.onrender.com` 的 URL。

在 LINE Developers Console 中設置您的 Webhook URL 為：
`https://your-service-name.onrender.com/callback`

## 使用指南

### 基本指令

- **新增任務**：`新增：看書30分鐘`
- **完成任務**：`完成：看書30分鐘`
- **查詢任務**：`查詢任務`
- **今日進度**：`今日進度`
- **記錄反思**：`反思：今天我學到了...`
- **設定每日計畫**：`設定計畫：{"早上":"晨間閱讀","中午":"午餐後散步","晚上":"復盤一天"}`
- **查看幫助**：`幫助` 或 `help`

### 自動功能

本 Bot 會自動在以下時間點發送訊息：

- **早上 7:00**: 早晨思考問題
- **早上 8:00**: 早上任務提醒
- **中午 12:00**: 中午任務提醒
- **晚上 6:00**: 晚上任務提醒
- **晚上 9:00**: 晚間反思問題

## 維護提示

- Render 免費版會在15分鐘不活動後進入休眠狀態
- 建議使用外部服務（如 UptimeRobot）定期 ping 您的應用程式，保持其活動狀態
- 定期備份 `tasks.json` 和 `reflections.json` 文件，避免數據丟失

## 問題排解

如果遇到問題，請檢查：

1. 環境變數是否正確設置
2. LINE Bot 的 Webhook URL 是否正確
3. 查看 Render 的日誌輸出了解可能的錯誤

## 鳴謝

感謝使用本 LINE Bot 任務管理系統。希望它能幫助您更有效地管理時間和任務！
