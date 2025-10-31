#!/usr/bin/env python3
"""
清理重复和异常的股票数据文件
"""
import os
from pathlib import Path
from collections import defaultdict

def clean_duplicate_files():
    """清理重复和异常的股票数据文件"""
    data_dir = Path.home() / "stock_data"
    
    if not data_dir.exists():
        print("❌ 数据目录不存在")
        return
    
    # 统计所有CSV文件
    csv_files = list(data_dir.glob("*.csv"))
    print(f"📂 发现 {len(csv_files)} 个CSV文件")
    
    # 按股票代码分组 (提取前6位数字)
    stock_groups = defaultdict(list)
    
    for csv_file in csv_files:
        filename = csv_file.name
        # 提取股票代码 (前6位数字)
        stock_code = ''.join(filter(str.isdigit, filename.split('_')[0]))[:6]
        if stock_code:
            stock_groups[stock_code].append(csv_file)
    
    # 找出重复文件
    duplicate_count = 0
    deleted_count = 0
    
    for stock_code, files in stock_groups.items():
        if len(files) > 1:
            duplicate_count += 1
            print(f"\n🔍 股票代码 {stock_code} 有 {len(files)} 个文件:")
            
            # 按文件修改时间排序,保留最新的
            files_sorted = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 显示所有文件
            for i, f in enumerate(files_sorted):
                size_kb = f.stat().st_size / 1024
                mtime = f.stat().st_mtime
                status = "✅ 保留 (最新)" if i == 0 else "🗑️ 删除"
                print(f"  {status}: {f.name} ({size_kb:.1f} KB)")
            
            # 删除旧文件
            for f in files_sorted[1:]:
                try:
                    f.unlink()
                    deleted_count += 1
                    print(f"     已删除: {f.name}")
                except Exception as e:
                    print(f"     ⚠️ 删除失败: {e}")
    
    print(f"\n" + "="*60)
    print(f"✅ 清理完成!")
    print(f"📊 统计:")
    print(f"   - 总文件数: {len(csv_files)}")
    print(f"   - 重复股票数: {duplicate_count}")
    print(f"   - 已删除文件: {deleted_count}")
    print(f"   - 剩余文件数: {len(csv_files) - deleted_count}")
    print("="*60)

if __name__ == "__main__":
    clean_duplicate_files()

