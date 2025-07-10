# 設定變數
API_URL="http://localhost:5000/run"
BUILDING_ID="12"
BUILDING_NAME="瑞湖大樓"
YEAR="2024"
OUTPUT_DIR="./batch_reihu_building_data_${YEAR}"
LOG_FILE="${OUTPUT_DIR}/batch_query_log.txt"
ERROR_LOG="${OUTPUT_DIR}/batch_error_log.txt"
PROGRESS_FILE="${OUTPUT_DIR}/progress.txt"

# 並行設定
MAX_PARALLEL_JOBS=3  # 最大並行任務數
BATCH_SIZE=30        # 每批處理的天數
REQUEST_DELAY=0.5    # 每個請求之間的延遲（秒）

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_progress() {
    echo -e "${CYAN}[PROGRESS]${NC} $1"
}

print_worker() {
    local worker_id="$1"
    local message="$2"
    echo -e "${PURPLE}[WORKER-$worker_id]${NC} $message"
}

# 函數：記錄日誌（線程安全）
log_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp - $1" >> "$LOG_FILE"
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$timestamp - ERROR: $1" >> "$ERROR_LOG"
}

# 函數：更新進度（線程安全）
update_progress() {
    local success_count="$1"
    local error_count="$2"
    local total_processed="$3"
    local total_days="$4"
    
    {
        flock -x 200
        echo "$success_count,$error_count,$total_processed,$total_days" > "$PROGRESS_FILE"
    } 200>"$PROGRESS_FILE.lock"
}

# 函數：更新全域進度（原子操作）
update_global_progress() {
    local processed_increment="$1"
    local success_increment="$2"
    local error_increment="$3"
    
    {
        flock -x 200
        
        # 讀取當前進度
        local current_data=$(cat "$PROGRESS_FILE" 2>/dev/null || echo "0,0,0,366")
        IFS=',' read -r current_success current_error current_processed total_days <<< "$current_data"
        
        # 更新計數
        local new_success=$((current_success + success_increment))
        local new_error=$((current_error + error_increment))
        local new_processed=$((current_processed + processed_increment))
        
        # 寫入新進度
        echo "$new_success,$new_error,$new_processed,$total_days" > "$PROGRESS_FILE"
        
    } 200>"$PROGRESS_FILE.lock"
}

# 函數：讀取進度
read_progress() {
    if [ -f "$PROGRESS_FILE" ]; then
        cat "$PROGRESS_FILE"
    else
        echo "0,0,0,366"
    fi
}

# 函數：檢查API服務是否可用
check_api_service() {
    print_info "檢查API服務狀態..."
    
    local retry_count=0
    local max_retries=3
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s --connect-timeout 5 "http://localhost:5000/health" > /dev/null 2>&1; then
            print_success "API服務正常運行"
            return 0
        else
            retry_count=$((retry_count + 1))
            print_warning "API服務連接失敗，重試 $retry_count/$max_retries..."
            sleep 2
        fi
    done
    
    print_error "API服務無法連接，請確保服務正在運行在 localhost:5000"
    return 1
}

# 函數：創建輸出目錄
create_output_directory() {
    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
        print_info "創建輸出目錄: $OUTPUT_DIR"
    fi
    
    # 創建臨時目錄
    mkdir -p "${OUTPUT_DIR}/temp"
    mkdir -p "${OUTPUT_DIR}/workers"
}

