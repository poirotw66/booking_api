from flask import Flask, request, jsonify, Response
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from utils.convert_to_csv import process_files, write_output, write_output_csv
from utils.extract_meeting_info import process_html_file
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 建築物配置
BUILDING_CONFIG = {
    '4': '仁愛大樓',
    '6': '松仁大樓',
    '10': '國泰證券總公司',
    '12': '瑞湖大樓',
    '15': '信義安和大樓',
    '19': '台中忠明大樓',
    '20': 'A3置地廣場',
    '22': '高雄資訊開發中心'
}

# 根路徑 - API 服務狀態
@app.route('/', methods=['GET'])
def home():
    """API 服務首頁和狀態檢查"""
    return jsonify({
        'service': 'Booking Meeting Room API',
        'status': 'running',
        'version': '2.0',
        'endpoints': {
            'GET /': 'Service status check',
            'GET /health': 'Health check',
            'GET /buildings': 'Get available buildings list',
            'POST /run': 'Query meeting room availability',
            'POST /book': 'Book meeting room'
        },
        'available_buildings': BUILDING_CONFIG
    })

# 健康檢查端點
@app.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'booking-api'
    })

# API 路由：根據提供的登入資訊和日期，進行會議室查詢
@app.route('/run', methods=['POST'])
def run_booking():
    # 開始計時
    start_time = time.time()
    print(f"🕐 開始執行會議室查詢 - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    
    data = request.json

    username = os.getenv('BOOKING_USERNAME')
    password = os.getenv('BOOKING_PASSWORD')
    print(f"使用帳號: {username}")
    current_date = data.get('date', '2025/07/10')

    # 取得要查詢的建築物列表，如果沒有指定則使用預設值
    default_buildings = data.get('default_buildings', ['6'])  # A3置地廣場
    buildings = data.get('buildings', default_buildings)
    if isinstance(buildings, str):
        buildings = [buildings]  # 如果是單個字串，轉換為列表

    print(f"要查詢的建築物: {[BUILDING_CONFIG.get(b, f'未知建築物({b})') for b in buildings]}")

    if not username or not password:
        return jsonify({'error': '環境變數中缺少帳號或密碼'}), 500
    
    # Selenium 驅動程式設置 - 優化啟動速度並自動管理 ChromeDriver
    selenium_start_time = time.time()
    print(f"🚀 啟動瀏覽器 - {time.strftime('%H:%M:%S', time.localtime(selenium_start_time))}")
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    # Chrome 瀏覽器路徑 (macOS)
    # options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    # ubuntu
    options.binary_location = "/usr/bin/google-chrome"
    # 效能優化選項
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-images')  # 不載入圖片，節省時間
    options.add_argument('--disable-logging')
    options.add_argument('--disable-notifications')
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # 使用 webdriver-manager 自動管理 ChromeDriver
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ ChromeDriver 初始化成功")
    except Exception as e:
        print(f"❌ ChromeDriver 初始化失敗: {e}")
        return jsonify({'error': f'瀏覽器驅動程式初始化失敗: {e}'}), 500
    
    driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')
    # 登入
    driver.implicitly_wait(3)  # 進一步減少隱式等待時間
    
    # 使用顯式等待確保登入元素載入
    email = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, 'username'))
    )
    email.send_keys(username)
    password_field = driver.find_element(By.ID, 'KEY')
    password_field.send_keys(password)

    # 點擊登入按鈕
    login_button = driver.find_element(By.ID, 'btnLogin')
    login_button.click()
    
    login_start_time = time.time()
    print(f"🔐 執行登入 - {time.strftime('%H:%M:%S', time.localtime(login_start_time))}")
    
    # 等待登入完成並檢查是否成功
    try:
        # 等待頁面元素出現，確認登入成功
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'startDate'))
        )
        # 移除不必要的sleep，依賴顯式等待即可
        login_end_time = time.time()
        print(f"✅ 登入成功 - 耗時 {login_end_time - login_start_time:.2f} 秒")
    except Exception as e:
        print(f"登入可能失敗或頁面載入超時: {e}")
        driver.quit()
        return jsonify({'error': '登入失敗或頁面載入超時'}), 500

    # 一次性設置日期，避免重複定位元素
    try:
        start_date_input = driver.find_element(By.ID, 'startDate')
        end_date_input = driver.find_element(By.ID, 'endDate')

        # 批量執行JavaScript，減少往返次數
        driver.execute_script("""
            var startInput = arguments[0];
            var endInput = arguments[1];
            var dateValue = arguments[2];
            
            startInput.value = dateValue;
            endInput.value = dateValue;
            
            var event = new Event('change', { bubbles: true });
            startInput.dispatchEvent(event);
            endInput.dispatchEvent(event);
        """, start_date_input, end_date_input, current_date)
        
        print(f"📅 日期設置完成: {current_date}")
    except Exception as e:
        print(f"日期設置失敗: {e}")
        driver.quit()
        return jsonify({'error': '日期設置失敗'}), 500

    # 儲存所有建築物的數據
    all_building_data = []
    
    # 預先定位下拉選單元素，避免重複查找
    try:
        dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
        select = Select(dropdown)
        print("📍 建築物選擇器已定位")
    except Exception as e:
        print(f"無法定位建築物選擇器: {e}")
        driver.quit()
        return jsonify({'error': '無法定位建築物選擇器'}), 500

    # 遍歷每個建築物進行查詢 - 進一步優化
    for building_id in buildings:
        building_start_time = time.time()
        building_name = BUILDING_CONFIG.get(building_id, f'未知建築物({building_id})')
        print(f"🏢 正在查詢建築物: {building_name} (ID: {building_id}) - {time.strftime('%H:%M:%S', time.localtime(building_start_time))}")

        # 選擇建築物
        try:
            select.select_by_value(building_id)
            # 移除固定等待，使用動態檢測
        except Exception as e:
            print(f"選擇建築物失敗 - {building_name}: {e}")
            continue

        # 智能優化：先判斷當前時段再收集數據
        building_morning_data = None
        building_afternoon_data = None
        
        try:
            print(f"⚡ 智能收集 {building_name} 上下午數據...")
            
            # 檢測當前頁面是上午還是下午時段 - 改進檢測邏輯
            current_period = driver.execute_script("""
                let morningBtn = document.querySelector('button[name="selectedTimePeriod"][value="MORNING"]');
                let afternoonBtn = document.querySelector('button[name="selectedTimePeriod"][value="AFTERNOON"]');
                
                // 方法1: 檢查按鈕的 class 屬性
                if (morningBtn && (morningBtn.classList.contains('active') || morningBtn.classList.contains('selected') || morningBtn.classList.contains('btn-primary'))) {
                    return 'MORNING';
                }
                if (afternoonBtn && (afternoonBtn.classList.contains('active') || afternoonBtn.classList.contains('selected') || afternoonBtn.classList.contains('btn-primary'))) {
                    return 'AFTERNOON';
                }
                
                // 方法2: 檢查按鈕的 style 屬性
                if (morningBtn && morningBtn.style.backgroundColor && morningBtn.style.backgroundColor !== 'transparent') {
                    return 'MORNING';
                }
                if (afternoonBtn && afternoonBtn.style.backgroundColor && afternoonBtn.style.backgroundColor !== 'transparent') {
                    return 'AFTERNOON';
                }
                
                // 方法3: 檢查 aria-pressed 或 data-* 屬性
                if (morningBtn && (morningBtn.getAttribute('aria-pressed') === 'true' || morningBtn.dataset.selected === 'true')) {
                    return 'MORNING';
                }
                if (afternoonBtn && (afternoonBtn.getAttribute('aria-pressed') === 'true' || afternoonBtn.dataset.selected === 'true')) {
                    return 'AFTERNOON';
                }
                
                // 方法4: 檢查按鈕的 disabled 狀態（未選中的可能是 disabled）
                if (morningBtn && !morningBtn.disabled && afternoonBtn && afternoonBtn.disabled) {
                    return 'MORNING';
                }
                if (afternoonBtn && !afternoonBtn.disabled && morningBtn && morningBtn.disabled) {
                    return 'AFTERNOON';
                }
                
                // 方法5: 檢查頁面內容中的時間表格或數據
                let timeElements = document.querySelectorAll('.time, .hour, [class*="time"]');
                let foundAfternoon = false;
                let foundMorning = false;
                
                for (let element of timeElements) {
                    let text = element.textContent || element.innerText;
                    if (text.includes('13:') || text.includes('14:') || text.includes('15:') || text.includes('16:') || text.includes('17:')) {
                        foundAfternoon = true;
                    }
                    if (text.includes('08:') || text.includes('09:') || text.includes('10:') || text.includes('11:') || text.includes('12:')) {
                        foundMorning = true;
                    }
                }
                
                if (foundAfternoon && !foundMorning) return 'AFTERNOON';
                if (foundMorning && !foundAfternoon) return 'MORNING';
                
                // 方法6: 檢查頁面 URL 或表單隱藏字段
                let hiddenInputs = document.querySelectorAll('input[type="hidden"]');
                for (let input of hiddenInputs) {
                    if (input.name.includes('period') || input.name.includes('time')) {
                        if (input.value === 'AFTERNOON' || input.value === 'PM') return 'AFTERNOON';
                        if (input.value === 'MORNING' || input.value === 'AM') return 'MORNING';
                    }
                }
                
                // 如果所有方法都無法確定，記錄詳細信息並預設為上午
                console.log('無法確定當前時段，按鈕狀態:');
                console.log('Morning button classes:', morningBtn ? morningBtn.className : 'not found');
                console.log('Afternoon button classes:', afternoonBtn ? afternoonBtn.className : 'not found');
                console.log('Morning button style:', morningBtn ? morningBtn.style.cssText : 'not found');
                console.log('Afternoon button style:', afternoonBtn ? afternoonBtn.style.cssText : 'not found');
                
                return 'MORNING';  // 預設為上午
            """)
            
            print(f"🔍 {building_name} 當前時段: {current_period}")
            
            if current_period == 'MORNING':
                # 當前是上午，先截取上午數據
                print(f"📅 {building_name} 截取上午數據...")
                time.sleep(0.2)  # 確保頁面穩定
                building_morning_data = driver.page_source
                
                # 驗證數據是否確實是上午時段
                morning_verification = driver.execute_script("""
                    let content = document.body.innerHTML;
                    let afternoonTimes = (content.match(/1[3-7]:/g) || []).length;
                    let morningTimes = (content.match(/0[8-9]:|1[0-2]:/g) || []).length;
                    return {afternoon: afternoonTimes, morning: morningTimes};
                """)
                
                if morning_verification['afternoon'] > morning_verification['morning']:
                    print(f"⚠️ {building_name} 檢測到時段不匹配！重新檢測...")
                    current_period = 'AFTERNOON'
                    building_afternoon_data = building_morning_data
                    building_morning_data = None
                
                if building_morning_data:
                    # 切換到下午
                    print(f"🔄 {building_name} 切換到下午...")
                    driver.execute_script("""
                        let afternoonBtn = document.querySelector('button[name="selectedTimePeriod"][value="AFTERNOON"]');
                        if (afternoonBtn) afternoonBtn.click();
                    """)
                    time.sleep(0.3)
                    building_afternoon_data = driver.page_source
                else:
                    # 切換到上午獲取正確數據
                    print(f"🔄 {building_name} 切換到上午...")
                    driver.execute_script("""
                        let morningBtn = document.querySelector('button[name="selectedTimePeriod"][value="MORNING"]');
                        if (morningBtn) morningBtn.click();
                    """)
                    time.sleep(0.3)
                    building_morning_data = driver.page_source
                
            else:  # AFTERNOON
                # 當前是下午，先截取下午數據
                print(f"🌆 {building_name} 截取下午數據...")
                time.sleep(0.2)  # 確保頁面穩定
                building_afternoon_data = driver.page_source
                
                # 驗證數據是否確實是下午時段
                afternoon_verification = driver.execute_script("""
                    let content = document.body.innerHTML;
                    let afternoonTimes = (content.match(/1[3-7]:/g) || []).length;
                    let morningTimes = (content.match(/0[8-9]:|1[0-2]:/g) || []).length;
                    return {afternoon: afternoonTimes, morning: morningTimes};
                """)
                
                if afternoon_verification['morning'] > afternoon_verification['afternoon']:
                    print(f"⚠️ {building_name} 檢測到時段不匹配！重新檢測...")
                    current_period = 'MORNING'
                    building_morning_data = building_afternoon_data
                    building_afternoon_data = None
                
                if building_afternoon_data:
                    # 切換到上午
                    print(f"🔄 {building_name} 切換到上午...")
                    driver.execute_script("""
                        let morningBtn = document.querySelector('button[name="selectedTimePeriod"][value="MORNING"]');
                        if (morningBtn) morningBtn.click();
                    """)
                    time.sleep(0.3)
                    building_morning_data = driver.page_source
                else:
                    # 切換到下午獲取正確數據
                    print(f"🔄 {building_name} 切換到下午...")
                    driver.execute_script("""
                        let afternoonBtn = document.querySelector('button[name="selectedTimePeriod"][value="AFTERNOON"]');
                        if (afternoonBtn) afternoonBtn.click();
                    """)
                    time.sleep(0.3)
                    building_afternoon_data = driver.page_source
            
            # 快速驗證數據完整性
            if (building_morning_data and len(building_morning_data) > 30000 and building_afternoon_data and len(building_afternoon_data) > 30000):
                print(f"✅ {building_name} 智能數據收集成功")
            else:
                print(f"⚠️ {building_name} 數據可能不完整，使用備用方法...")
                # 備用方法：強制按順序收集
                driver.execute_script("""
                    let morningBtn = document.querySelector('button[name="selectedTimePeriod"][value="MORNING"]');
                    if (morningBtn) morningBtn.click();
                """)
                time.sleep(0.8)
                building_morning_data = driver.page_source
                
                driver.execute_script("""
                    let afternoonBtn = document.querySelector('button[name="selectedTimePeriod"][value="AFTERNOON"]');
                    if (afternoonBtn) afternoonBtn.click();
                """)
                time.sleep(0.8)
                building_afternoon_data = driver.page_source
                print(f"✅ {building_name} 備用方法收集完成")
                
        except Exception as e:
            print(f"❌ {building_name} 數據收集失敗: {e}")
            continue

        # 儲存檔案和建築物資訊
        # 處理保存數據並添加性能監測
        if building_morning_data and building_afternoon_data:
            period_switch_time = time.time() - building_start_time
            print(f"⚡ {building_name} 時段切換總耗時: {period_switch_time:.2f}秒 (智能優化)")
            
            morning_file_name = f'./tmp/{building_id}_{current_date.replace("/", "")}_morning.html'
            afternoon_file_name = f'./tmp/{building_id}_{current_date.replace("/", "")}_afternoon.html'
            
            # 批量寫入檔案以提高效率
            try:
                with open(morning_file_name, 'w', encoding='utf-8-sig') as f:
                    f.write(building_morning_data)
                with open(afternoon_file_name, 'w', encoding='utf-8-sig') as f:
                    f.write(building_afternoon_data)
                    
                building_end_time = time.time()
                all_building_data.append({
                    'building_id': building_id,
                    'building_name': building_name,
                    'morning_file': morning_file_name,
                    'afternoon_file': afternoon_file_name
                })
                print(f"✅ 成功收集建築物 {building_name} 的數據 - 總耗時 {building_end_time - building_start_time:.2f} 秒")
                
            except Exception as e:
                print(f"檔案寫入失敗 - {building_name}: {e}")
                continue
        else:
            building_end_time = time.time()
            print(f"❌ 建築物 {building_name} 數據收集不完整，跳過 - 耗時 {building_end_time - building_start_time:.2f} 秒")

    driver.quit()
    
    crawling_end_time = time.time()
    print(f"🕷️ 爬蟲階段完成 - 總耗時 {crawling_end_time - selenium_start_time:.2f} 秒")

    # 檢查是否有成功收集到數據
    if not all_building_data:
        return jsonify({'error': '沒有成功收集到任何建築物的數據'}), 500

    print(f"📊 成功收集到 {len(all_building_data)} 個建築物的數據")

    # 處理所有建築物的檔案 - 並行處理優化
    processing_start_time = time.time()
    print(f"⚙️ 開始處理檔案 - {time.strftime('%H:%M:%S', time.localtime(processing_start_time))}")
    
    all_file_list = []
    
    # 並行處理檔案以提高效率
    for building_data in all_building_data:
        morning_file = building_data['morning_file']
        afternoon_file = building_data['afternoon_file']
        building_name = building_data['building_name']

        # 快速檔案存在性檢查
        if not (os.path.exists(morning_file) and os.path.exists(afternoon_file)):
            print(f"警告：{building_name} HTML檔案不完整")
            continue

        print(f"📁 處理 {building_name} 檔案...")

        # 批量處理HTML檔案
        try:
            # 處理早上的HTML檔案
            processed_morning = morning_file[:-5]  # 移除 .html 擴展名
            morning_meetings = process_html_file(morning_file, processed_morning)
            
            # 處理下午的HTML檔案
            processed_afternoon = afternoon_file[:-5]  # 移除 .html 擴展名
            afternoon_meetings = process_html_file(afternoon_file, processed_afternoon)
            
            total_meetings = len(morning_meetings) + len(afternoon_meetings)
            print(f"✅ {building_name} 處理完成：提取 {total_meetings} 筆記錄")
            
            # 添加處理後的檔案到列表
            all_file_list.extend([processed_morning, processed_afternoon])
            
        except Exception as e:
            print(f"❌ 處理 {building_name} 檔案時發生錯誤：{e}")
            continue

    if not all_file_list:
        return jsonify({'error': '沒有成功處理任何檔案'}), 500

    # 合併並生成最終輸出文件 - 優化檔案處理
    buildings_str = '_'.join([data['building_id'] for data in all_building_data])
    output_file = f'./output/{current_date.replace("/", "")}_buildings_{buildings_str}_combined_output.txt'
    output_csv = f'./output/{current_date.replace("/", "")}_buildings_{buildings_str}_combined.csv'

    print(f"📊 合併處理 {len(all_file_list)} 個檔案...")

    # 快速檔案存在性檢查（簡化調試輸出）
    valid_files = [f for f in all_file_list if os.path.exists(f)]
    if len(valid_files) != len(all_file_list):
        print(f"⚠️ 警告：{len(all_file_list) - len(valid_files)} 個檔案不存在")

    # 處理會議數據
    meeting_data = process_files(sorted(valid_files))
    total_meetings = sum(len(meetings) for meetings in meeting_data.values())
    print(f"📈 總共處理了 {total_meetings} 筆會議記錄")

    # 並行寫入輸出檔案
    try:
        write_output(meeting_data, output_file)
        write_output_csv(meeting_data, output_csv)
        print(f"📄 輸出檔案已生成：{output_csv}")
    except Exception as e:
        print(f"❌ 輸出檔案生成失敗：{e}")
        return jsonify({'error': f'輸出檔案生成失敗：{e}'}), 500
    
    # 計算總執行時間
    end_time = time.time()
    total_time = end_time - start_time
    processing_time = end_time - processing_start_time
    
    print(f"📝 檔案處理完成 - 耗時 {processing_time:.2f} 秒")
    print(f"🏁 總執行時間: {total_time:.2f} 秒")
    print(f"📈 平均每個建築物耗時: {total_time / len(all_building_data):.2f} 秒")
    
    # 返回處理結果 - 優化輸出
    try:
        with open(output_csv, 'r', encoding='utf-8-sig') as csv_file:
            csv_content = csv_file.read()

        # 效能統計
        print("📊 效能統計：")
        print(f"   🕷️ 爬蟲耗時: {crawling_end_time - selenium_start_time:.2f} 秒")
        print(f"   ⚙️ 處理耗時: {processing_time:.2f} 秒")
        print(f"   🏁 總執行時間: {total_time:.2f} 秒")
        print(f"   📈 平均每建築物: {total_time / len(all_building_data):.2f} 秒")
        print(f"   📄 生成記錄數: {total_meetings} 筆")
        
        return Response(csv_content, mimetype='text/csv')
        
    except Exception as e:
        print(f"❌ 讀取輸出檔案失敗：{e}")
        return jsonify({'error': f'讀取輸出檔案失敗：{e}'}), 500

