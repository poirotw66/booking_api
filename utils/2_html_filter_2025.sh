#!/bin/bash

# 檢查是否有提供檔案
if [ "$#" -lt 1 ]; then
  echo "請提供至少一個檔案，例如：./your_script.sh file1.html file2.html"
  exit 1
fi

for file in "$@"
do
  python3 -c "
import re
import sys
import csv

def extract_meeting_info(html_content):
    results = []
    
    # 分割HTML以找到每個會議室區域
    room_sections = re.split(r'<div class=\"Title ToggleTitle\"[^>]*>', html_content)
    
    for section in room_sections[1:]:  # 跳過第一個空的部分
        # 提取會議室名稱
        room_match = re.search(r'<div class=\"Room\">([^<]+)</div>', section)
        if not room_match:
            continue
        room_name = room_match.group(1).strip()
        
        # 查找這個區域內的所有預訂資訊
        text_areas = re.finditer(r'<div class=\"Text_area\"[^>]*>\s*<ul>(.*?)</ul>', section, re.DOTALL)
        
        for text_area in text_areas:
            ul_content = text_area.group(1)
            # 提取li內容
            li_matches = re.findall(r'<li>([^<]+)</li>', ul_content)
            
            # 檢查是否包含日期時間信息（第一個li通常是時間）
            if li_matches and len(li_matches) >= 1:
                first_li = li_matches[0].strip()
                # 檢查是否為日期時間格式
                if re.search(r'20\d{2}/\d{2}/\d{2}.*\d{2}:\d{2}', first_li):
                    # 確保有足夠的資訊
                    time_info = li_matches[0].strip() if len(li_matches) > 0 else ''
                    meeting_name = li_matches[1].strip() if len(li_matches) > 1 else ''
                    organizer = li_matches[2].strip() if len(li_matches) > 2 else ''
                    
                    # 清理欄位，移除多餘的空白和換行
                    organizer = re.sub(r'\s+', ' ', organizer)
                    meeting_name = re.sub(r'\s+', ' ', meeting_name)
                    
                    results.append([room_name, time_info, meeting_name, organizer])
    
    return results

# 讀取HTML文件
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    html_content = f.read()

# 提取資訊
meetings = extract_meeting_info(html_content)

# 輸出為TSV格式（Tab分隔）
for meeting in meetings:
    print('\t'.join(meeting))
" "$file" > "${file%.html}"
done

echo "處理完成。輸出檔案：${1%.html}"
echo "提取的會議室預訂記錄：$(wc -l < ${1%.html}) 筆"
