# 會議室預約 API

此專案提供了一個 REST API，用於在國泰控股預約系統中查詢和預約會議室。

## 專案概述

本應用程式自動化以下流程：
1. 查詢特定日期的可用會議室
2. 使用指定參數預約會議室
3. 提取會議室數據並轉換為 CSV 格式進行分析

## 功能特點

### 1. 會議室查詢 API
- 端點：`/run`
- 方法：POST
- 功能：擷取特定日期的會議室可用性資訊
- 回傳：可用會議室的 CSV 數據

### 2. 會議室預約 API
- 端點：`/book`
- 方法：POST
- 功能：使用指定參數預約會議室
- 回傳：表明預約狀態的 JSON 回應

## 專案結構

```
.
├── booking_meeting_room_api.py   # 主要 Flask API 應用
├── output/                       # CSV 和文本數據的輸出目錄
│   └── YYYYMMDD_combined.csv     # 會議室數據的 CSV 輸出
├── tmp/                          # 處理過程中使用的臨時文件
└── utils/                        # 工具腳本和輔助程式
    ├── 2_html_filter.sh          # 用於過濾 HTML 數據的 Shell 腳本
    └── convert_to_csv.py         # 用於 CSV 轉換的 Python 工具
```

## 技術細節

### 依賴項
- Flask：API 端點的 Web 框架
- Selenium：用於與預約系統互動的瀏覽器自動化工具
- Python 標準庫：csv、os、time、subprocess

### 工作原理

#### 會議室查詢流程：
1. 向預約系統進行認證
2. 導航至會議室搜尋頁面
3. 設定搜尋參數（日期、大樓）
4. 擷取上午和下午的可用性數據
5. 使用 Shell 腳本處理 HTML 數據
6. 將數據轉換為結構化的 CSV 格式
7. 將數據返回給 API 調用者

#### 會議室預約流程：
1. 向預約系統進行認證
2. 導航至預約介面
3. 選擇指定的會議室
4. 填寫會議詳情（主題、時間、參與人數）
5. 提交預約請求
6. 返回成功/失敗回應

## 使用方法

### 查詢會議室
```bash
curl -X POST http://localhost:5000/run \
  -H "Content-Type: application/json" \
  -d '{"date": "2024/09/20"}'
```

### 預約會議室
```bash
curl -X POST http://localhost:5000/book \
  -H "Content-Type: application/json" \
  -d '{
    "room_number": "3303",
    "start_date": "2024/09/19",
    "meeting_subject": "技術討論",
    "time_from": "08:00",
    "time_to": "09:00"
  }'
```

## 設置說明

1. 複製儲存庫
2. 安裝所需依賴項：
   ```bash
   pip install flask selenium
   ```
3. 確保 Chrome WebDriver 已安裝並在您的 PATH 中可用
4. 運行 API 伺服器：
   ```bash
   python booking_meeting_room_api.py
   ```
5. API 將在 http://localhost:5000 可用

## 輸出數據格式

CSV 輸出包含以下欄位：
- 會議室 (Meeting Room)
- 會議時間 (Meeting Time)
- 會議名稱 (Meeting Name)
- 借用人 (Requester)

## 安全性注意事項

- 憑證應安全存儲，不應在應用程式中硬編碼
- 考慮為 API 端點實施適當的認證
