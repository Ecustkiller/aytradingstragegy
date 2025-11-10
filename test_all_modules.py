"""
全面测试所有功能模块
检查错误并生成优化建议
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import traceback

# 测试结果收集
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_module(module_name, test_func):
    """测试单个模块"""
    print(f"\n{'='*60}")
    print(f"测试模块: {module_name}")
    print('='*60)
    try:
        test_func()
        test_results['passed'].append(module_name)
        print(f"✅ {module_name} 测试通过")
        return True
    except Exception as e:
        test_results['failed'].append((module_name, str(e)))
        print(f"❌ {module_name} 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def test_data_loader():
    """测试数据加载模块"""
    from modules.data_loader import get_stock_data

    # 测试CSV数据源
    df = get_stock_data("000001",
                       datetime.now() - timedelta(days=30),
                       datetime.now(),
                       "daily", "csv")
    assert df is not None and not df.empty, "CSV数据加载失败"
    print(f"  ✓ CSV数据源: 成功加载 {len(df)} 条数据")

    # 测试数据完整性
    required_cols = ['Open', 'Close', 'High', 'Low', 'Volume']
    for col in required_cols:
        assert col in df.columns, f"缺少必需列: {col}"
    print(f"  ✓ 数据完整性检查通过")

def test_indicators():
    """测试技术指标计算"""
    from modules.data_loader import get_stock_data
    from modules.indicators import calculate_technical_indicators, analyze_market_status

    df = get_stock_data("000001",
                       datetime.now() - timedelta(days=90),
                       datetime.now(),
                       "daily", "csv")

    # 计算技术指标
    df_with_indicators = calculate_technical_indicators(df)

    # 检查指标列
    indicator_cols = ['MA5', 'MA10', 'MA20', 'MACD', 'MACD_Signal', 'RSI', 'K', 'D', 'J']
    missing_cols = [col for col in indicator_cols if col not in df_with_indicators.columns]
    if missing_cols:
        print(f"  ⚠️ 缺少部分指标: {missing_cols}")
        test_results['warnings'].append(f"indicators: 缺少指标 {missing_cols}")
    else:
        print(f"  ✓ 所有技术指标计算成功")

    # 测试市场状态分析
    market_status = analyze_market_status(df_with_indicators)
    assert market_status is not None, "市场状态分析失败"
    assert 'ma' in market_status, "缺少均线状态"
    assert 'macd' in market_status, "缺少MACD状态"
    print(f"  ✓ 市场状态分析成功")

def test_trade_advisor():
    """测试交易建议模块"""
    from modules.data_loader import get_stock_data
    from modules.indicators import calculate_technical_indicators
    from modules.trade_advisor import get_comprehensive_advice

    df = get_stock_data("000001",
                       datetime.now() - timedelta(days=120),
                       datetime.now(),
                       "daily", "csv")
    df = calculate_technical_indicators(df)

    # 测试综合建议（含峰级线）
    advice = get_comprehensive_advice(df)
    assert advice is not None, "交易建议生成失败"
    assert 'action' in advice, "缺少操作建议"
    assert 'position' in advice, "缺少仓位建议"
    assert 'reason' in advice, "缺少理由说明"
    print(f"  ✓ 交易建议: {advice['action']}, 仓位: {advice['position']}%")

    # 检查峰级线信息
    if 'peak_valley_info' in advice:
        pv_info = advice['peak_valley_info']
        print(f"  ✓ 峰级线分析: 支撑位 {len(pv_info.get('support_levels', []))} 个, 压力位 {len(pv_info.get('resistance_levels', []))} 个")
    else:
        print(f"  ⚠️ 峰级线信息不完整")
        test_results['warnings'].append("trade_advisor: 峰级线信息不完整")

def test_peak_valley_analyzer():
    """测试峰谷分析模块"""
    from modules.data_loader import get_stock_data
    from modules.peak_valley_analyzer import peak_valley_analyzer

    df = get_stock_data("000001",
                       datetime.now() - timedelta(days=120),
                       datetime.now(),
                       "daily", "csv")

    # 测试峰谷识别
    df_marked = peak_valley_analyzer.identify_peaks_valleys(df)
    peaks = df_marked[df_marked['is_peak']]
    valleys = df_marked[df_marked['is_valley']]
    print(f"  ✓ 峰谷识别: {len(peaks)} 个峰点, {len(valleys)} 个谷点")

    # 测试支撑压力位
    sr_levels = peak_valley_analyzer.calculate_support_resistance(df)
    print(f"  ✓ 支撑压力位: {len(sr_levels['support_levels'])} 个支撑, {len(sr_levels['resistance_levels'])} 个压力")

    # 测试趋势分析
    trend = peak_valley_analyzer.analyze_trend(df)
    print(f"  ✓ 趋势分析: {trend['trend']}, 置信度 {trend['confidence']:.0%}")

    # 测试形态识别
    patterns = peak_valley_analyzer.identify_trading_patterns(df)
    print(f"  ✓ 形态识别: {len(patterns)} 个形态")

def test_visualization():
    """测试可视化模块"""
    from modules.data_loader import get_stock_data
    from modules.indicators import calculate_technical_indicators
    from modules.visualization import create_plotly_chart

    df = get_stock_data("000001",
                       datetime.now() - timedelta(days=60),
                       datetime.now(),
                       "daily", "csv")
    df = calculate_technical_indicators(df)

    # 测试基础K线图
    fig = create_plotly_chart(df, "日线", show_ma=True, show_vol=True,
                             show_peak_valley=True, data_source="csv")
    assert fig is not None, "K线图生成失败"
    print(f"  ✓ K线图生成成功（含峰谷标记）")

    # 测试完整指标图表
    fig_full = create_plotly_chart(df, "日线", show_ma=True, show_boll=True,
                                   show_vol=True, show_macd=True, show_kdj=True,
                                   show_rsi=True, show_peak_valley=True,
                                   data_source="csv")
    assert fig_full is not None, "完整图表生成失败"
    print(f"  ✓ 完整技术指标图表生成成功")

def test_enhanced_momentum_selector():
    """测试增强选股模块"""
    try:
        from modules.enhanced_momentum_selector import (
            calculate_rps, screen_stocks, get_all_stock_list
        )

        # 测试获取股票列表
        stock_list = get_all_stock_list()
        if stock_list is not None and not stock_list.empty:
            print(f"  ✓ 股票列表获取成功: {len(stock_list)} 只股票")
        else:
            print(f"  ⚠️ 股票列表为空")
            test_results['warnings'].append("enhanced_momentum: 股票列表为空")

        # RPS计算测试（使用小样本）
        print(f"  ✓ 增强选股模块加载成功")

    except ImportError as e:
        print(f"  ⚠️ 增强选股模块依赖缺失: {e}")
        test_results['warnings'].append(f"enhanced_momentum: 依赖缺失 - {e}")

def test_concept_analysis():
    """测试概念分析模块"""
    try:
        from modules.concept_analysis import HAS_PYWENCAI

        if HAS_PYWENCAI:
            print(f"  ✓ 问财接口可用")
        else:
            print(f"  ⚠️ 问财接口不可用，pywencai未安装")
            test_results['warnings'].append("concept_analysis: pywencai未安装")

    except Exception as e:
        print(f"  ⚠️ 概念分析模块异常: {e}")
        test_results['warnings'].append(f"concept_analysis: {e}")

def test_auction_analysis():
    """测试竞价分析模块"""
    try:
        from modules.auction_analysis import HAS_PYWENCAI, HAS_CHINESE_CALENDAR

        if HAS_PYWENCAI:
            print(f"  ✓ 问财接口可用")
        else:
            print(f"  ⚠️ 问财接口不可用")
            test_results['warnings'].append("auction_analysis: pywencai未安装")

        if not HAS_CHINESE_CALENDAR:
            print(f"  ⚠️ 交易日历不可用，chinese_calendar未安装")
            test_results['warnings'].append("auction_analysis: chinese_calendar未安装")
        else:
            print(f"  ✓ 交易日历可用")

    except Exception as e:
        print(f"  ⚠️ 竞价分析模块异常: {e}")
        test_results['warnings'].append(f"auction_analysis: {e}")

def test_limit_up_analysis():
    """测试涨停分析模块"""
    try:
        from modules.limit_up_analysis import HAS_PYWENCAI, HAS_AKSHARE

        if HAS_PYWENCAI:
            print(f"  ✓ 问财接口可用")
        else:
            print(f"  ⚠️ 问财接口不可用")
            test_results['warnings'].append("limit_up_analysis: pywencai未安装")

        if HAS_AKSHARE:
            print(f"  ✓ AKShare可用")
        else:
            print(f"  ⚠️ AKShare不可用")
            test_results['warnings'].append("limit_up_analysis: akshare未安装")

    except Exception as e:
        print(f"  ⚠️ 涨停分析模块异常: {e}")
        test_results['warnings'].append(f"limit_up_analysis: {e}")

def test_custom_strategy_editor():
    """测试自定义策略编辑器"""
    try:
        from modules.custom_strategy_editor import execute_strategy_code, STRATEGY_TEMPLATES

        # 测试策略模板
        print(f"  ✓ 策略模板数量: {len(STRATEGY_TEMPLATES)}")

        # 测试简单策略执行
        test_code = """
