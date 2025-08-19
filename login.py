from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()

username = os.getenv('BOOKING_USERNAME')
password = os.getenv('BOOKING_PASSWORD')

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
# Chrome 瀏覽器路徑 (macOS)
options.binary_location = "/usr/bin/google-chrome"
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
    exit(1)
    
driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')

driver.implicitly_wait(3)  # 減少隱式等待時間
email = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.NAME, 'username'))
)
email.send_keys(username)
password_field = driver.find_element(By.ID, 'KEY')
password_field.send_keys(password)
login_button = driver.find_element(By.ID, 'btnLogin')
login_button.click()
