# 松仁大樓會議室查詢腳本使用說明

## 概述

本專案包含三個 bash 腳本，用於自動查詢松仁大樓的會議室可用性：

1. `test_query_songshan.sh` - 測試腳本（查詢幾天）
2. `query_songshan_building_2024.sh` - 完整腳本（查詢2024年全年）
3. `test_encoding.sh` - UTF-8 編碼測試腳本

## 🔧 編碼修正說明

**v2.0 更新**：修正了 CSV 檔案亂碼問題
- 使用直接重定向 curl 輸出的方法，避免 shell 變數處理導致的編碼問題
- 添加 UTF-8 字符集標頭到 HTTP 請求
- 自動驗證檔案是否包含中文字符
- 提供編碼測試腳本來診斷問題

## 前置條件

1. **API 服務運行**：確保 Flask API 服務正在 `localhost:5000` 運行
   ```bash
   python booking_meeting_room_api.py
   ```

2. **網路連接**：確保可以訪問 localhost:5000

3. **系統要求**：
   - macOS 或 Linux 系統
   - bash shell
   - curl 命令
   - 足夠的磁碟空間（全年查詢約需要幾百MB）

## 使用方法

### 1. 編碼測試腳本（如果遇到亂碼問題）

```bash
./test_encoding.sh
```

**功能**：
- 測試不同的檔案保存方法
- 驗證 UTF-8 編碼處理
- 診斷編碼問題

### 2. 測試腳本（推薦先執行）

```bash
./test_query_songshan.sh
```

**功能**：
- 查詢 3 天的會議室資料（2025/07/10, 2025/07/11, 2025/07/12）
- 驗證 API 連接和腳本功能
- 自動檢查 UTF-8 編碼是否正確
- 輸出到 `./test_songshan_data/` 目錄

### 3. 完整年度查詢腳本

```bash
./query_songshan_building_2024.sh
```

**功能**：
- 查詢 2024 年全年（366 天）的會議室資料
- 自動驗證每個檔案的 UTF-8 編碼
- 輸出到 `./songshan_building_data_2024/` 目錄
- 生成詳細的日誌和錯誤記錄

## 輸出檔案

### 測試腳本輸出
```
./test_songshan_data/
├── 松仁大樓_20250710.csv
├── 松仁大樓_20250711.csv
└── 松仁大樓_20250712.csv
```

### 完整腳本輸出
```
./songshan_building_data_2024/
├── 松仁大樓_20240101.csv
├── 松仁大樓_20240102.csv
├── ...
├── 松仁大樓_20241231.csv
├── query_log.txt          # 查詢日誌
└── error_log.txt          # 錯誤日誌
```

## 腳本特性

### 錯誤處理
- 自動檢查 API 服務狀態
- 網路請求超時處理（30秒連接，120秒總時間）
- 單日查詢失敗不影響其他日期
- 詳細的錯誤日誌記錄

### 進度顯示
- 實時顯示查詢進度（X/總天數）
- 成功/失敗統計
- 執行時間計算
- 彩色輸出便於閱讀

### 負載控制
- 請求間隔延遲（預設2秒）
- 避免對服務器造成過大負載
- 可調整的超時設定

## 自定義設定

### 修改查詢參數

編輯腳本中的變數：

```bash
# API設定
API_URL="http://localhost:5000/run"
BUILDING_ID="6"                    # 松仁大樓ID
BUILDING_NAME="松仁大樓"

# 延遲設定
DELAY_SECONDS=2                    # 請求間隔（秒）

# 輸出目錄
OUTPUT_DIR="./songshan_building_data_2024"
```

### 修改查詢年份

要查詢其他年份，修改 `query_songshan_building_2024.sh` 中的：

```bash
YEAR="2025"  # 改為想要的年份

# 並修改 generate_date_sequence 函數中的日期範圍
local start_date="2025/01/01"
local end_date="2025/12/31"
```

### 查詢其他建築物

修改 `BUILDING_ID` 和 `BUILDING_NAME`：

```bash
BUILDING_ID="20"                   # A3置地廣場
BUILDING_NAME="A3置地廣場"

# 或其他建築物：
# "4" - 仁愛大樓
# "10" - 國泰證券總公司  
# "22" - 高雄資訊開發中心
```

## 故障排除

### 1. API 服務無法連接
```bash
# 檢查服務狀態
curl http://localhost:5000/health

# 重新啟動服務
python booking_meeting_room_api.py
```

### 2. 權限問題
```bash
# 確保腳本有執行權限
chmod +x test_query_songshan.sh
chmod +x query_songshan_building_2024.sh
```

### 3. 查詢失敗
- 檢查 `error_log.txt` 了解具體錯誤
- 確認日期格式正確（YYYY/MM/DD）
- 檢查網路連接和 API 服務狀態

### 4. 磁碟空間不足
```bash
# 檢查可用空間
df -h .

# 清理舊的查詢結果
rm -rf ./test_songshan_data
rm -rf ./songshan_building_data_2024
```

## 執行時間估算

- **測試腳本**：約 10-15 秒（3天 + 2秒間隔）
- **完整腳本**：約 12-15 分鐘（366天 × 2秒間隔 + API處理時間）

## 注意事項

1. **服務穩定性**：長時間查詢前確保 API 服務穩定
2. **資源使用**：全年查詢會產生大量檔案，注意磁碟空間
3. **網路穩定**：建議在穩定的網路環境下執行
4. **備份重要**：建議定期備份查詢結果
5. **日誌檢查**：執行完成後檢查錯誤日誌確認資料完整性

## 範例執行輸出

```bash
$ ./test_query_songshan.sh
[INFO] 開始執行松仁大樓會議室查詢測試腳本
[INFO] 建築物: 松仁大樓 (ID: 6)
[INFO] 檢查API服務狀態...
[SUCCESS] API服務正常運行
[INFO] 創建輸出目錄: ./test_songshan_data
[INFO] 測試查詢 3 天
[INFO] [1/3] 查詢日期: 2025/07/10
[SUCCESS] [1/3] 成功保存: ./test_songshan_data/松仁大樓_20250710.csv (1234 bytes)
[INFO] [2/3] 查詢日期: 2025/07/11
[SUCCESS] [2/3] 成功保存: ./test_songshan_data/松仁大樓_20250711.csv (1456 bytes)
[INFO] [3/3] 查詢日期: 2025/07/12
[SUCCESS] [3/3] 成功保存: ./test_songshan_data/松仁大樓_20250712.csv (1345 bytes)

[SUCCESS] 測試完成！
[INFO] 總共查詢天數: 3
[SUCCESS] 成功查詢: 3
[ERROR] 失敗查詢: 0
[INFO] 輸出目錄: ./test_songshan_data
[SUCCESS] 所有測試查詢都成功完成！
```
