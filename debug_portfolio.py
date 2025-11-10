#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试持仓监控问题
"""
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / 'modules'))

from Ashare import get_realtime_quotes_sina

# 模拟持仓监控中的实际调用
print("=" * 60)
print("调试持仓监控问题")
print("=" * 60)

# 测试1：传入纯数字代码（这是持仓监控中实际保存的格式）
print("\n测试1: 传入纯数字代码（模拟实际场景）")
stock_codes = ['000001', '600519']
print(f"输入代码: {stock_codes}")

quotes = get_realtime_quotes_sina(stock_codes)
print(f"返回结果: {quotes}")
print(f"是否为空: {not quotes}")

# 测试2：传入带前缀的代码
print("\n测试2: 传入带前缀的代码")
stock_codes_with_prefix = ['sz000001', 'sh600519']
print(f"输入代码: {stock_codes_with_prefix}")

quotes2 = get_realtime_quotes_sina(stock_codes_with_prefix)
print(f"返回结果: {quotes2}")
print(f"是否为空: {not quotes2}")

print("\n" + "=" * 60)
print("结论:")
if not quotes and quotes2:
    print("❌ 问题确认：纯数字代码无法获取数据")
    print("✅ 解决方案：需要在调用前将代码格式化为带前缀格式")
elif quotes:
    print("✅ 纯数字代码可以正常工作")
else:
    print("❌ 两种格式都无法获取数据，可能是网络或接口问题")
print("=" * 60)
