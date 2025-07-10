#!/bin/bash

# 檔案列表檔
if [ "$#" -lt 1 ]; then
  echo "請提供至少一個檔案，例如：./your_script.sh file1.html file2.html"
  exit 1
fi

# 逐行讀取檔案列表
for file in "$@"
do
  # 處理每個檔案
  cat "$file" | \
  awk '/meetingRoomRecordPk/ {exit} {print}' | \
  grep -E "會議室<|刪除會議室預約" -A 9 | \
  sed -n '/會議室</p; /2025/,+3p' | \
  sed -e 's|<div class="Room">|<li>|g' -e 's|</li>||g' -e 's|</div>||g' | \
  grep -v "為達公平使用會議資源" | \
  awk '{ gsub(/^[ \t]+/, ""); print }' | \
  sed 's/<li>//g' | \
  grep -v -- '^--$' > "${file%.html}"
done

echo "處理完成。"
