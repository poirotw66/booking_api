from collections import defaultdict
import csv
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        return file.readlines()

def process_files(file_list):
    meeting_data = defaultdict(list)
    current_room = None
    
    # 處理每個檔案
    for file_path in file_list:
        lines = read_file(file_path)
        for line in lines:
            line = line.strip()
            if "會議室" in line:
                current_room = line
            elif current_room:
                # 將會議記錄加到對應的會議室
                meeting_data[current_room].append(line)
    
    return meeting_data

def write_output(meeting_data, output_file):
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        for room, details in meeting_data.items():
            f.write(room + '\n')
            f.write('\n'.join(details) + '\n')
def write_output_csv(meeting_data, csv_filename):
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        # print('meeting_data:', meeting_data)
        fieldnames = ['會議室', '會議時間', '會議名稱', '借用人']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for room, meeting_info in meeting_data.items():
            for i in range(0, len(meeting_info), 3):
                row = {'會議室': room, '會議時間': meeting_info[i], '會議名稱': meeting_info[i + 1], '借用人': meeting_info[i + 2]}
                writer.writerow(row)
            # writer.writerow({'會議室', '時間', '會議名稱', '借用人'})
            
            # print(room + '\n')
            # print("details:", '\n'.join(details) + '\n')

# # 主程式邏輯
# file_list = ['2_page_source_afternoon', '1_page_source_morning']  # 你的兩個檔案
# output_file = 'combined_output.txt'  # 輸出檔案
# output_csv = 'combined.csv'
# meeting_data = process_files(sorted(file_list))
# write_output(meeting_data, output_file)
# write_output_csv(meeting_data, output_csv)
# print(f"檔案已合併並輸出至 {output_file}")