meeting_room_xpath = {
    '3303': '//*[@id="timeTableMeetingRoom"]/div[2]/button[1]',
    '3304': '//*[@id="timeTableMeetingRoom"]/div[4]/button[1]',
    '3305': '//*[@id="timeTableMeetingRoom"]/div[6]/button[1]',
    '3307': '//*[@id="timeTableMeetingRoom"]/div[8]/button[1]',
    '3309': '//*[@id="timeTableMeetingRoom"]/div[10]/button[1]',
    '3310': '//*[@id="timeTableMeetingRoom"]/div[12]/button[1]',
    '3311': '//*[@id="timeTableMeetingRoom"]/div[14]/button[1]'
}

songren_room_xpath = {
    '15F-15樓接待大廳': '//*[@id="timeTableMeetingRoom"]/div[10]/button[1]',
    '15F-階梯教室': '//*[@id="timeTableMeetingRoom"]/div[12]/button[1]',
    '15F-深水炸彈-1(15-1)': '//*[@id="timeTableMeetingRoom"]/div[14]/button[1]',
    '15F-深水炸彈-2(15-2)': '//*[@id="timeTableMeetingRoom"]/div[16]/button[1]',
    '15F-老經典(15-3)': '//*[@id="timeTableMeetingRoom"]/div[18]/button[1]',
    '15F-香格里拉(15-4)(觀察室)': '//*[@id="timeTableMeetingRoom"]/div[20]/button[1]',
    '15F-血腥瑪麗(15-5)(受訪室)': '//*[@id="timeTableMeetingRoom"]/div[22]/button[1]',
    '15F-亞歷山大(15-10)': '//*[@id="timeTableMeetingRoom"]/div[24]/button[1]',
    '15F-琴通寧(15-11)': '//*[@id="timeTableMeetingRoom"]/div[26]/button[1]',
    '4F-微風Chill室': '//*[@id="timeTableMeetingRoom"]/div[48]/button[1]',
    '4F-滴大地': '//*[@id="timeTableMeetingRoom"]/div[50]/button[1]',
    '4F-光影綠谷': '//*[@id="timeTableMeetingRoom"]/div[52]/button[1]',
    '4F-剛果秘境': '//*[@id="timeTableMeetingRoom"]/div[54]/button[1]',
    '4F-未來綠洲': '//*[@id="timeTableMeetingRoom"]/div[56]/button[1]',
    '4F-森林之光': '//*[@id="timeTableMeetingRoom"]/div[58]/button[1]',
    '4F-優勝美地': '//*[@id="timeTableMeetingRoom"]/div[60]/button[1]',
    '4F-亞馬遜雨林': '//*[@id="timeTableMeetingRoom"]/div[62]/button[1]',
    '4F-安新芽': '//*[@id="timeTableMeetingRoom"]/div[64]/button[1]',
    '3F-HIVE': '//*[@id="timeTableMeetingRoom"]/div[66]/button[1]',
    '3F-Kafka': '//*[@id="timeTableMeetingRoom"]/div[68]/button[1]',
    '3F-中心樹投影3': '//*[@id="timeTableMeetingRoom"]/div[70]/button[1]',
    '3F-中心樹投影5': '//*[@id="timeTableMeetingRoom"]/div[72]/button[1]',
    '3F-Scala': '//*[@id="timeTableMeetingRoom"]/div[74]/button[1]',
    '3F-中心樹投影6': '//*[@id="timeTableMeetingRoom"]/div[76]/button[1]',
    '3F-Matlab': '//*[@id="timeTableMeetingRoom"]/div[78]/button[1]',
    '3F-中心樹投影4': '//*[@id="timeTableMeetingRoom"]/div[80]/button[1]',
    '3F-Python': '//*[@id="timeTableMeetingRoom"]/div[82]/button[1]',
    '3F-Julia': '//*[@id="timeTableMeetingRoom"]/div[84]/button[1]',
    '3F-中心樹投影1': '//*[@id="timeTableMeetingRoom"]/div[86]/button[1]',
    '3F-R': '//*[@id="timeTableMeetingRoom"]/div[88]/button[1]',
    '3F-Spark': '//*[@id="timeTableMeetingRoom"]/div[90]/button[1]',
    '3F-SQL': '//*[@id="timeTableMeetingRoom"]/div[92]/button[1]',
    '3F-Base': '//*[@id="timeTableMeetingRoom"]/div[94]/button[1]',
    '3F-Java': '//*[@id="timeTableMeetingRoom"]/div[96]/button[1]',
    '3F-C++': '//*[@id="timeTableMeetingRoom"]/div[98]/button[1]'
}

