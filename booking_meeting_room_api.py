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

app = Flask(__name__)

# API 路由：根據提供的登入資訊和日期，進行會議室查詢
@app.route('/run', methods=['POST'])
def run_booking():
    data = request.json
    
    username = 'XXXXXXXX'
    password = 'XXXXXXXXX'
    current_date = data.get('date', '2024/09/20')

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
    # time.sleep(5)
    driver.implicitly_wait(10)

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

    # 選擇建築物
    dropdown = driver.find_element(By.ID, 'searchBeanBuildingPK')
    select = Select(dropdown)
    select.select_by_value('20')

    driver.implicitly_wait(10)
    time.sleep(1)
    # 下載早上與下午的數據
    morning_btn = driver.find_element(By.XPATH, '//button[@name="selectedTimePeriod" and @value="MORNING"]')
    morning_btn.click()
    driver.implicitly_wait(10)
    page_source = driver.page_source
    morning_file_name = f'./tmp/1_{current_date.replace("/", "")}_morning.html'
    with open(morning_file_name, 'w', encoding='utf-8') as f:
        f.write(page_source)
    driver.implicitly_wait(10)
    time.sleep(1)
    afternoon_btn = driver.find_element(By.XPATH, '//button[@name="selectedTimePeriod" and @value="AFTERNOON"]')
    afternoon_btn.click()
    driver.implicitly_wait(10)
    page_source = driver.page_source
    afternoon_file_name = f'./tmp/2_{current_date.replace("/", "")}_afternoon.html'
    with open(afternoon_file_name, 'w', encoding='utf-8') as f:
        f.write(page_source)

    driver.quit()

    # 執行Shell腳本進行文件處理
    result = subprocess.run(['sh', 'utils/2_html_filter.sh', morning_file_name, afternoon_file_name], capture_output=True, text=True)
    print(result)

    # 合併並生成最終輸出文件
    file_list = [morning_file_name[:-5], afternoon_file_name[:-5]]  # 兩個檔案
    output_file = f'./output/{current_date.replace("/", "")}_combined_output.txt'  # 輸出檔案
    output_csv = f'./output/{current_date.replace("/", "")}_combined.csv'
    meeting_data = process_files(sorted(file_list))
    write_output(meeting_data, output_file)
    write_output_csv(meeting_data, output_csv)
    with open(output_csv, 'r', encoding='utf-8') as csv_file:
        csv_content = csv_file.read()
    os.remove(morning_file_name)
    os.remove(afternoon_file_name)
    # os.remove(output_csv)
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

    # 啟動 Chrome driver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    
    # 打開頁面
    driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')

    # time.sleep(2)
    driver.implicitly_wait(10)

    # 登錄過程
    email = driver.find_element(By.NAME, 'username')
    email.send_keys('00896102')
    password_field = driver.find_element(By.ID, 'KEY')
    password_field.send_keys('Cxzasdf5')

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
    select.select_by_value('20')

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

# 啟動 Flask 應用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
