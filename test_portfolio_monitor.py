#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试持仓监控模块的新功能
"""
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / 'aitrader_core' / 'datafeed'))
sys.path.insert(0, str(Path(__file__).parent / 'modules'))

from Ashare import get_stock_name, get_realtime_quotes_sina

def test_get_stock_name():
    """测试获取股票名称"""
    print("=" * 60)
    print("测试1: 获取股票名称")
    print("=" * 60)
    
    test_codes = ['000001', '600519', '300750', 'sh000001', '600519.XSHG']
    
    for code in test_codes:
        name = get_stock_name(code)
        print(f"{code:15s} -> {name}")
    
    print()

def test_realtime_quotes():
    """测试获取实时行情"""
    print("=" * 60)
    print("测试2: 获取实时行情")
    print("=" * 60)
    
    # 需要格式化代码
    test_codes = ['sz000001', 'sh600519', 'sz300750']
    quotes = get_realtime_quotes_sina(test_codes)
    
    for code, data in quotes.items():
        print(f"\n{code}: {data['name']}")
        print(f"  当前价: {data['current_price']:.2f}")
        print(f"  涨跌额: {data['change']:+.2f}")
        print(f"  涨跌幅: {data['change_pct']:+.2f}%")
        print(f"  开盘价: {data['open']:.2f}")
        print(f"  最高价: {data['high']:.2f}")
        print(f"  最低价: {data['low']:.2f}")
        print(f"  成交量: {data['volume']:.0f}")
        print(f"  时间: {data['time']}")
    
    print()

def test_batch_quotes():
    """测试批量获取行情"""
    print("=" * 60)
    print("测试3: 批量获取行情（模拟持仓监控）")
    print("=" * 60)
    
    # 模拟持仓列表（纯数字代码）
    portfolio_codes = ['000001', '600519', '300750', '000858', '601318']
    
    print(f"持仓股票数量: {len(portfolio_codes)}")
    print(f"股票代码: {', '.join(portfolio_codes)}")
    print()
    
    # 格式化代码（添加市场前缀）
    formatted_codes = []
    for code in portfolio_codes:
        if code.startswith('6'):
            formatted_codes.append('sh' + code)
        elif code.startswith('0') or code.startswith('3'):
            formatted_codes.append('sz' + code)
        else:
            formatted_codes.append(code)
    
    quotes = get_realtime_quotes_sina(formatted_codes)
    
    print(f"{'代码':<10} {'名称':<10} {'当前价':>10} {'涨跌幅':>10} {'成交量':>15}")
    print("-" * 60)
    
    for i, code in enumerate(portfolio_codes):
        # 使用格式化后的代码
        xcode = formatted_codes[i]
        
        if xcode in quotes:
            data = quotes[xcode]
            print(f"{code:<10} {data['name']:<10} {data['current_price']:>10.2f} {data['change_pct']:>9.2f}% {data['volume']:>15.0f}")
        else:
            print(f"{code:<10} {'获取失败':<10}")
    
    print()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("持仓监控模块功能测试")
    print("=" * 60)
    print()
    
    try:
        test_get_stock_name()
        test_realtime_quotes()
        test_batch_quotes()
        
        print("=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
