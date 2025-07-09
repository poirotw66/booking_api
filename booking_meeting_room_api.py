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
    '20': 'A3置地廣場',
    '22': '高雄資訊開發中心'
}

# API 路由：根據提供的登入資訊和日期，進行會議室查詢
@app.route('/run', methods=['POST'])
def run_booking():
    data = request.json

    username = os.getenv('BOOKING_USERNAME')
    password = os.getenv('BOOKING_PASSWORD')
    print(f"使用帳號: {username}")
    current_date = data.get('date', '2025/07/10')

    # 取得要查詢的建築物列表，如果沒有指定則使用預設值
    default_buildings = data.get('default_buildings', ['20'])  # A3置地廣場
    buildings = data.get('buildings', default_buildings)
    if isinstance(buildings, str):
        buildings = [buildings]  # 如果是單個字串，轉換為列表

    print(f"要查詢的建築物: {[BUILDING_CONFIG.get(b, f'未知建築物({b})') for b in buildings]}")

    if not username or not password:
        return jsonify({'error': '環境變數中缺少帳號或密碼'}), 500
    
    # Selenium 驅動程式設置
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')
    # 登入
    # time.sleep(2)
    driver.implicitly_wait(10)
    email = driver.find_element(By.NAME, 'username')
    email.send_keys(username)
    password_field = driver.find_element(By.ID, 'KEY')
    password_field.send_keys(password)

    # 點擊登入按鈕
    login_button = driver.find_element(By.ID, 'btnLogin')
    login_button.click()
    
    # 等待登入完成並檢查是否成功
    try:
        # 等待頁面元素出現，確認登入成功
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, 'startDate'))
        )
        time.sleep(1)  # 額外等待確保頁面完全載入
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
        building_name = BUILDING_CONFIG.get(building_id, f'未知建築物({building_id})')
        print(f"正在查詢建築物: {building_name} (ID: {building_id})")

        # 選擇建築物
        dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
        select = Select(dropdown)
        select.select_by_value(building_id)

        # 等待頁面載入時段選擇按鈕
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//button[@name="selectedTimePeriod"]'))
            )
            time.sleep(1)  # 確保所有按鈕都載入完成
        except Exception as e:
            print(f"等待時段按鈕載入失敗 - {building_name}: {e}")
            continue  # 跳過這個建築物，繼續下一個

        # 下載早上與下午的數據
        building_morning_data = None
        building_afternoon_data = None

        try:
            # 使用 WebDriverWait 明確等待元素出現
            morning_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@name="selectedTimePeriod" and @value="MORNING"]'))
            )
            morning_btn.click()
            driver.implicitly_wait(10)
            time.sleep(1)  # 等待頁面更新
            page_source = driver.page_source
            print(f"早上頁面內容長度：{len(page_source)} 字符 - {building_name}")
            print(f"頁面是否包含會議室關鍵字：{'會議室' in page_source}")
            print(f"頁面是否包含時間表：{'timeTable' in page_source}")
            building_morning_data = page_source
        except Exception as e:
            print(f"找不到早上時段按鈕 - {building_name}: {e}")
            # 嘗試其他可能的選擇器
            try:
                morning_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@value, "MORNING")]'))
                )
                morning_btn.click()
                driver.implicitly_wait(10)
                time.sleep(1)
                page_source = driver.page_source
                building_morning_data = page_source
            except Exception as e2:
                print(f"使用備用選擇器也失敗 - {building_name}: {e2}")
                continue  # 跳過這個建築物，繼續下一個

        morning_file_name = f'./tmp/{building_id}_{current_date.replace("/", "")}_morning.html'
        if building_morning_data:
            with open(morning_file_name, 'w', encoding='utf-8-sig') as f:
                f.write(building_morning_data)

        # 處理下午時段
        try:
            afternoon_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@name="selectedTimePeriod" and @value="AFTERNOON"]'))
            )
            afternoon_btn.click()
            driver.implicitly_wait(10)
            time.sleep(1)  # 等待頁面更新
            page_source = driver.page_source
            print(f"下午頁面內容長度：{len(page_source)} 字符 - {building_name}")
            print(f"頁面是否包含會議室關鍵字：{'會議室' in page_source}")
            print(f"頁面是否包含時間表：{'timeTable' in page_source}")
            building_afternoon_data = page_source
        except Exception as e:
            print(f"找不到下午時段按鈕 - {building_name}: {e}")
            # 嘗試其他可能的選擇器
            try:
                afternoon_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@value, "AFTERNOON")]'))
                )
                afternoon_btn.click()
                driver.implicitly_wait(10)
                time.sleep(1)
                page_source = driver.page_source
                building_afternoon_data = page_source
            except Exception as e2:
                print(f"使用備用選擇器也失敗 - {building_name}: {e2}")
                continue  # 跳過這個建築物，繼續下一個

        afternoon_file_name = f'./tmp/{building_id}_{current_date.replace("/", "")}_afternoon.html'
        if building_afternoon_data:
            with open(afternoon_file_name, 'w', encoding='utf-8-sig') as f:
                f.write(building_afternoon_data)

        # 儲存這個建築物的檔案資訊
        if building_morning_data and building_afternoon_data:
            all_building_data.append({
                'building_id': building_id,
                'building_name': building_name,
                'morning_file': morning_file_name,
                'afternoon_file': afternoon_file_name
            })
            print(f"成功收集建築物 {building_name} 的數據")
        else:
            print(f"建築物 {building_name} 數據收集不完整，跳過")

    driver.quit()

    # 檢查是否有成功收集到數據
    if not all_building_data:
        return jsonify({'error': '沒有成功收集到任何建築物的數據'}), 500

    print(f"成功收集到 {len(all_building_data)} 個建築物的數據")

    # 處理所有建築物的檔案
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
        result = subprocess.run(['sh', 'utils/2_html_filter.sh', morning_file, afternoon_file], capture_output=True, text=True)
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
    building_id = data.get('building_id', '20')
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
    xpath_value = meeting_room_xpath.get(room_number)
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
