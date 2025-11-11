"""
双均线策略 - triple_ma_trend.py
使用说明：复制代码到Streamlit应用的自定义策略编辑器中
"""


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

