from flask import Flask, request, jsonify, Response
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import subprocess
from utils.convert_to_csv import process_files, write_output, write_output_csv
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
    
    # Selenium 驅動程式設置
    selenium_start_time = time.time()
    print(f"🚀 啟動瀏覽器 - {time.strftime('%H:%M:%S', time.localtime(selenium_start_time))}")
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')
    # 登入
    driver.implicitly_wait(5)  # 減少隱式等待時間
    
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
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'startDate'))
        )
        time.sleep(1)  # 額外等待確保頁面完全載入
        login_end_time = time.time()
        print(f"✅ 登入成功 - 耗時 {login_end_time - login_start_time:.2f} 秒")
    except Exception as e:
        print(f"登入可能失敗或頁面載入超時: {e}")
        driver.quit()
        return jsonify({'error': '登入失敗或頁面載入超時'}), 500

    # 選擇開始日期和結束日期
    start_date_input = driver.find_element(By.ID, 'startDate')
    end_date_input = driver.find_element(By.ID, 'endDate')

    driver.execute_script("""
        var input = arguments[0];
        input.value = arguments[1];
        var event = new Event('change', { bubbles: true });
        input.dispatchEvent(event);
    """, start_date_input, current_date)

    driver.execute_script("""
        var input = arguments[0];
        input.value = arguments[1];
        var event = new Event('change', { bubbles: true });
        input.dispatchEvent(event);
    """, end_date_input, current_date)

    # 儲存所有建築物的數據
    all_building_data = []

    # 遍歷每個建築物進行查詢
    for building_id in buildings:
        building_start_time = time.time()
        building_name = BUILDING_CONFIG.get(building_id, f'未知建築物({building_id})')
        print(f"🏢 正在查詢建築物: {building_name} (ID: {building_id}) - {time.strftime('%H:%M:%S', time.localtime(building_start_time))}")

        # 選擇建築物
        dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
        select = Select(dropdown)
        select.select_by_value(building_id)

        # 等待頁面載入時段選擇按鈕並直接點擊早上按鈕
        try:
            print(f"⏳ 等待並點擊早上時段按鈕 - {building_name}")
            # morning_btn = WebDriverWait(driver, 5).until(
            #     EC.element_to_be_clickable((By.XPATH, '//button[@name="selectedTimePeriod" and @value="MORNING"]'))
            # )
            # morning_btn = WebDriverWait(driver, 5).until(
            #     EC.element_to_be_clickable((By.XPATH, '//button[contains(@value, "MORNING")]'))
            # )
            # morning_btn.click()
            driver.execute_script("""
                let btn = document.querySelector('button[name="selectedTimePeriod"][value="MORNING"]');
                btn.click();
            """)
            print(f"✅ 早上按鈕點擊成功 - {building_name}")
            
            # 等待頁面載入會議室數據
            time.sleep(0.5)
            page_source = driver.page_source
            print(f"早上頁面內容長度：{len(page_source)} 字符 - {building_name}")
            print(f"頁面是否包含會議室關鍵字：{'會議室' in page_source}")
            print(f"頁面是否包含時間表：{'timeTable' in page_source}")
            building_morning_data = page_source
        except Exception as e:
            print(f"找不到早上時段按鈕 - {building_name}: {e}")
            # 嘗試其他可能的選擇器
            try:
                print(f"🔄 嘗試備用選擇器 - {building_name}")
                morning_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@value, "MORNING")]'))
                )
                morning_btn.click()
                time.sleep(0.5)
                page_source = driver.page_source
                building_morning_data = page_source
                print(f"✅ 備用選擇器成功 - {building_name}")
            except Exception as e2:
                print(f"使用備用選擇器也失敗 - {building_name}: {e2}")
                continue  # 跳過這個建築物，繼續下一個

        morning_file_name = f'./tmp/{building_id}_{current_date.replace("/", "")}_morning.html'
        if building_morning_data:
            with open(morning_file_name, 'w', encoding='utf-8-sig') as f:
                f.write(building_morning_data)
        # 處理下午時段 - 同樣優化
        try:
            print(f"⏳ 等待並點擊下午時段按鈕 - {building_name}")
            # afternoon_btn = WebDriverWait(driver, 5).until(
            #     EC.element_to_be_clickable((By.XPATH, '//button[@name="selectedTimePeriod" and @value="AFTERNOON"]'))
            # )
            # afternoon_btn.click()
            driver.execute_script("""
                let btn = document.querySelector('button[name="selectedTimePeriod"][value="AFTERNOON"]');
                btn.click();
            """)
            print(f"✅ 下午按鈕點擊成功 - {building_name}")
            
            time.sleep(0.5)
            page_source = driver.page_source
            print(f"下午頁面內容長度：{len(page_source)} 字符 - {building_name}")
            print(f"頁面是否包含會議室關鍵字：{'會議室' in page_source}")
            print(f"頁面是否包含時間表：{'timeTable' in page_source}")
            building_afternoon_data = page_source
        except Exception as e:
            print(f"找不到下午時段按鈕 - {building_name}: {e}")
            # 嘗試其他可能的選擇器
            try:
                print(f"🔄 嘗試備用選擇器 - {building_name}")
                afternoon_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@value, "AFTERNOON")]'))
                )
                afternoon_btn.click()
                time.sleep(0.5)
                page_source = driver.page_source
                building_afternoon_data = page_source
                print(f"✅ 備用選擇器成功 - {building_name}")
            except Exception as e2:
                print(f"使用備用選擇器也失敗 - {building_name}: {e2}")
                continue  # 跳過這個建築物，繼續下一個

        afternoon_file_name = f'./tmp/{building_id}_{current_date.replace("/", "")}_afternoon.html'
        if building_afternoon_data:
            with open(afternoon_file_name, 'w', encoding='utf-8-sig') as f:
                f.write(building_afternoon_data)

        # 儲存這個建築物的檔案資訊
        if building_morning_data and building_afternoon_data:
            building_end_time = time.time()
            all_building_data.append({
                'building_id': building_id,
                'building_name': building_name,
                'morning_file': morning_file_name,
                'afternoon_file': afternoon_file_name
            })
            print(f"✅ 成功收集建築物 {building_name} 的數據 - 耗時 {building_end_time - building_start_time:.2f} 秒")
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

    # 處理所有建築物的檔案
    processing_start_time = time.time()
    print(f"⚙️ 開始處理檔案 - {time.strftime('%H:%M:%S', time.localtime(processing_start_time))}")
    
    all_file_list = []
    for building_data in all_building_data:
        morning_file = building_data['morning_file']
        afternoon_file = building_data['afternoon_file']
        building_name = building_data['building_name']

        # 檢查檔案是否成功儲存
        if not os.path.exists(morning_file):
            print(f"警告：{building_name} 早上HTML檔案不存在：{morning_file}")
            continue
        if not os.path.exists(afternoon_file):
            print(f"警告：{building_name} 下午HTML檔案不存在：{afternoon_file}")
            continue

        print(f"HTML檔案儲存成功 - {building_name}：{morning_file}, {afternoon_file}")
        print(f"早上檔案大小：{os.path.getsize(morning_file)} bytes")
        print(f"下午檔案大小：{os.path.getsize(afternoon_file)} bytes")

        # 執行Shell腳本進行文件處理
        if current_date[:4] == "2024":
            result = subprocess.run(['sh', 'utils/2_html_filter_2024.sh', morning_file, afternoon_file], capture_output=True, text=True)
        else:
            result = subprocess.run(['sh', 'utils/2_html_filter_2025.sh', morning_file, afternoon_file], capture_output=True, text=True)
        print(f"Shell腳本執行結果 - {building_name}：")
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        print("return code:", result.returncode)

        # 添加處理後的檔案到列表
        processed_morning = morning_file[:-5]  # 移除 .html 擴展名
        processed_afternoon = afternoon_file[:-5]
        all_file_list.extend([processed_morning, processed_afternoon])

    if not all_file_list:
        return jsonify({'error': '沒有成功處理任何檔案'}), 500

    # 合併並生成最終輸出文件
    buildings_str = '_'.join([data['building_id'] for data in all_building_data])
    output_file = f'./output/{current_date.replace("/", "")}_buildings_{buildings_str}_combined_output.txt'
    output_csv = f'./output/{current_date.replace("/", "")}_buildings_{buildings_str}_combined.csv'

    print(f"處理檔案列表：{all_file_list}")

    # 檢查處理後的檔案是否存在
    for file_path in all_file_list:
        if os.path.exists(file_path):
            print(f"處理後檔案存在：{file_path}, 大小：{os.path.getsize(file_path)} bytes")
            # 顯示檔案前幾行內容
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()[:10]
                print(f"{file_path} 前10行內容：")
                for i, line in enumerate(lines, 1):
                    print(f"  {i}: {line.strip()}")
        else:
            print(f"處理後檔案不存在：{file_path}")

    meeting_data = process_files(sorted(all_file_list))
    print(f"處理後的會議數據：{meeting_data}")

    write_output(meeting_data, output_file)
    write_output_csv(meeting_data, output_csv)
    
    # 計算總執行時間
    end_time = time.time()
    total_time = end_time - start_time
    processing_time = end_time - processing_start_time
    
    print(f"📝 檔案處理完成 - 耗時 {processing_time:.2f} 秒")
    print(f"🏁 總執行時間: {total_time:.2f} 秒")
    print(f"📈 平均每個建築物耗時: {total_time / len(all_building_data):.2f} 秒")
    
    with open(output_csv, 'r', encoding='utf-8-sig') as csv_file:
        csv_content = csv_file.read()

    # 暫時不刪除檔案，方便調試
    debug_files = []
    for building_data in all_building_data:
        debug_files.extend([building_data['morning_file'], building_data['afternoon_file']])
    print(f"保留調試檔案：{debug_files}")
    print(f"輸出CSV檔案：{output_csv}")

    # 返回處理結果
    return Response(csv_content, mimetype='text/csv')

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
    '4F-安新芽': '//*[@id="timeTableMeetingRoom"]/div[48]/button[1]',
    '4F-微風Chill室': '//*[@id="timeTableMeetingRoom"]/div[50]/button[1]',
    '4F-滴大地': '//*[@id="timeTableMeetingRoom"]/div[52]/button[1]',
    '4F-光影綠谷': '//*[@id="timeTableMeetingRoom"]/div[54]/button[1]',
    '4F-剛果秘境': '//*[@id="timeTableMeetingRoom"]/div[56]/button[1]',
    '4F-未來綠洲': '//*[@id="timeTableMeetingRoom"]/div[58]/button[1]',
    '4F-森林之光': '//*[@id="timeTableMeetingRoom"]/div[60]/button[1]',
    '4F-優勝美地': '//*[@id="timeTableMeetingRoom"]/div[62]/button[1]',
    '4F-亞馬遜雨林': '//*[@id="timeTableMeetingRoom"]/div[64]/button[1]',
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
    attendance_number = '4'
    time_from_value = data.get('time_from', '08:00')
    time_to_value = data.get('time_to', '09:00')

    # 取得要預訂的建築物，如果沒有指定則使用預設值 (A3置地廣場)
    building_id = data.get('building_id', '6')
    building_name = BUILDING_CONFIG.get(building_id, f'未知建築物({building_id})')
    print(f"要預訂的建築物: {building_name} (ID: {building_id})")

    # 啟動 Chrome driver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    
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