# 函數：查詢單日會議室資料（工作函數）
query_single_day() {
    local query_date="$1"
    local worker_id="$2"
    
    # 格式化檔案名稱的日期 (YYYYMMDD)
    local file_date=$(echo "$query_date" | sed 's/\///g')
    local output_file="${OUTPUT_DIR}/${BUILDING_NAME}_${file_date}.csv"
    local temp_file="${OUTPUT_DIR}/temp/worker_${worker_id}_${file_date}.csv"
    
    # 準備JSON請求資料
    local json_data="{\"date\": \"$query_date\", \"buildings\": [\"$BUILDING_ID\"]}"
    
    # 發送請求
    local curl_exit_code=0
    curl -s \
        -X POST \
        -H "Content-Type: application/json; charset=utf-8" \
        -H "Accept: text/csv; charset=utf-8" \
        -d "$json_data" \
        --connect-timeout 30 \
        --max-time 120 \
        "$API_URL" > "$temp_file" 2>/dev/null

    curl_exit_code=$?

    if [ $curl_exit_code -eq 0 ]; then
        local file_size=$(wc -c < "$temp_file" 2>/dev/null || echo "0")

        # 檢查檔案是否為有效的CSV
        if [ "$file_size" -gt 100 ] && head -1 "$temp_file" | grep -q ","; then
            # 移動到最終位置
            mv "$temp_file" "$output_file"
            
            print_worker "$worker_id" "✅ 成功: $query_date (${file_size} bytes)"
            log_message "SUCCESS: Worker-$worker_id - $query_date - Size: ${file_size} bytes"

            # 檢查編碼
            if grep -q "會議室\|時間\|房間" "$output_file" 2>/dev/null; then
                log_message "SUCCESS: Worker-$worker_id - $query_date - UTF-8 encoding verified"
            fi

            return 0
        else
            # 清理失敗的檔案
            rm -f "$temp_file"
            
            if grep -q "error" "$temp_file" 2>/dev/null; then
                print_worker "$worker_id" "❌ API錯誤: $query_date"
                log_error "Worker-$worker_id - $query_date - API Error"
            else
                print_worker "$worker_id" "⚠️  資料異常: $query_date (${file_size} bytes)"
                log_error "Worker-$worker_id - $query_date - Invalid data: ${file_size} bytes"
            fi
            return 1
        fi
    else
        rm -f "$temp_file"
        print_worker "$worker_id" "🔌 網路失敗: $query_date (Exit: $curl_exit_code)"
        log_error "Worker-$worker_id - $query_date - Network failed: $curl_exit_code"
        return 1
    fi
}

# 函數：工作線程處理批次
process_batch() {
    local worker_id="$1"
    local batch_file="$2"
    
    local success_count=0
    local error_count=0
    local processed_count=0
    
    print_worker "$worker_id" "🚀 開始處理批次: $batch_file"
    
    while IFS= read -r query_date; do
        if [ -n "$query_date" ]; then
            if query_single_day "$query_date" "$worker_id"; then
                success_count=$((success_count + 1))
            else
                error_count=$((error_count + 1))
            fi
            
            processed_count=$((processed_count + 1))
            
            # 更新全域進度
            update_global_progress 1 $((success_count > error_count ? 1 : 0)) $((success_count == 0 ? 1 : 0))
            
            # 隨機延遲以避免同時請求
            local delay=$(echo "$REQUEST_DELAY + ($RANDOM % 100) / 100" | bc -l 2>/dev/null || echo "$REQUEST_DELAY")
            sleep "$delay"
        fi
    done < "$batch_file"
    
    # 寫入工作結果
    echo "$success_count,$error_count,$processed_count" > "${OUTPUT_DIR}/workers/worker_${worker_id}_result.txt"
    
    print_worker "$worker_id" "✅ 批次完成 - 成功: $success_count, 失敗: $error_count"
}

# 函數：生成2024年所有日期
generate_all_dates() {
    local dates=()
    
    # 生成2024年所有日期（366天）
    for month in {1..12}; do
        local days_in_month
        case $month in
            1|3|5|7|8|10|12) days_in_month=31 ;;
            4|6|9|11) days_in_month=30 ;;
            2) days_in_month=29 ;; # 2024是閏年
        esac
        
        for day in $(seq 1 $days_in_month); do
            printf "2024/%02d/%02d\n" $month $day
        done
    done
}

# 函數：分割日期到批次檔案
split_dates_to_batches() {
    local all_dates_file="${OUTPUT_DIR}/temp/all_dates.txt"
    
    # 生成所有日期
    generate_all_dates > "$all_dates_file"
    
    local total_dates=$(wc -l < "$all_dates_file")
    local total_batches=$(( (total_dates + BATCH_SIZE - 1) / BATCH_SIZE ))
    
    print_info "總日期數: $total_dates"
    print_info "批次大小: $BATCH_SIZE"
    print_info "總批次數: $total_batches"
    
    # 分割檔案
    split -l "$BATCH_SIZE" "$all_dates_file" "${OUTPUT_DIR}/temp/batch_"
    
    # 重命名批次檔案
    local batch_counter=1
    for batch_file in "${OUTPUT_DIR}"/temp/batch_*; do
        if [ -f "$batch_file" ]; then
            mv "$batch_file" "${OUTPUT_DIR}/temp/batch_$(printf '%03d' $batch_counter).txt"
            batch_counter=$((batch_counter + 1))
        fi
    done
    
    echo "$total_batches"
}

