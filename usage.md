# 會議室預訂 API 使用說明書

## 📋 專案簡介

這是一個自動化會議室查詢和預訂系統，支援多個建築物的會議室資訊查詢，並提供 RESTful API 介面。系統使用 Selenium 進行網頁爬蟲，並將結果以 CSV 格式回傳。

## 🚀 快速開始

### 1. 安裝依賴套件

首先安裝所需的 Python 套件：

```bash
pip install -r requirement.txt
```

### 2. 環境設定

在專案根目錄創建 `.env` 檔案，並填入您的個人資訊：

```bash
# .env 檔案範例
BOOKING_USERNAME=您的帳號
BOOKING_PASSWORD=您的密碼
```

### 3.使用login.py登入
```
python login.py
```
第一次登入需要使用OTP認證

### 4. 啟動 API 服務

```bash
python booking_meeting_room_api.py
```

服務啟動後會在 `http://localhost:5000` 監聽請求。

### 5. 執行測試腳本
```
./test_query_ruihu.sh
```
順利的話將會爬去2025/7/10日的瑞湖大樓會議室資料

成功的話就執行,爬取2024年的瑞湖大樓會議室資料
```
./batch_query_ruihu_2024.sh
```

## 🏢 支援的建築物

| 建築物 ID | 建築物名稱 |
|-----------|------------|
| 4         | 仁愛大樓 |
| 6         | 松仁大樓 |
| 10        | 國泰證券總公司 |
| 12        | 瑞湖大樓 |
| 15        | 信義安和大樓 |
| 19        | 台中忠明大樓 |
| 20        | A3置地廣場 |
| 22        | 高雄資訊開發中心 |

## 📡 API 端點

### 1. 服務狀態檢查

```http
GET /
```

檢查 API 服務狀態和可用端點。

**回應範例：**
```json
{
  "service": "Booking Meeting Room API",
  "status": "running",
  "version": "2.0",
  "endpoints": {
    "GET /": "Service status check",
    "GET /health": "Health check",
    "GET /buildings": "Get available buildings list",
    "POST /run": "Query meeting room availability",
    "POST /book": "Book meeting room"
  },
  "available_buildings": {...}
}
```

### 2. 健康檢查

```http
GET /health
```

檢查服務健康狀態。

### 3. 取得建築物列表

```http
GET /buildings
```

取得所有可用的建築物列表。

### 4. 查詢會議室可用狀況

```http
POST /run
```

查詢指定日期和建築物的會議室可用狀況。

**請求參數：**
```json
{
  "date": "2025/07/10",
  "buildings": ["20", "6"],
  "default_buildings": ["20"]
}
```

**參數說明：**
- `date`: 查詢日期，格式為 `YYYY/MM/DD`
- `buildings`: 要查詢的建築物 ID 列表
- `default_buildings`: 預設建築物列表（可選）

**回應：**
- 成功：返回 CSV 格式的會議室資料
- 失敗：返回錯誤訊息 JSON

### 5. 預訂會議室

```http
POST /book
```

預訂指定的會議室。

**請求參數：**
```json
{
  "room_number": "3303",
  "start_date": "2025/07/10",
  "meeting_subject": "技術討論",
  "time_from": "08:00",
  "time_to": "09:00",
  "building_id": "20"
}
```

**參數說明：**
- `room_number`: 會議室編號
- `start_date`: 預訂日期
- `meeting_subject`: 會議主題
- `time_from`: 開始時間
- `time_to`: 結束時間
- `building_id`: 建築物 ID

## 🛠️ 使用範例

### 使用 curl 查詢會議室

```bash
# 查詢 A3置地廣場 2025/07/10 的會議室資訊
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025/07/10",
    "buildings": ["20"]
  }' \
  -o meeting_rooms.csv
```

### 使用 curl 預訂會議室

```bash
# 預訂會議室
curl -X POST http://localhost:5000/book \
  -H "Content-Type: application/json" \
  -d '{
    "room_number": "3303",
    "start_date": "2025/07/10",
    "meeting_subject": "技術討論",
    "time_from": "08:00",
    "time_to": "09:00",
    "building_id": "20"
  }'
```

### 使用測試腳本

專案提供了測試腳本來驗證功能：

```bash
# 測試 A3置地廣場 查詢功能
./test_query_a3.sh
```

## 📁 專案結構

```
booking_api/
├── booking_meeting_room_api.py    # 主要 API 服務
├── login.py                       # 登入相關功能
├── requirement.txt                # Python 依賴套件
├── .env                           # 環境變數設定
├── usage.md                       # 使用說明書
├── README.md                      # 專案說明
├── test_query_a3.sh              # 測試腳本
├── utils/                         # 工具函數
│   ├── convert_to_csv.py         # CSV 轉換工具
│   └── 2_html_filter.sh          # HTML 過濾腳本
├── tmp/                           # 暫存檔案目錄
├── output/                        # 輸出檔案目錄
└── dify_workflow/                 # Dify 工作流程設定
```

## ⚙️ 設定說明

### Chrome 瀏覽器設定

系統使用 Selenium Chrome WebDriver，請確保：
1. 已安裝 Google Chrome 瀏覽器
2. ChromeDriver 已正確設定在 PATH 中

### 輸出目錄

- `tmp/`: 存放爬蟲過程中的暫存 HTML 檔案
- `output/`: 存放最終的 CSV 結果檔案

## 🔧 故障排除

### 常見問題

1. **API 服務無法啟動**
   - 檢查 5000 埠是否被佔用
   - 確認 `.env` 檔案格式正確

2. **登入失敗**
   - 檢查 `.env` 中的帳號密碼是否正確
   - 確認網路連線正常

3. **Chrome 相關錯誤**
   - 確認 Chrome 瀏覽器已安裝
   - 更新 ChromeDriver 到最新版本

4. **CSV 檔案為空或格式錯誤**
   - 檢查目標網站是否正常運作
   - 確認查詢的日期和建築物 ID 是否有效

### 日誌說明

API 運行時會輸出詳細的日誌資訊，包括：
- 🕐 執行時間統計
- 🚀 瀏覽器啟動狀態
- 🔐 登入過程
- 🏢 建築物查詢進度
- ⚙️ 檔案處理狀態
- 📊 執行結果統計

## 📞 技術支援

如有問題或建議，請查看：
1. 檢查日誌輸出中的錯誤訊息
2. 確認所有依賴套件已正確安裝
3. 驗證網路連線和目標網站可用性

## 🔄 版本更新

目前版本：v2.0

主要特色：
- 多建築物同時查詢
- 詳細時間統計
- 優化的等待邏輯
- 完整的錯誤處理
- UTF-8-SIG 編碼支援
