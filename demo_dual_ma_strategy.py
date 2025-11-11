#!/usr/bin/env python3
"""
双均线策略演示代码
可直接复制到自定义策略编辑器中进行测试
"""

# 策略代码1：经典双均线策略
CLASSIC_DUAL_MA = '''
def initialize(context):
    """经典双均线策略
    短期均线上穿长期均线买入，下穿卖出
    """
    # 股票池：选择流动性好的大盘股
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600036.SH',  # 招商银行
        '600519.SH'   # 贵州茅台
    ]
    context.short_ma = 5   # 短期均线周期
    context.long_ma = 20   # 长期均线周期
    context.hold_count = 2 # 持仓数量

def handle_data(context):
    """策略逻辑"""
    # 买入信号：短期均线上穿长期均线（金叉）
    buy_signal = f"ma(close, {context.short_ma}) > ma(close, {context.long_ma})"
    
    # 卖出信号：短期均线下穿长期均线（死叉）
    sell_signal = f"ma(close, {context.short_ma}) < ma(close, {context.long_ma})"
    
    return {
        'select_buy': [buy_signal],
        'select_sell': [sell_signal],
        'order_by_signal': f'roc(close, {context.short_ma})',  # 按短期动量排序
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'  # 每日调仓
    }
'''

# 策略代码2：优化版双均线策略
OPTIMIZED_DUAL_MA = '''
def initialize(context):
    """优化版双均线策略
    增加RSI过滤器，避免在超买时买入
    """
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600036.SH',  # 招商银行
        '600000.SH'   # 浦发银行
    ]
    context.short_ma = 8
    context.long_ma = 21
    context.rsi_period = 14
    context.rsi_overbought = 70  # RSI超买阈值
    context.hold_count = 2

def handle_data(context):
    """优化策略逻辑"""
    # 买入条件：
    # 1. 均线金叉
    # 2. RSI未超买
    buy_conditions = [
        f"ma(close, {context.short_ma}) > ma(close, {context.long_ma})",
        f"rsi(close, {context.rsi_period}) < {context.rsi_overbought}"
    ]
    
    # 卖出条件：均线死叉
    sell_signal = f"ma(close, {context.short_ma}) < ma(close, {context.long_ma})"
    
    return {
        'select_buy': buy_conditions,
        'buy_at_least_count': 2,  # 两个买入条件都要满足
        'select_sell': [sell_signal],
        'order_by_signal': f'roc(close, {context.short_ma})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
'''

# 策略代码3：三均线趋势策略
TRIPLE_MA_TREND = '''
def initialize(context):
    """三均线趋势策略
    短、中、长三根均线，确认趋势后再入场
    """
    context.symbols = [
        '000001.SZ',  # 平安银行
        '600519.SH',  # 贵州茅台
        '000858.SZ',  # 五粮液
        '002415.SZ'   # 海康威视
    ]
    context.short_ma = 5   # 短期均线
    context.mid_ma = 20    # 中期均线
    context.long_ma = 60   # 长期均线
    context.hold_count = 2

def handle_data(context):
    """三均线策略逻辑"""
    # 买入条件：多头排列（短 > 中 > 长）
    buy_conditions = [
        f"ma(close, {context.short_ma}) > ma(close, {context.mid_ma})",
        f"ma(close, {context.mid_ma}) > ma(close, {context.long_ma})"
    ]
    
    # 卖出条件：空头排列（短 < 中 < 长）
    sell_conditions = [
        f"ma(close, {context.short_ma}) < ma(close, {context.mid_ma})",
        f"ma(close, {context.mid_ma}) < ma(close, {context.long_ma})"
    ]
    
    return {
        'select_buy': buy_conditions,
        'buy_at_least_count': 2,  # 必须同时满足
        'select_sell': sell_conditions,
        'sell_at_least_count': 2,  # 必须同时满足
        'order_by_signal': f'roc(close, {context.short_ma})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
'''

def print_strategies():
    """打印所有策略代码"""
    print("📋 双均线策略演示代码")
    print("=" * 80)
    print("\n1. 经典双均线策略：")
    print(CLASSIC_DUAL_MA)
    
    print("\n" + "=" * 80)
    print("\n2. 优化版双均线策略（带RSI过滤）：")
    print(OPTIMIZED_DUAL_MA)
    
    print("\n" + "=" * 80)
    print("\n3. 三均线趋势策略：")
    print(TRIPLE_MA_TREND)
    
    print("\n" + "=" * 80)
    print("📖 使用说明：")
    print("1. 复制上述任一策略代码")
    print("2. 启动Streamlit应用：python3 -m streamlit run streamlit_app.py")
    print("3. 选择「📝 自定义策略」功能")
    print("4. 将代码粘贴到编辑器中")
    print("5. 设置回测参数并运行")

def generate_strategy_file():
    """生成策略文件"""
    strategies = {
        "classic_dual_ma.py": CLASSIC_DUAL_MA,
        "optimized_dual_ma.py": OPTIMIZED_DUAL_MA,
        "triple_ma_trend.py": TRIPLE_MA_TREND
    }
    
    for filename, code in strategies.items():
        filepath = Path(__file__).parent / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f'''"""
双均线策略 - {filename}
使用说明：复制代码到Streamlit应用的自定义策略编辑器中
"""

{code}
''')
        print(f"✅ 策略文件已生成：{filepath}")

if __name__ == "__main__":
    from pathlib import Path
    
    print("🎯 双均线策略演示")
    print("=" * 80)
    
    # 打印策略代码
    print_strategies()
    
    # 生成策略文件
    print("\n📁 正在生成策略文件...")
    generate_strategy_file()
    
    print("\n🚀 快速开始：")
    print("1. 复制任一策略代码")
    print("2. 启动应用：python3 -m streamlit run streamlit_app.py")
    print("3. 访问：http://localhost:8501")
    print("4. 选择「📝 自定义策略」")
    print("5. 粘贴代码并测试")