"""
测试持仓监控功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.portfolio_monitor import (
    add_stock_to_portfolio,
    remove_stock_from_portfolio,
    load_portfolio,
    get_realtime_quotes
)
from datetime import datetime

def test_portfolio_functions():
    """测试持仓监控功能"""
    print("="*60)
    print("持仓监控功能测试")
    print("="*60)

    # 1. 测试添加股票
    print("\n1. 测试添加股票到持仓")
    add_stock_to_portfolio("000001", "平安银行", 11.5, 1000, datetime.now())
    add_stock_to_portfolio("600519", "贵州茅台", 1650.0, 100, datetime.now())
    add_stock_to_portfolio("000858", "五粮液", 135.0, 500, datetime.now())

    # 2. 测试加载持仓
    print("\n2. 测试加载持仓数据")
    portfolio = load_portfolio()
    print(f"   持仓股票数量: {len(portfolio)}")
    for code, info in portfolio.items():
        print(f"   - {info['name']}({code}): 成本价{info.get('buy_price', 'N/A')}, 数量{info.get('quantity', 'N/A')}")

    # 3. 测试获取实时行情
    print("\n3. 测试获取实时行情")
    stock_codes = list(portfolio.keys())
    quotes_df = get_realtime_quotes(stock_codes)

    if quotes_df is not None and not quotes_df.empty:
        print("   实时行情获取成功:")
        for _, row in quotes_df.iterrows():
            print(f"   - {row['code']}: 当前价{row['current_price']:.2f}, 涨跌幅{row['change_pct']:+.2f}%")
    else:
        print("   ⚠️ 实时行情获取失败")

    # 4. 清理测试数据
    print("\n4. 清理测试数据")
    for code in stock_codes:
        remove_stock_from_portfolio(code)

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    test_portfolio_functions()
