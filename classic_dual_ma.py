"""
双均线策略 - classic_dual_ma.py
使用说明：复制代码到Streamlit应用的自定义策略编辑器中
"""


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

