#!/bin/bash

# 松仁大樓會議室查詢測試腳本
# 只查詢幾天來測試功能

# 設定變數
API_URL="http://localhost:5000/run"
BUILDING_ID="20"
BUILDING_NAME="A3置地廣場"
OUTPUT_DIR="./test_a3_data"
DELAY_SECONDS=1

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函數：打印帶顏色的訊息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函數：檢查API服務是否可用
check_api_service() {
    print_info "檢查API服務狀態..."
    
    # 先測試根路徑
    if curl -s --connect-timeout 5 "http://localhost:5000/" > /dev/null 2>&1; then
        print_success "API服務正常運行"
        return 0
    else
        print_error "API服務無法連接，請確保服務正在運行在 localhost:5000"
        return 1
    fi
}

# 函數：創建輸出目錄
create_output_directory() {
    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
        print_info "創建輸出目錄: $OUTPUT_DIR"
    fi
}

# 函數：查詢單日會議室資料
query_single_day() {
    local query_date="$1"
    local day_count="$2"
    local total_days="$3"
    
    # 格式化檔案名稱的日期 (YYYYMMDD)
    local file_date=$(echo "$query_date" | sed 's/\///g')
    local output_file="${OUTPUT_DIR}/${BUILDING_NAME}_${file_date}.csv"
    
    print_info "[$day_count/$total_days] 查詢日期: $query_date"
    
    # 準備JSON請求資料
    local json_data="{\"date\": \"$query_date\", \"buildings\": [\"$BUILDING_ID\"]}"
    
    print_info "發送請求: $json_data"

    # 方法1: 直接重定向 curl 輸出（最佳方法，避免編碼問題）
    local curl_exit_code=0
    curl -s \
        -X POST \
        -H "Content-Type: application/json; charset=utf-8-sig" \
        -H "Accept: text/csv; charset=utf-8-sig" \
        -d "$json_data" \
        --connect-timeout 30 \
        --max-time 120 \
        "$API_URL" > "$output_file" 2>/dev/null

    curl_exit_code=$?

    print_info "Curl exit code: $curl_exit_code"

    if [ $curl_exit_code -eq 0 ]; then
        local file_size=$(wc -c < "$output_file" 2>/dev/null || echo "0")
        print_info "檔案大小: ${file_size} bytes"

        # 檢查檔案是否為有效的CSV
        if [ "$file_size" -gt 50 ] && head -1 "$output_file" | grep -q ","; then
            print_success "[$day_count/$total_days] 成功保存: $output_file (${file_size} bytes)"

            # 顯示檔案前幾行來驗證編碼
            print_info "檔案前3行內容:"
            head -3 "$output_file" | sed 's/^/  /'

            # 檢查是否包含中文字符
            if grep -q "會議室\|時間\|房間" "$output_file" 2>/dev/null; then
                print_success "✓ 檔案包含中文字符，編碼正確"
            else
                print_warning "⚠ 檔案不包含預期的中文字符"
            fi

            return 0
        else
            # 檢查是否是錯誤回應
            if grep -q "error" "$output_file" 2>/dev/null; then
                print_error "[$day_count/$total_days] API返回錯誤: $query_date"
                echo "錯誤內容:"
                head -3 "$output_file" | sed 's/^/  /'
            else
                print_error "[$day_count/$total_days] 回應格式異常或檔案過小: $query_date"
            fi
            return 1
        fi
    else
        print_error "[$day_count/$total_days] 網路請求失敗: $query_date (Exit code: $curl_exit_code)"
        return 1
    fi
}

# 主函數
main() {
    print_info "開始執行松仁大樓會議室查詢測試腳本"
    print_info "建築物: $BUILDING_NAME (ID: $BUILDING_ID)"
    
    # 檢查API服務
    if ! check_api_service; then
        exit 1
    fi
    
    # 創建輸出目錄
    create_output_directory
    
    # 測試日期列表（只查詢幾天）
    local test_dates=("2025/07/10")
    local total_days=${#test_dates[@]}
    
    print_info "測試查詢 $total_days 天"
    
    # 統計變數
    local success_count=0
    local error_count=0
    local day_count=0
    
    # 遍歷測試日期
    for query_date in "${test_dates[@]}"; do
        day_count=$((day_count + 1))
        
        if query_single_day "$query_date" "$day_count" "$total_days"; then
            success_count=$((success_count + 1))
        else
            error_count=$((error_count + 1))
        fi
        
        # 延遲
        if [ $day_count -lt $total_days ]; then
            sleep $DELAY_SECONDS
        fi
    done
    
    # 輸出最終統計
    echo ""
    print_success "測試完成！"
    print_info "總共查詢天數: $total_days"
    print_success "成功查詢: $success_count"
    print_error "失敗查詢: $error_count"
    print_info "輸出目錄: $OUTPUT_DIR"
    
    if [ $error_count -gt 0 ]; then
        print_error "有查詢失敗，請檢查API服務和網路連接"
        exit 1
    else
        print_success "所有測試查詢都成功完成！"
        exit 0
    fi
}

# 腳本入口點
main "$@"