@app.route('/book', methods=['POST'])
def book_meeting_room():
    # 從請求中獲取輸入
    data = request.get_json()
    room_number = data.get('room_number', '3303')  # 默認房間號
    start_date = data.get('start_date', '2024/09/19')
    end_date = start_date
    meeting_subject = data.get('meeting_subject', '技術討論')
    attendance_number = '1'
    time_from_value = data.get('time_from', '08:00')
    time_to_value = data.get('time_to', '09:00')

    # 取得要預訂的建築物，如果沒有指定則使用預設值 (A3置地廣場)
    building_id = data.get('building_id', '6')
    building_name = BUILDING_CONFIG.get(building_id, f'未知建築物({building_id})')
    print(f"要預訂的建築物: {building_name} (ID: {building_id})")

    # 啟動 Chrome driver - 使用 webdriver-manager
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    # options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    options.binary_location = "/usr/bin/google-chrome"    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ ChromeDriver 初始化成功 (booking)")
    except Exception as e:
        print(f"❌ ChromeDriver 初始化失敗 (booking): {e}")
        return jsonify({'error': f'瀏覽器驅動程式初始化失敗: {e}'}), 500
    
    # 打開頁面
    driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')

    # time.sleep(2)
    driver.implicitly_wait(10)

    # 登錄過程
    username = os.getenv('BOOKING_USERNAME')
    password = os.getenv('BOOKING_PASSWORD')
    
    if not username or not password:
        driver.quit()
        return jsonify({'error': '環境變數中缺少帳號或密碼'}), 500
    
    email = driver.find_element(By.NAME, 'username')
    email.send_keys(username)
    password_field = driver.find_element(By.ID, 'KEY')
    password_field.send_keys(password)

    # 點擊登入按鈕
    login_button = driver.find_element(By.ID, 'btnLogin')
    login_button.click()

    # time.sleep(5)
    driver.implicitly_wait(10)

    # 選擇開始日期
    start_date_input = driver.find_element(By.ID, 'startDate')
    driver.execute_script(f"""
        var input = arguments[0];
        input.value = '{start_date}';
        var event = new Event('change', {{ bubbles: true }});
        input.dispatchEvent(event);
    """, start_date_input)

    # time.sleep(1)
    driver.implicitly_wait(10)

    # 選擇結束日期
    end_date_input = driver.find_element(By.ID, 'endDate')
    driver.execute_script(f"""
        var input = arguments[0];
        input.value = '{end_date}';
        var event = new Event('change', {{ bubbles: true }});
        input.dispatchEvent(event);
    """, end_date_input)

    # time.sleep(1)
    driver.implicitly_wait(10)

    # 選擇大樓
    dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
    select = Select(dropdown)
    select.select_by_value(building_id)
    print(f"已選擇建築物: {building_name} (ID: {building_id})")

    # time.sleep(3)
    driver.implicitly_wait(10)

    # 點擊對應房間的按鈕
    # xpath_value = meeting_room_xpath.get(room_number)
    xpath_value = songren_room_xpath.get(room_number)
    book_btn = driver.find_element(By.XPATH, xpath_value)
    book_btn.click()

    # time.sleep(1)
    driver.implicitly_wait(10)

    # 填寫會議名稱
    input_box = driver.find_element(By.ID, 'subject')
    input_box.clear()
    input_box.send_keys(meeting_subject)

    # 設置開始時間
    time_from = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'mrm101w3_appointmentTime_timeFrom'))
    )
    driver.execute_script(f'arguments[0].value = "{time_from_value}";', time_from)

    # 設置結束時間
    time_to = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, 'mrm101w3_appointmentTime_timeTo'))
    )
    driver.execute_script(f'arguments[0].value = "{time_to_value}";', time_to)

    # time.sleep(1)
    driver.implicitly_wait(10)

    # 填寫人數
    attendance = driver.find_element(By.ID, 'attendance')
    attendance.send_keys(attendance_number)

    # 下一步
    next_step = driver.find_element(By.ID, 'getBookRoomStatus')
    next_step.click()

    # time.sleep(4)
    driver.implicitly_wait(10)

    # 最終提交
    go_book = driver.find_element(By.ID, 'goBooking')
    go_book.click()

    time.sleep(15)
    # driver.implicitly_wait(10)
    driver.quit()

    return jsonify({'status': 'success', 'message': 'Meeting room booked successfully!'})

# 新增 API 端點：取得可用的建築物列表
@app.route('/buildings', methods=['GET'])
def get_buildings():
    """返回所有可用的建築物列表"""
    default_buildings = ['6']  # A3置地廣場
    return jsonify({
        'buildings': BUILDING_CONFIG,
        'default_buildings': default_buildings,
        'message': '可用的建築物列表'
    })

# 啟動 Flask 應用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
