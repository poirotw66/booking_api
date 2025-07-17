from collections import defaultdict
import csv
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        return file.readlines()

def process_files(file_list):
    meeting_data = defaultdict(list)
    
    # 處理每個檔案
    for file_path in file_list:
        lines = read_file(file_path)
        for line in lines:
            line = line.strip()
            if not line:  # 跳過空行
                continue
                
            # 處理TSV格式：會議室名稱\t時間\t會議名稱\t主辦方
            parts = line.split('\t')
            if len(parts) >= 4:
                room_name = parts[0].strip()
                time_info = parts[1].strip()
                meeting_name = parts[2].strip()
                organizer = parts[3].strip()
                
                # 將會議記錄加到對應的會議室，保持原有格式以兼容現有的write_output_csv函數
                meeting_data[room_name].extend([time_info, meeting_name, organizer])
            elif len(parts) >= 3:
                # 處理只有3個欄位的情況
                room_name = parts[0].strip()
                time_info = parts[1].strip()
                meeting_name = parts[2].strip()
                organizer = ""  # 空的主辦方
                
                meeting_data[room_name].extend([time_info, meeting_name, organizer])
    
    return meeting_data

def write_output(meeting_data, output_file):
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for room, details in meeting_data.items():
            f.write(room + '\n')
            f.write('\n'.join(details) + '\n')
def write_output_csv(meeting_data, csv_filename):
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['會議室', '會議時間', '會議名稱', '借用人']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for room, meeting_info in meeting_data.items():
            # 確保有足夠的資料來處理
            for i in range(0, len(meeting_info), 3):
                # 安全地取得每個欄位，如果不存在則使用空字串
                time_info = meeting_info[i] if i < len(meeting_info) else ''
                meeting_name = meeting_info[i + 1] if i + 1 < len(meeting_info) else ''
                organizer = meeting_info[i + 2] if i + 2 < len(meeting_info) else ''
                
                # 只有當至少有時間資訊時才寫入記錄
                if time_info:
                    row = {
                        '會議室': room,
                        '會議時間': time_info,
                        '會議名稱': meeting_name,
                        '借用人': organizer
                    }
                    writer.writerow(row)

# # 主程式邏輯
# file_list = ['2_page_source_afternoon', '1_page_source_morning']  # 你的兩個檔案
# output_file = 'combined_output.txt'  # 輸出檔案
# output_csv = 'combined.csv'
# meeting_data = process_files(sorted(file_list))
# write_output(meeting_data, output_file)
# write_output_csv(meeting_data, output_csv)
# print(f"檔案已合併並輸出至 {output_file}")
