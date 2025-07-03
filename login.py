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

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)
driver.get('https://booking.cathayholdings.com/frontend/mrm101w/index?')
time.sleep(60)