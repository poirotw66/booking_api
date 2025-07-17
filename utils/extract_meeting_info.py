#!/usr/bin/env python3
"""
會議室預訂資訊提取工具

從HTML文件中提取會議室名稱和預訂資訊
"""

import re
import sys
import os
from typing import List, Tuple


def extract_meeting_info(html_content: str) -> List[List[str]]:
    """
    從HTML內容中提取會議室預訂資訊
    
    Args:
        html_content (str): HTML檔案內容
        
    Returns:
        List[List[str]]: 會議室預訂資訊列表，每個元素包含 [會議室名稱, 時間, 會議名稱, 主辦方]
    """
    results = []
    
    # 首先從HTML中提取查詢日期
    date_pattern = r'value="(20\d{2}/\d{2}/\d{2})"'
    date_match = re.search(date_pattern, html_content)
    query_date = date_match.group(1) if date_match else "2025/07/18"  # 預設值
    
    # 找到所有會議室標題區域
    room_pattern = r'<div class="Title ToggleTitle"[^>]*>.*?<div class="Room">([^<]+)</div>'
    room_matches = re.finditer(room_pattern, html_content, re.DOTALL)
    
    # 找到所有會議按鈕（這是實際的會議記錄，不是重複的彈出窗口）
    button_pattern = r'<button[^>]+class="[^"]*Calendar_block[^"]*meetingRecordBtn[^"]*"[^>]*>(.*?)</button>'
    button_matches = re.finditer(button_pattern, html_content, re.DOTALL)
    
    # 提取會議室資訊
    rooms = {}
    for room_match in room_matches:
        room_name = room_match.group(1).strip()
        room_position = room_match.start()
        rooms[room_position] = room_name
    
    # 排序會議室位置
    sorted_room_positions = sorted(rooms.keys())
    
    # 處理每個會議按鈕
    for button_match in button_matches:
        button_content = button_match.group(1)
        button_position = button_match.start()
        
        # 找到這個按鈕屬於哪個會議室（最近的前一個會議室）
        room_name = None
        for i in range(len(sorted_room_positions) - 1, -1, -1):
            if sorted_room_positions[i] < button_position:
                room_name = rooms[sorted_room_positions[i]]
                break
        
        if not room_name:
            continue
            
        # 從按鈕內容中提取會議資訊
        meeting_name_match = re.search(r'<div class="Company textDis">([^<]+)</div>', button_content)
        if not meeting_name_match:
            # 嘗試帶空格的版本
            meeting_name_match = re.search(r'<div class="Company text\s*Dis">([^<]+)</div>', button_content)
        if not meeting_name_match:
            continue
            
        meeting_name = meeting_name_match.group(1).strip()
        
        # 提取部門資訊
        department_match = re.search(r'<div class="Department">([^<]+)</div>', button_content)
        department = department_match.group(1).strip() if department_match else ''
        
        # 提取人員資訊
        section_match = re.search(r'<div class="Section">([^<]+?)(?:\s*<span[^>]*>[^<]*</span>)?</div>', button_content)
        person = section_match.group(1).strip() if section_match else ''
        
        # 從按鈕屬性中提取時間資訊
        button_tag = button_match.group(0)
        start_time_match = re.search(r'data-starttime="([^"]+)"', button_tag)
        end_time_match = re.search(r'data-endtime="([^"]+)"', button_tag)
        
        if start_time_match and end_time_match:
            start_time = start_time_match.group(1)
            end_time = end_time_match.group(1)
            time_info = f"{query_date} {start_time}~{end_time}"
        else:
            continue
            
        # 組合主辦方資訊
        organizer = f"{department} {person}".strip() if department or person else ''
        
        results.append([room_name, time_info, meeting_name, organizer])
    
    return results


def process_html_file(html_file_path: str, output_file_path: str = None) -> List[List[str]]:
    """
    處理單個HTML檔案並提取會議室資訊
    
    Args:
        html_file_path (str): HTML檔案路徑
        output_file_path (str, optional): 輸出檔案路徑，如果不指定則不寫入檔案
        
    Returns:
        List[List[str]]: 會議室預訂資訊列表
    """
    try:
        # 讀取HTML文件
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 提取資訊
        meetings = extract_meeting_info(html_content)
        
        # 如果指定了輸出檔案路徑，則寫入檔案
        if output_file_path:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                for meeting in meetings:
                    f.write('\t'.join(meeting) + '\n')
            print(f"處理完成。輸出檔案：{output_file_path}")
            print(f"提取的會議室預訂記錄：{len(meetings)} 筆")
        
        return meetings
        
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {html_file_path}")
        return []
    except Exception as e:
        print(f"處理檔案 {html_file_path} 時發生錯誤：{e}")
        return []


def process_multiple_files(html_files: List[str]) -> List[List[str]]:
    """
    處理多個HTML檔案
    
    Args:
        html_files (List[str]): HTML檔案路徑列表
        
    Returns:
        List[List[str]]: 所有檔案的會議室預訂資訊列表
    """
    all_meetings = []
    
    for html_file in html_files:
        if not os.path.exists(html_file):
            print(f"警告：檔案不存在 {html_file}")
            continue
            
        # 生成對應的輸出檔案路徑（移除.html擴展名）
        output_file = html_file[:-5] if html_file.endswith('.html') else html_file + '_processed'
        
        meetings = process_html_file(html_file, output_file)
        all_meetings.extend(meetings)
    
    return all_meetings


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("使用方法：python3 extract_meeting_info.py file1.html [file2.html ...]")
        print("範例：python3 extract_meeting_info.py tmp/6_20250718_afternoon.html")
        sys.exit(1)
    
    html_files = sys.argv[1:]
    
    # 檢查所有檔案是否存在
    for html_file in html_files:
        if not os.path.exists(html_file):
            print(f"錯誤：檔案不存在 {html_file}")
            sys.exit(1)
    
    print(f"開始處理 {len(html_files)} 個HTML檔案...")
    
    # 處理所有檔案
    total_meetings = 0
    for html_file in html_files:
        print(f"\n處理檔案：{html_file}")
        
        # 生成對應的輸出檔案路徑
        output_file = html_file[:-5] if html_file.endswith('.html') else html_file + '_processed'
        
        meetings = process_html_file(html_file, output_file)
        total_meetings += len(meetings)
    
    print(f"\n總結：成功處理 {len(html_files)} 個檔案，提取 {total_meetings} 筆會議室預訂記錄")


if __name__ == '__main__':
    main()
