from selenium import webdriver
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
driver = webdriver.Chrome(options=options)
driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')\

driver.implicitly_wait(5)  # 減少隱式等待時間
email = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.NAME, 'username'))
)
email.send_keys(username)
password_field = driver.find_element(By.ID, 'KEY')
password_field.send_keys(password)
login_button = driver.find_element(By.ID, 'btnLogin')
login_button.click()