# 函數：進度監控
monitor_progress() {
    local total_days="$1"
    
    print_info "🔍 啟動進度監控..."
    
    local last_processed=0
    local stall_count=0
    
    while true; do
        local progress_data=$(read_progress)
        IFS=',' read -r success_count error_count total_processed total_days_check <<< "$progress_data"
        
        # 檢查是否完成
        if [ "$total_processed" -ge "$total_days" ]; then
            print_progress "🎯 所有任務已完成！"
            break
        fi
        
        # 計算進度百分比
        local progress_percent=0
        if [ "$total_days" -gt 0 ]; then
            progress_percent=$((total_processed * 100 / total_days))
        fi
        
        # 計算成功率
        local success_rate=0
        if [ "$total_processed" -gt 0 ]; then
            success_rate=$((success_count * 100 / total_processed))
        fi
        
        # 計算處理速度
        local speed_info=""
        if [ "$total_processed" -gt "$last_processed" ]; then
            local processed_diff=$((total_processed - last_processed))
            speed_info=" | 速度: ${processed_diff}/5秒"
            stall_count=0
        else
            stall_count=$((stall_count + 1))
            if [ $stall_count -ge 3 ]; then
                speed_info=" | ⚠️ 處理停滯"
            fi
        fi
        
        # 估算剩餘時間
        local eta_info=""
        if [ "$total_processed" -gt 0 ] && [ "$total_processed" -lt "$total_days" ]; then
            local remaining=$((total_days - total_processed))
            local avg_speed=$(echo "scale=2; $total_processed / ($(date +%s) - $start_time)" | bc -l 2>/dev/null || echo "0")
            if [ "$avg_speed" != "0" ]; then
                local eta_seconds=$(echo "scale=0; $remaining / $avg_speed" | bc -l 2>/dev/null || echo "0")
                if [ "$eta_seconds" -gt 0 ]; then
                    local eta_minutes=$((eta_seconds / 60))
                    local eta_hours=$((eta_minutes / 60))
                    eta_minutes=$((eta_minutes % 60))
                    eta_info=" | ETA: ${eta_hours}h${eta_minutes}m"
                fi
            fi
        fi
        
        print_progress "進度: ${progress_percent}% | 已處理: ${total_processed}/${total_days} | 成功: ${success_count} | 失敗: ${error_count} | 成功率: ${success_rate}%${speed_info}${eta_info}"
        
        last_processed=$total_processed
        sleep 5
    done
}

