"""
交易建议模块 - 根据技术指标和峰级线趋势分析给出交易建议
"""
import pandas as pd
import numpy as np
from .peak_valley_analyzer import peak_valley_analyzer

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
    获取综合交易建议（整合峰级线趋势分析）

    参数:
    df: 包含技术指标的DataFrame

    返回:
    dict: 包含交易建议的字典
    """
    from .indicators import analyze_market_status

    # 获取市场状态
    market_status = analyze_market_status(df)

    # 生成基础交易建议
    advice = generate_trade_advice(market_status)

    # 获取峰级线趋势分析
    try:
        peak_valley_advice = peak_valley_analyzer.generate_trade_advice(df)

        # 整合峰级线分析结果
        advice = integrate_peak_valley_advice(advice, peak_valley_advice, market_status)
    except Exception as e:
        # 如果峰级线分析失败，仍然返回基础建议
        print(f"峰级线分析失败: {e}")

    # 添加市场状态到建议中
    advice["market_status"] = market_status

    return advice

def integrate_peak_valley_advice(basic_advice, peak_valley_advice, market_status):
    """
    整合基础建议和峰级线建议

    参数:
    basic_advice: 基础技术指标建议
    peak_valley_advice: 峰级线趋势建议
    market_status: 市场状态

    返回:
    dict: 综合建议
    """
    # 提取峰级线建议信息
    pv_action = peak_valley_advice.get('action', 'hold')
    pv_confidence = peak_valley_advice.get('confidence', 0)
    pv_description = peak_valley_advice.get('description', '')
    pv_patterns = peak_valley_advice.get('patterns', [])
    pv_trend = peak_valley_advice.get('trend', {})
    support_levels = peak_valley_advice.get('support_levels', [])
    resistance_levels = peak_valley_advice.get('resistance_levels', [])

    # 提取基础建议信息
    basic_action = basic_advice.get('action', '观望')
    basic_position = basic_advice.get('position', 0)
    basic_reason = basic_advice.get('reason', '')

    # 动作映射
    action_map = {
        'buy': '买入',
        'sell': '卖出',
        'hold': '观望'
    }
    pv_action_cn = action_map.get(pv_action, '观望')

    # 综合判断：峰级线分析优先级更高
    final_action = basic_action
    final_position = basic_position
    final_reasons = [basic_reason] if basic_reason else []

    # 如果峰级线有明确信号且置信度高，调整建议
    if pv_confidence >= 0.7:
        final_action = pv_action_cn

        # 根据峰级线信号调整仓位
        if pv_action == 'buy':
            final_position = int(pv_confidence * 100)
        elif pv_action == 'sell':
            final_position = 0
        else:
            final_position = max(basic_position * 0.5, 30)  # 观望时保持轻仓

    # 添加峰级线分析理由
    peak_valley_reasons = []

    # 趋势分析
    if pv_trend:
        trend_desc = pv_trend.get('description', '')
        if trend_desc:
            peak_valley_reasons.append(f"【趋势】{trend_desc}")

    # 形态分析
    if pv_patterns:
        # 只显示最强的形态
        best_pattern = max(pv_patterns, key=lambda x: x.get('confidence', 0))
        pattern_name = best_pattern.get('pattern', '')
        pattern_desc = best_pattern.get('description', '')
        if pattern_name and pattern_desc:
            peak_valley_reasons.append(f"【形态】{pattern_desc}")

    # 支撑压力位分析
    if support_levels or resistance_levels:
        sr_info = []
        if support_levels:
            nearest_support = support_levels[0]
            sr_info.append(f"支撑位 {nearest_support:.2f}")
        if resistance_levels:
            nearest_resistance = resistance_levels[0]
            sr_info.append(f"压力位 {nearest_resistance:.2f}")
        if sr_info:
            peak_valley_reasons.append(f"【关键价位】{', '.join(sr_info)}")

    # 整合所有理由
    if peak_valley_reasons:
        final_reasons = peak_valley_reasons + final_reasons

    reason_text = "；".join(final_reasons) if final_reasons else "技术指标信号不明确，建议等待更清晰的市场方向"

    # 构建最终建议
    comprehensive_advice = {
        "action": final_action,
        "position": final_position,
        "reason": reason_text,
        "peak_valley_info": {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "trend": pv_trend,
            "patterns": pv_patterns,
            "confidence": pv_confidence
        }
    }

    # 如果有明确的止损和止盈价位，添加到建议中
    if 'stop_loss' in peak_valley_advice and peak_valley_advice['stop_loss']:
        comprehensive_advice['stop_loss'] = peak_valley_advice['stop_loss']

    if 'take_profit' in peak_valley_advice and peak_valley_advice['take_profit']:
        comprehensive_advice['take_profit'] = peak_valley_advice['take_profit']

    if 'entry_price' in peak_valley_advice and peak_valley_advice['entry_price']:
        comprehensive_advice['entry_price'] = peak_valley_advice['entry_price']

    return comprehensive_advice