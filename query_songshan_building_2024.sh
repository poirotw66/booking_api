#!/bin/bash

# 松仁大樓2024年全年會議室可用性查詢腳本
# 作者: Booking API Script
# 日期: 2025-07-09
# 描述: 自動查詢松仁大樓（建築物ID: 6）在2024年全年的會議室可用性

# 設定變數
API_URL="http://localhost:5000/run"
BUILDING_ID="6"
BUILDING_NAME="松仁大樓"
YEAR="2024"
OUTPUT_DIR="./songshan_building_data_${YEAR}"
LOG_FILE="${OUTPUT_DIR}/query_log.txt"
ERROR_LOG="${OUTPUT_DIR}/error_log.txt"
DELAY_SECONDS=2

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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函數：記錄日誌
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" >> "$ERROR_LOG"
    print_error "$1"
}

# 函數：檢查API服務是否可用
check_api_service() {
    print_info "檢查API服務狀態..."
    
    if curl -s --connect-timeout 5 "http://localhost:5000/health" > /dev/null 2>&1; then
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

# 函數：檢查日期是否有效
is_valid_date() {
    local date_str="$1"
    if date -j -f "%Y/%m/%d" "$date_str" > /dev/null 2>&1; then
        return 0
    else
        return 1
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
    
    # 直接重定向 curl 輸出到檔案（避免編碼問題）
    local curl_exit_code=0
    curl -s \
        -X POST \
        -H "Content-Type: application/json; charset=utf-8" \
        -H "Accept: text/csv; charset=utf-8" \
        -d "$json_data" \
        --connect-timeout 30 \
        --max-time 120 \
        "$API_URL" > "$output_file" 2>/dev/null

    curl_exit_code=$?

    if [ $curl_exit_code -eq 0 ]; then
        local file_size=$(wc -c < "$output_file" 2>/dev/null || echo "0")

        # 檢查檔案是否為有效的CSV
        if [ "$file_size" -gt 100 ] && head -1 "$output_file" | grep -q ","; then
            print_success "[$day_count/$total_days] 成功保存: $output_file (${file_size} bytes)"
            log_message "SUCCESS: $query_date - File: $output_file - Size: ${file_size} bytes"

            # 檢查編碼是否正確（包含中文字符）
            if grep -q "會議室\|時間\|房間" "$output_file" 2>/dev/null; then
                log_message "SUCCESS: $query_date - UTF-8 encoding verified"
            else
                log_message "WARNING: $query_date - No Chinese characters found, encoding may be incorrect"
            fi

            return 0
        else
            # 檢查是否是錯誤回應
            if grep -q "error" "$output_file" 2>/dev/null; then
                print_error "[$day_count/$total_days] API返回錯誤: $query_date"
                log_error "$query_date - API Error found in response"
            else
                print_warning "[$day_count/$total_days] 回應資料過小或格式異常: $query_date (${file_size} bytes)"
                log_error "$query_date - Response too small or invalid format: ${file_size} bytes"
            fi
            return 1
        fi
    else
        print_error "[$day_count/$total_days] 網路請求失敗: $query_date (Exit code: $curl_exit_code)"
        log_error "$query_date - Network request failed with exit code: $curl_exit_code"
        return 1
    fi
}

# 函數：計算2024年的總天數
calculate_total_days() {
    # 2024年是閏年，共366天
    echo "366"
}

# 函數：生成日期序列
generate_date_sequence() {
    local start_date="2024/01/01"
    local end_date="2024/12/31"
    
    # 使用date命令生成日期序列
    local current_date="$start_date"
    local dates=()
    
    while [ "$current_date" != "2024/12/32" ]; do
        dates+=("$current_date")
        # 計算下一天
        local next_date=$(date -j -v+1d -f "%Y/%m/%d" "$current_date" "+%Y/%m/%d" 2>/dev/null)
        if [ $? -ne 0 ]; then
            break
        fi
        current_date="$next_date"
    done
    
    printf '%s\n' "${dates[@]}"
}

# 主函數
main() {
    print_info "開始執行松仁大樓2024年全年會議室查詢腳本"
    print_info "建築物: $BUILDING_NAME (ID: $BUILDING_ID)"
    print_info "查詢年份: $YEAR"
    print_info "輸出目錄: $OUTPUT_DIR"
    print_info "請求間隔: ${DELAY_SECONDS}秒"
    
    # 檢查API服務
    if ! check_api_service; then
        exit 1
    fi
    
    # 創建輸出目錄
    create_output_directory
    
    # 初始化日誌檔案
    echo "松仁大樓2024年查詢日誌 - 開始時間: $(date)" > "$LOG_FILE"
    echo "松仁大樓2024年錯誤日誌 - 開始時間: $(date)" > "$ERROR_LOG"
    
    # 計算總天數
    local total_days=$(calculate_total_days)
    print_info "總共需要查詢 $total_days 天"
    
    # 生成日期序列
    print_info "生成日期序列..."
    local dates=($(generate_date_sequence))
    
    if [ ${#dates[@]} -eq 0 ]; then
        print_error "無法生成日期序列"
        exit 1
    fi
    
    print_info "成功生成 ${#dates[@]} 個日期"
    
    # 統計變數
    local success_count=0
    local error_count=0
    local day_count=0
    
    # 記錄開始時間
    local start_time=$(date +%s)
    
    # 遍歷每一天
    for query_date in "${dates[@]}"; do
        day_count=$((day_count + 1))
        
        if query_single_day "$query_date" "$day_count" "$total_days"; then
            success_count=$((success_count + 1))
        else
            error_count=$((error_count + 1))
        fi
        
        # 顯示進度
        local progress=$((day_count * 100 / total_days))
        print_info "進度: ${progress}% (成功: $success_count, 失敗: $error_count)"
        
        # 延遲以避免對服務器造成過大負載
        if [ $day_count -lt $total_days ]; then
            sleep $DELAY_SECONDS
        fi
    done
    
    # 計算執行時間
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local hours=$((duration / 3600))
    local minutes=$(((duration % 3600) / 60))
    local seconds=$((duration % 60))
    
    # 輸出最終統計
    echo ""
    print_success "查詢完成！"
    print_info "總共查詢天數: $total_days"
    print_success "成功查詢: $success_count"
    print_error "失敗查詢: $error_count"
    print_info "執行時間: ${hours}小時 ${minutes}分鐘 ${seconds}秒"
    print_info "輸出目錄: $OUTPUT_DIR"
    print_info "日誌檔案: $LOG_FILE"
    print_info "錯誤日誌: $ERROR_LOG"
    
    # 記錄最終統計到日誌
    log_message "查詢完成 - 總計: $total_days, 成功: $success_count, 失敗: $error_count, 執行時間: ${duration}秒"
    
    if [ $error_count -gt 0 ]; then
        print_warning "有 $error_count 天查詢失敗，請檢查錯誤日誌: $ERROR_LOG"
        exit 1
    else
        print_success "所有查詢都成功完成！"
        exit 0
    fi
}

# 腳本入口點
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