# 主函數
main() {
    print_info "🚀 開始執行松仁大樓2024年批次查詢腳本"
    print_info "建築物: $BUILDING_NAME (ID: $BUILDING_ID)"
    print_info "查詢年份: $YEAR"
    print_info "最大並行數: $MAX_PARALLEL_JOBS"
    print_info "批次大小: $BATCH_SIZE"
    print_info "輸出目錄: $OUTPUT_DIR"
    
    # 檢查API服務
    if ! check_api_service; then
        exit 1
    fi
    
    # 創建輸出目錄
    create_output_directory
    
    # 檢查bc命令是否可用（用於計算延遲）
    if ! command -v bc >/dev/null 2>&1; then
        print_warning "bc命令不可用，使用固定延遲"
    fi
    
    # 初始化日誌檔案
    echo "松仁大樓2024年批次查詢日誌 - 開始時間: $(date)" > "$LOG_FILE"
    echo "松仁大樓2024年批次錯誤日誌 - 開始時間: $(date)" > "$ERROR_LOG"
    echo "0,0,0,366" > "$PROGRESS_FILE"
    
    # 記錄開始時間
    local start_time=$(date +%s)
    
    # 將開始時間設為全域變數，供進度監控使用
    echo "$start_time" > "${OUTPUT_DIR}/start_time.txt"
    
    # 分割日期到批次
    print_info "📂 準備批次檔案..."
    local total_batches=$(split_dates_to_batches)
    local total_days=366
    
    # 啟動進度監控（背景執行）
    start_time=$start_time monitor_progress "$total_days" &
    local monitor_pid=$!
    
    # 處理所有批次
    print_info "⚡ 開始並行處理 $total_batches 個批次..."
    
    local job_count=0
    local pids=()
    
    for batch_file in "${OUTPUT_DIR}"/temp/batch_*.txt; do
        if [ -f "$batch_file" ]; then
            # 等待直到有可用的工作槽位
            while [ ${#pids[@]} -ge $MAX_PARALLEL_JOBS ]; do
                # 檢查並移除已完成的任務
                local new_pids=()
                for pid in "${pids[@]}"; do
                    if kill -0 "$pid" 2>/dev/null; then
                        new_pids+=("$pid")
                    fi
                done
                pids=("${new_pids[@]}")
                sleep 0.1
            done
            
            # 啟動新的工作線程
            job_count=$((job_count + 1))
            local worker_id=$(printf '%02d' $job_count)
            
            process_batch "$worker_id" "$batch_file" &
            local worker_pid=$!
            pids+=("$worker_pid")
            
            print_info "🔄 啟動工作線程 $worker_id (PID: $worker_pid) - 批次: $(basename "$batch_file")"
            
            # 短暫延遲避免同時啟動
            sleep 0.2
        fi
    done
    
    # 等待所有工作線程完成
    print_info "⏳ 等待所有工作線程完成..."
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # 停止進度監控
    kill "$monitor_pid" 2>/dev/null
    wait "$monitor_pid" 2>/dev/null
    
    # 計算最終統計
    local total_success=0
    local total_error=0
    local total_processed=0
    
    for result_file in "${OUTPUT_DIR}"/workers/worker_*_result.txt; do
        if [ -f "$result_file" ]; then
            IFS=',' read -r success error processed < "$result_file"
            total_success=$((total_success + success))
            total_error=$((total_error + error))
            total_processed=$((total_processed + processed))
        fi
    done
    
    # 計算執行時間
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local hours=$((duration / 3600))
    local minutes=$(((duration % 3600) / 60))
    local seconds=$((duration % 60))
    
    # 計算效能統計
    local avg_time_per_day=0
    if [ "$total_processed" -gt 0 ]; then
        avg_time_per_day=$(echo "scale=2; $duration / $total_processed" | bc -l 2>/dev/null || echo "N/A")
    fi
    
    local success_rate=0
    if [ "$total_processed" -gt 0 ]; then
        success_rate=$((total_success * 100 / total_processed))
    fi
    
    # 輸出最終統計
    echo ""
    echo "=================================="
    print_success "🎉 批次查詢完成！"
    echo "=================================="
    print_info "📊 執行統計:"
    print_info "   總查詢天數: $total_days"
    print_info "   實際處理: $total_processed"
    print_success "   成功查詢: $total_success"
    print_error "   失敗查詢: $total_error"
    print_info "   成功率: ${success_rate}%"
    print_info "   執行時間: ${hours}小時 ${minutes}分鐘 ${seconds}秒"
    if [ "$avg_time_per_day" != "N/A" ]; then
        print_info "   平均每天: ${avg_time_per_day}秒"
    fi
    print_info "   並行任務數: $MAX_PARALLEL_JOBS"
    print_info "   批次大小: $BATCH_SIZE"
    echo "=================================="
    print_info "📁 輸出目錄: $OUTPUT_DIR"
    print_info "📋 日誌檔案: $LOG_FILE"
    print_info "🚨 錯誤日誌: $ERROR_LOG"
    
    # 記錄最終統計到日誌
    log_message "批次查詢完成 - 總計: $total_days, 處理: $total_processed, 成功: $total_success, 失敗: $total_error, 執行時間: ${duration}秒"
    
    # 清理臨時檔案
    print_info "🧹 清理臨時檔案..."
    rm -rf "${OUTPUT_DIR}/temp"
    rm -rf "${OUTPUT_DIR}/workers"
    rm -f "$PROGRESS_FILE.lock"
    
    if [ $total_error -gt 0 ]; then
        print_warning "⚠️  有 $total_error 天查詢失敗，請檢查錯誤日誌: $ERROR_LOG"
        exit 1
    else
        print_success "🎊 所有查詢都成功完成！"
        exit 0
    fi
}

# 腳本入口點
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