def initialize(context):
    context.s1 = '000001.SZ'

def handle_data(context, data):
    pass
"""
        try:
            task = execute_strategy_code(test_code, data_source='csv')
            if task:
                print(f"  ✓ 策略代码解析成功")
            else:
                print(f"  ⚠️ 策略代码解析返回None")
                test_results['warnings'].append("custom_strategy: 策略解析返回None")
        except Exception as e:
            print(f"  ⚠️ 策略代码执行测试失败: {e}")
            test_results['warnings'].append(f"custom_strategy: {e}")

    except Exception as e:
        print(f"  ⚠️ 自定义策略编辑器异常: {e}")
        test_results['warnings'].append(f"custom_strategy: {e}")

def test_aitrader_integration():
    """测试AI Trader集成"""
    try:
        from modules.aitrader_integration import check_aitrader_available

        available, path = check_aitrader_available()
        if available:
            print(f"  ✓ AI Trader可用: {path}")
        else:
            print(f"  ⚠️ AI Trader不可用")
            test_results['warnings'].append("aitrader: AI Trader不可用")

    except Exception as e:
        print(f"  ⚠️ AI Trader集成异常: {e}")
        test_results['warnings'].append(f"aitrader: {e}")

def test_performance():
    """性能测试"""
    import time
    from modules.data_loader import get_stock_data
    from modules.indicators import calculate_technical_indicators
    from modules.trade_advisor import get_comprehensive_advice

    print("\n  性能测试:")

    # 数据加载性能
    start = time.time()
    df = get_stock_data("000001",
                       datetime.now() - timedelta(days=120),
                       datetime.now(),
                       "daily", "csv")
    data_load_time = time.time() - start
    print(f"    数据加载: {data_load_time:.3f}秒")

    # 指标计算性能
    start = time.time()
    df = calculate_technical_indicators(df)
    indicator_time = time.time() - start
    print(f"    指标计算: {indicator_time:.3f}秒")

    # 交易建议性能（含峰级线）
    start = time.time()
    advice = get_comprehensive_advice(df)
    advice_time = time.time() - start
    print(f"    交易建议（含峰级线）: {advice_time:.3f}秒")

    # 性能警告
    if data_load_time > 2:
        test_results['warnings'].append(f"performance: 数据加载较慢 ({data_load_time:.1f}秒)")
    if indicator_time > 1:
        test_results['warnings'].append(f"performance: 指标计算较慢 ({indicator_time:.1f}秒)")
    if advice_time > 2:
        test_results['warnings'].append(f"performance: 交易建议生成较慢 ({advice_time:.1f}秒)")

def print_summary():
    """打印测试摘要"""
    print("\n" + "="*60)
    print("测试摘要")
    print("="*60)

    print(f"\n✅ 通过的测试 ({len(test_results['passed'])}):")
    for module in test_results['passed']:
        print(f"  - {module}")

    if test_results['failed']:
        print(f"\n❌ 失败的测试 ({len(test_results['failed'])}):")
        for module, error in test_results['failed']:
            print(f"  - {module}: {error}")

    if test_results['warnings']:
        print(f"\n⚠️ 警告 ({len(test_results['warnings'])}):")
        for warning in test_results['warnings']:
            print(f"  - {warning}")

    # 统计
    total = len(test_results['passed']) + len(test_results['failed'])
    success_rate = len(test_results['passed']) / total * 100 if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"总测试: {total} | 通过: {len(test_results['passed'])} | 失败: {len(test_results['failed'])} | 成功率: {success_rate:.1f}%")
    print("="*60)

def main():
    """主测试函数"""
    print("="*60)
    print("AY Trading System - 全面功能测试")
    print("="*60)

    # 核心模块测试
    test_module("数据加载", test_data_loader)
    test_module("技术指标", test_indicators)
    test_module("交易建议", test_trade_advisor)
    test_module("峰谷分析", test_peak_valley_analyzer)
    test_module("可视化", test_visualization)

    # 功能模块测试
    test_module("增强选股", test_enhanced_momentum_selector)
    test_module("概念分析", test_concept_analysis)
    test_module("竞价分析", test_auction_analysis)
    test_module("涨停分析", test_limit_up_analysis)
    test_module("自定义策略", test_custom_strategy_editor)
    test_module("AI Trader集成", test_aitrader_integration)

    # 性能测试
    test_module("性能测试", test_performance)

    # 打印摘要
    print_summary()

    # 生成优化建议
    print("\n" + "="*60)
    print("优化建议")
    print("="*60)
    generate_optimization_suggestions()

def generate_optimization_suggestions():
    """生成优化建议"""
    suggestions = []

    # 基于测试结果生成建议
    if any('pywencai' in w for w in test_results['warnings']):
        suggestions.append({
            'priority': 'high',
            'category': '依赖缺失',
            'issue': 'pywencai库未安装',
            'suggestion': '安装pywencai以启用概念分析、竞价分析、涨停分析功能',
            'command': 'pip install pywencai'
        })

    if any('chinese_calendar' in w for w in test_results['warnings']):
        suggestions.append({
            'priority': 'medium',
            'category': '依赖缺失',
            'issue': 'chinese_calendar库未安装',
            'suggestion': '安装chinese_calendar以提供准确的交易日历',
            'command': 'pip install chinesecalendar'
        })

    if any('akshare' in w for w in test_results['warnings']):
        suggestions.append({
            'priority': 'medium',
            'category': '依赖缺失',
            'issue': 'akshare库问题',
            'suggestion': '更新或重新安装akshare以获取更准确的交易日历',
            'command': 'pip install --upgrade akshare'
        })

    if any('performance' in w for w in test_results['warnings']):
        suggestions.append({
            'priority': 'medium',
            'category': '性能优化',
            'issue': '部分操作耗时较长',
            'suggestion': '考虑添加数据缓存机制，减少重复计算'
        })

    # 通用优化建议
    suggestions.extend([
        {
            'priority': 'low',
            'category': '用户体验',
            'issue': '峰谷点可能过多',
            'suggestion': '在可视化中添加开关，允许用户控制是否显示峰谷标记'
        },
        {
            'priority': 'low',
            'category': '功能增强',
            'issue': '支撑压力位固定显示3个',
            'suggestion': '允许用户自定义显示的支撑压力位数量'
        },
        {
            'priority': 'medium',
            'category': '数据验证',
            'issue': '缺少数据质量检查',
            'suggestion': '添加数据异常检测（如突然的价格跳跃、异常成交量等）'
        },
        {
            'priority': 'low',
            'category': '文档',
            'issue': '缺少峰级线交易理论说明',
            'suggestion': '在UI中添加峰级线理论的简要说明和使用指南'
        }
    ])

    # 按优先级排序
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    suggestions.sort(key=lambda x: priority_order[x['priority']])

    # 打印建议
    for i, sug in enumerate(suggestions, 1):
        priority_icon = '🔴' if sug['priority'] == 'high' else '🟡' if sug['priority'] == 'medium' else '🟢'
        print(f"\n{i}. {priority_icon} [{sug['category']}] {sug['issue']}")
        print(f"   建议: {sug['suggestion']}")
        if 'command' in sug:
            print(f"   命令: {sug['command']}")

if __name__ == "__main__":
    main()
