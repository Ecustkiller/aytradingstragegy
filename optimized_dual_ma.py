"""
双均线策略 - optimized_dual_ma.py
使用说明：复制代码到Streamlit应用的自定义策略编辑器中
"""


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

