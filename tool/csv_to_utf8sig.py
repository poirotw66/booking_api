#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV 編碼轉換工具
將 CSV 檔案從 UTF-8 編碼轉換為 UTF-8-SIG 編碼

使用方式:
1. 轉換單一檔案: python csv_to_utf8sig.py input.csv
2. 轉換目錄下所有 CSV: python csv_to_utf8sig.py directory/
3. 指定輸出檔案: python csv_to_utf8sig.py input.csv -o output.csv
4. 批次轉換並覆蓋原檔: python csv_to_utf8sig.py directory/ --overwrite
"""

import os
import sys
import argparse
import csv
from pathlib import Path


def convert_csv_to_utf8_sig(input_file, output_file=None, overwrite=False):
    """
    將 CSV 檔案從 UTF-8 轉換為 UTF-8-SIG 編碼
    
    Args:
        input_file (str): 輸入檔案路徑
        output_file (str): 輸出檔案路徑，若為 None 則自動生成
        overwrite (bool): 是否覆蓋原檔案
    
    Returns:
        bool: 轉換是否成功
    """
    try:
        input_path = Path(input_file)
        
        if not input_path.exists():
            print(f"❌ 檔案不存在: {input_file}")
            return False
            
        if not input_path.suffix.lower() == '.csv':
            print(f"⚠️ 跳過非 CSV 檔案: {input_file}")
            return False
        
        # 決定輸出檔案路徑
        if output_file:
            output_path = Path(output_file)
        elif overwrite:
            output_path = input_path
        else:
            # 自動生成輸出檔名 (加上 _utf8sig 後綴)
            output_path = input_path.parent / f"{input_path.stem}_utf8sig{input_path.suffix}"
        
        print(f"🔄 轉換中: {input_file} -> {output_path}")
        
        # 讀取原始檔案 (嘗試多種編碼)
        encodings_to_try = ['utf-8', 'utf-8-sig', 'big5', 'cp950', 'gb2312']
        content = None
        source_encoding = None
        
        for encoding in encodings_to_try:
            try:
                with open(input_path, 'r', encoding=encoding, newline='') as f:
                    content = list(csv.reader(f))
                    source_encoding = encoding
                    break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"❌ 讀取檔案時發生錯誤 (encoding: {encoding}): {e}")
                continue
        
        if content is None:
            print(f"❌ 無法讀取檔案 {input_file}，嘗試過的編碼: {encodings_to_try}")
            return False
        
        print(f"✅ 成功讀取檔案，原始編碼: {source_encoding}，共 {len(content)} 行")
        
        # 寫入新檔案，使用 UTF-8-SIG 編碼
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(content)
        
        print(f"✅ 轉換完成: {output_path}")
        
        # 顯示檔案大小資訊
        input_size = input_path.stat().st_size
        output_size = output_path.stat().st_size
        print(f"📊 檔案大小: {input_size:,} bytes -> {output_size:,} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 轉換檔案時發生錯誤: {e}")
        return False


def convert_directory(directory, overwrite=False):
    """
    轉換目錄下所有 CSV 檔案
    
    Args:
        directory (str): 目錄路徑
        overwrite (bool): 是否覆蓋原檔案
    
    Returns:
        tuple: (成功數量, 失敗數量)
    """
    dir_path = Path(directory)
    
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"❌ 目錄不存在: {directory}")
        return 0, 1
    
    csv_files = list(dir_path.glob("*.csv"))
    
    if not csv_files:
        print(f"⚠️ 目錄中沒有找到 CSV 檔案: {directory}")
        return 0, 0
    
    print(f"🔍 找到 {len(csv_files)} 個 CSV 檔案")
    
    success_count = 0
    fail_count = 0
    
    for csv_file in csv_files:
        print(f"\n--- 處理檔案 {success_count + fail_count + 1}/{len(csv_files)} ---")
        
        if convert_csv_to_utf8_sig(str(csv_file), overwrite=overwrite):
            success_count += 1
        else:
            fail_count += 1
    
    return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(
        description="CSV 編碼轉換工具 - 將 UTF-8 轉換為 UTF-8-SIG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python csv_to_utf8sig.py file.csv                    # 轉換單一檔案
  python csv_to_utf8sig.py file.csv -o new_file.csv   # 指定輸出檔案
  python csv_to_utf8sig.py ./data/                     # 轉換目錄下所有 CSV
  python csv_to_utf8sig.py ./data/ --overwrite         # 批次轉換並覆蓋原檔
        """
    )
    
    parser.add_argument(
        "input",
        help="輸入檔案路徑或目錄路徑"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="輸出檔案路徑 (僅適用於單一檔案轉換)"
    )
    
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆蓋原檔案 (危險操作，請謹慎使用)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模擬執行，不實際轉換檔案"
    )
    
    args = parser.parse_args()
    
    # 檢查輸入路徑
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ 路徑不存在: {args.input}")
        sys.exit(1)
    
    print("=" * 50)
    print("🔧 CSV 編碼轉換工具")
    print("📝 功能: UTF-8 -> UTF-8-SIG")
    print("=" * 50)
    
    if args.dry_run:
        print("🧪 模擬執行模式 (不會實際修改檔案)")
        return
    
    if args.overwrite:
        response = input("⚠️ 您選擇了覆蓋原檔案，此操作無法復原。確定要繼續嗎？ (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ 操作已取消")
            sys.exit(0)
    
    if input_path.is_file():
        # 處理單一檔案
        if args.output and Path(args.input).parent != Path(args.output).parent:
            # 確保輸出目錄存在
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        
        success = convert_csv_to_utf8_sig(
            args.input, 
            args.output, 
            args.overwrite
        )
        
        if success:
            print("\n🎉 轉換完成！")
        else:
            print("\n❌ 轉換失敗！")
            sys.exit(1)
            
    elif input_path.is_dir():
        # 處理目錄
        if args.output:
            print("⚠️ 目錄模式下忽略 --output 參數")
        
        success_count, fail_count = convert_directory(args.input, args.overwrite)
        
        print("\n" + "=" * 50)
        print("📊 轉換結果統計")
        print(f"✅ 成功: {success_count} 個檔案")
        print(f"❌ 失敗: {fail_count} 個檔案")
        print(f"📁 總計: {success_count + fail_count} 個檔案")
        print("=" * 50)
        
        if fail_count > 0:
            print("⚠️ 部分檔案轉換失敗，請檢查上方錯誤訊息")
            sys.exit(1)
        else:
            print("🎉 所有檔案轉換完成！")
    
    else:
        print(f"❌ 無效的路徑類型: {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()
