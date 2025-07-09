#!/bin/bash

# UTF-8 編碼測試腳本
# 測試 API 回應的編碼處理

# 設定變數
API_URL="http://localhost:5000/run"
BUILDING_ID="6"
TEST_DATE="2025/07/10"
OUTPUT_DIR="./encoding_test"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 創建測試目錄
mkdir -p "$OUTPUT_DIR"

print_info "開始 UTF-8 編碼測試"
print_info "測試日期: $TEST_DATE"
print_info "建築物ID: $BUILDING_ID"

# 準備請求資料
json_data="{\"date\": \"$TEST_DATE\", \"buildings\": [\"$BUILDING_ID\"]}"
print_info "請求資料: $json_data"

# 執行 API 請求
print_info "執行 API 請求..."
response=$(curl -s \
    -X POST \
    -H "Content-Type: application/json; charset=utf-8" \
    -H "Accept: text/csv; charset=utf-8" \
    -d "$json_data" \
    --connect-timeout 30 \
    --max-time 120 \
    "$API_URL" 2>&1)

curl_exit_code=$?

if [ $curl_exit_code -ne 0 ]; then
    print_error "API 請求失敗，退出碼: $curl_exit_code"
    exit 1
fi

print_success "API 請求成功"
print_info "回應長度: ${#response} 字符"

# 檢查回應內容
print_info "回應前 200 字符:"
echo "$response" | head -c 200
echo ""

# 檢查是否包含中文字符
if echo "$response" | grep -q "會議室\|時間\|房間"; then
    print_success "回應包含中文字符"
else
    print_warning "回應不包含預期的中文字符"
fi

# 測試不同的保存方法
print_info "測試不同的檔案保存方法..."

# 方法1: 使用 echo
echo "$response" > "${OUTPUT_DIR}/method1_echo.csv"
print_info "方法1 (echo): 已保存到 method1_echo.csv"

# 方法2: 使用 printf
printf '%s\n' "$response" > "${OUTPUT_DIR}/method2_printf.csv"
print_info "方法2 (printf): 已保存到 method2_printf.csv"

# 方法3: 使用 cat with here document
cat > "${OUTPUT_DIR}/method3_cat.csv" << EOF
$response
EOF
print_info "方法3 (cat): 已保存到 method3_cat.csv"

# 方法4: 直接重定向 curl 輸出
curl -s \
    -X POST \
    -H "Content-Type: application/json; charset=utf-8" \
    -H "Accept: text/csv; charset=utf-8" \
    -d "$json_data" \
    "$API_URL" > "${OUTPUT_DIR}/method4_direct.csv"
print_info "方法4 (直接重定向): 已保存到 method4_direct.csv"

# 檢查檔案編碼
print_info "檢查檔案編碼和內容..."

for method in method1_echo method2_printf method3_cat method4_direct; do
    file_path="${OUTPUT_DIR}/${method}.csv"
    
    if [ -f "$file_path" ]; then
        file_size=$(wc -c < "$file_path")
        print_info "檔案: ${method}.csv"
        print_info "  大小: ${file_size} bytes"
        
        # 檢查檔案編碼
        if command -v file >/dev/null 2>&1; then
            encoding=$(file -b --mime-encoding "$file_path")
            print_info "  編碼: $encoding"
        fi
        
        # 檢查是否包含中文
        if grep -q "會議室\|時間\|房間" "$file_path" 2>/dev/null; then
            print_success "  ✓ 包含中文字符"
        else
            print_error "  ✗ 不包含中文字符或編碼有問題"
        fi
        
        # 顯示前幾行
        print_info "  前3行內容:"
        head -3 "$file_path" | sed 's/^/    /'
        echo ""
    else
        print_error "檔案不存在: $file_path"
    fi
done

# 推薦最佳方法
print_info "編碼測試完成"
print_success "推薦使用方法4 (直接重定向 curl 輸出) 或方法2 (printf)"
print_info "測試檔案保存在: $OUTPUT_DIR"

# 清理測試檔案（可選）
read -p "是否刪除測試檔案？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$OUTPUT_DIR"
    print_info "測試檔案已刪除"
else
    print_info "測試檔案保留在: $OUTPUT_DIR"
fi
