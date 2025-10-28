"""
交易建议模块 - 根据技术指标分析给出交易建议
"""
import pandas as pd
import numpy as np

def generate_trade_advice(market_status):
    """
    根据市场状态和技术指标生成交易建议
    
    参数:
    market_status: 由 analyze_market_status 函数生成的市场状态字典
    
    返回:
    dict: 包含交易建议、建议仓位和理由的字典
    """
    if not market_status:
        return {
            "action": "观望",
            "position": 0,
            "reason": "无法获取足够的市场数据进行分析"
        }
    
    # 提取各项指标状态
    ma_status = market_status.get("ma", {}).get("status", "中性")
    macd_status = market_status.get("macd", {}).get("status", "中性")
    rsi_status = market_status.get("rsi", {}).get("status", "中性")
    kdj_status = market_status.get("kdj", {}).get("status", "中性")
    vol_status = market_status.get("volume", {}).get("status", "平稳")
    price_status = market_status.get("price", {}).get("status", "中位")
    
    # 计算买入信号数量
    buy_signals = 0
    sell_signals = 0
    
    # 均线分析
    if ma_status == "看涨":
        buy_signals += 1
    elif ma_status == "看跌":
        sell_signals += 1
    
    # MACD分析
    if macd_status == "金叉" or macd_status == "看涨趋势":
        buy_signals += 1
    elif macd_status == "死叉" or macd_status == "看跌趋势":
        sell_signals += 1
    
    # RSI分析
    if rsi_status == "超卖":
        buy_signals += 1
    elif rsi_status == "超买":
        sell_signals += 1
    
    # KDJ分析
    if kdj_status == "超卖" or kdj_status == "金叉":
        buy_signals += 1
    elif kdj_status == "超买" or kdj_status == "死叉":
        sell_signals += 1
    
    # 成交量分析
    if vol_status == "放量" and (ma_status == "看涨" or macd_status == "金叉"):
        buy_signals += 0.5
    elif vol_status == "放量" and (ma_status == "看跌" or macd_status == "死叉"):
        sell_signals += 0.5
    
    # 价格位置分析
    if price_status == "低位":
        buy_signals += 0.5
    elif price_status == "高位":
        sell_signals += 0.5
    
    # 计算信号强度
    total_signals = 4  # 主要考虑MA, MACD, RSI, KDJ四个指标
    buy_strength = buy_signals / total_signals
    sell_strength = sell_signals / total_signals
    
    # 生成建议
    reasons = []
    
    if buy_strength > sell_strength and buy_strength > 0.5:
        # 买入信号
        position = int(min(buy_strength * 100, 100))
        action = "买入"
        
        # 生成买入理由
        if ma_status == "看涨":
            reasons.append("均线呈多头排列")
        if macd_status == "金叉":
            reasons.append("MACD金叉")
        elif macd_status == "看涨趋势":
            reasons.append("MACD处于上升趋势")
        if rsi_status == "超卖":
            reasons.append("RSI显示超卖")
        if kdj_status == "超卖":
            reasons.append("KDJ显示超卖")
        elif kdj_status == "金叉":
            reasons.append("KDJ金叉")
        if vol_status == "放量" and ma_status == "看涨":
            reasons.append("放量上涨")
        if price_status == "低位":
            reasons.append("价格处于低位")
            
    elif sell_strength > buy_strength and sell_strength > 0.5:
        # 卖出信号
        position = int(min(sell_strength * 100, 100))
        action = "卖出"
        
        # 生成卖出理由
        if ma_status == "看跌":
            reasons.append("均线呈空头排列")
        if macd_status == "死叉":
            reasons.append("MACD死叉")
        elif macd_status == "看跌趋势":
            reasons.append("MACD处于下降趋势")
        if rsi_status == "超买":
            reasons.append("RSI显示超买")
        if kdj_status == "超买":
            reasons.append("KDJ显示超买")
        elif kdj_status == "死叉":
            reasons.append("KDJ死叉")
        if vol_status == "放量" and ma_status == "看跌":
            reasons.append("放量下跌")
        if price_status == "高位":
            reasons.append("价格处于高位")
            
    else:
        # 观望信号
        position = 0
        action = "观望"
        
        # 生成观望理由
        if ma_status == "中性":
            reasons.append("均线走势不明确")
        if macd_status not in ["金叉", "死叉"]:
            reasons.append("MACD没有明确交叉信号")
        if rsi_status == "中性":
            reasons.append("RSI处于中性区间")
        if kdj_status == "中性":
            reasons.append("KDJ没有明确信号")
        if vol_status == "平稳":
            reasons.append("成交量平稳")
        if price_status == "中位":
            reasons.append("价格处于中位")
        
        # 如果没有找到观望理由，添加一个默认理由
        if not reasons:
            reasons.append("技术指标信号不明确，建议等待更清晰的市场方向")
    
    # 组合理由文本
    reason_text = "、".join(reasons)
    
    return {
        "action": action,
        "position": position,
        "reason": reason_text
    }

def get_comprehensive_advice(df):
    """
    获取综合交易建议
    
    参数:
    df: 包含技术指标的DataFrame
    
    返回:
    dict: 包含交易建议的字典
    """
    from .indicators import analyze_market_status
    
    # 获取市场状态
    market_status = analyze_market_status(df)
    
    # 生成交易建议
    advice = generate_trade_advice(market_status)
    
    # 添加市场状态到建议中
    advice["market_status"] = market_status
    
    return advice