#!/usr/bin/env python3
"""
双均线策略测试脚本
测试多种双均线策略变体并提供详细的回测分析
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加模块路径
AITRADER_PATH = Path(__file__).parent / "aitrader_core"
sys.path.insert(0, str(AITRADER_PATH))

from modules.custom_strategy_editor import execute_strategy_code, run_backtest_with_task


class DualMAStrategies:
    """双均线策略集合"""
    
    @staticmethod
    def classic_dual_ma():
        """经典双均线策略"""
        return """
def initialize(context):
    '''经典双均线策略
    短期均线上穿长期均线买入，下穿卖出
    '''
    # 股票池：主要A股
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600519.SH',  # 贵州茅台
        '000858.SZ'   # 五粮液
    ]
    context.short_ma = 5   # 短期均线
    context.long_ma = 20   # 长期均线
    context.hold_count = 2 # 持仓数量

def handle_data(context):
    # 金叉买入信号
    buy_signal = f"ma(close, {context.short_ma}) > ma(close, {context.long_ma})"
    # 死叉卖出信号
    sell_signal = f"ma(close, {context.short_ma}) < ma(close, {context.long_ma})"
    
    return {
        'select_buy': [buy_signal],
        'select_sell': [sell_signal],
        'order_by_signal': f'roc(close, {context.short_ma})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
"""
    
    @staticmethod
    def ema_dual_ma():
        """EMA双均线策略"""
        return """
def initialize(context):
    '''EMA双均线策略
    使用指数移动平均线，更敏感
    '''
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600036.SH',  # 招商银行
        '000858.SZ'   # 五粮液
    ]
    context.short_ema = 8   # 短期EMA
    context.long_ema = 21   # 长期EMA
    context.hold_count = 2

def handle_data(context):
    # EMA金叉买入
    buy_signal = f"ema(close, {context.short_ema}) > ema(close, {context.long_ema})"
    # EMA死叉卖出
    sell_signal = f"ema(close, {context.short_ema}) < ema(close, {context.long_ema})"
    
    return {
        'select_buy': [buy_signal],
        'select_sell': [sell_signal],
        'order_by_signal': f'roc(close, {context.short_ema})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
"""
    
    @staticmethod
    def triple_ma():
        """三均线策略"""
        return """
def initialize(context):
    '''三均线策略
    短、中、长三根均线，多头排列时买入
    '''
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600000.SH',  # 浦发银行
        '000858.SZ'   # 五粮液
    ]
    context.ma_short = 5   # 短期均线
    context.ma_mid = 20    # 中期均线
    context.ma_long = 60   # 长期均线
    context.hold_count = 2

def handle_data(context):
    # 多头排列：短 > 中 > 长
    buy_conditions = [
        f"ma(close, {context.ma_short}) > ma(close, {context.ma_mid})",
        f"ma(close, {context.ma_mid}) > ma(close, {context.ma_long})"
    ]
    
    # 空头排列：短 < 中 < 长
    sell_conditions = [
        f"ma(close, {context.ma_short}) < ma(close, {context.ma_mid})",
        f"ma(close, {context.ma_mid}) < ma(close, {context.ma_long})"
    ]
    
    return {
        'select_buy': buy_conditions,
        'buy_at_least_count': 2,  # 必须同时满足
        'select_sell': sell_conditions,
        'sell_at_least_count': 2,
        'order_by_signal': f'roc(close, {context.ma_short})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
"""
    
    @staticmethod
    def ma_with_rsi():
        """均线+RSI过滤策略"""
        return """
def initialize(context):
    '''均线+RSI过滤策略
    均线金叉且RSI不超买时买入
    '''
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600036.SH',  # 招商银行
        '000858.SZ'   # 五粮液
    ]
    context.short_ma = 10
    context.long_ma = 30
    context.rsi_period = 14
    context.rsi_oversold = 30
    context.rsi_overbought = 70
    context.hold_count = 2

def handle_data(context):
    # 买入条件：均线金叉 + RSI不超买
    buy_conditions = [
        f"ma(close, {context.short_ma}) > ma(close, {context.long_ma})",
        f"rsi(close, {context.rsi_period}) < {context.rsi_overbought}"
    ]
    
    # 卖出条件：均线死叉 或 RSI超买
    sell_conditions = [
        f"ma(close, {context.short_ma}) < ma(close, {context.long_ma})",
        f"rsi(close, {context.rsi_period}) > {context.rsi_overbought}"
    ]
    
    return {
        'select_buy': buy_conditions,
        'buy_at_least_count': 2,  # 两个条件都要满足
        'select_sell': sell_conditions,
        'sell_at_least_count': 1,  # 满足一个即可卖出
        'order_by_signal': f'roc(close, {context.short_ma})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
"""
    
    @staticmethod
    def adaptive_ma():
        """自适应均线策略"""
        return """
def initialize(context):
    '''自适应均线策略
    根据市场波动率调整均线周期
    '''
    context.symbols = [
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '600519.SH',  # 贵州茅台
        '000858.SZ'   # 五粮液
    ]
    context.base_short = 8
    context.base_long = 24
    context.hold_count = 2

def handle_data(context):
    # 这里使用固定周期作为示例，实际可以计算ATR等指标来调整
    short_period = context.base_short
    long_period = context.base_long
    
    buy_signal = f"ma(close, {short_period}) > ma(close, {long_period})"
    sell_signal = f"ma(close, {short_period}) < ma(close, {long_period})"
    
    return {
        'select_buy': [buy_signal],
        'select_sell': [sell_signal],
        'order_by_signal': f'roc(close, {short_period})',
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
"""


def test_strategy_validation():
    """测试策略验证"""
    print("=" * 80)
    print("🔍 策略代码验证测试")
    print("=" * 80)
    
    strategies = {
        "经典双均线": DualMAStrategies.classic_dual_ma(),
        "EMA双均线": DualMAStrategies.ema_dual_ma(),
        "三均线策略": DualMAStrategies.triple_ma(),
        "均线+RSI": DualMAStrategies.ma_with_rsi(),
        "自适应均线": DualMAStrategies.adaptive_ma()
    }
    
    success_count = 0
    for name, code in strategies.items():
        print(f"\n📋 测试策略：{name}")
        try:
            task, error = execute_strategy_code(code)
            if error:
                print(f"  ❌ 验证失败：{error}")
            else:
                print(f"  ✅ 验证通过")
                print(f"     股票池：{len(task.symbols)}只")
                print(f"     买入条件：{len(task.select_buy)}个")
                print(f"     卖出条件：{len(task.select_sell)}个")
                print(f"     调仓周期：{task.period}")
                success_count += 1
        except Exception as e:
            print(f"  ❌ 异常：{e}")
    
    print(f"\n📊 验证结果：{success_count}/{len(strategies)} 个策略通过验证")
    return success_count == len(strategies)


def run_backtest_comparison():
    """运行回测对比"""
    print("\n" + "=" * 80)
    print("📈 双均线策略回测对比")
    print("=" * 80)
    
    # 检查数据路径
    data_path = Path.home() / "stock_data"
    if not data_path.exists():
        print(f"⚠️  本地数据路径不存在：{data_path}")
        print("💡 请先在应用中执行「💾 AI数据管理」→「开始更新」")
        return False
    
    # 选择要回测的策略
    strategies_to_test = {
        "经典双均线(5,20)": DualMAStrategies.classic_dual_ma(),
        "EMA双均线(8,21)": DualMAStrategies.ema_dual_ma(),
        "均线+RSI过滤": DualMAStrategies.ma_with_rsi()
    }
    
    # 回测时间范围
    backtest_results = {}
    
    for name, code in strategies_to_test.items():
        print(f"\n🚀 回测策略：{name}")
        print("-" * 50)
        
        try:
            # 解析策略
            task, error = execute_strategy_code(code)
            if error:
                print(f"❌ 策略解析失败：{error}")
                continue
            
            # 设置回测时间
            task.start_date = '20230101'
            task.end_date = '20241101'
            
            print(f"📅 回测时间：{task.start_date} - {task.end_date}")
            print(f"📊 股票池：{task.symbols}")
            
            # 执行回测
            result, error = run_backtest_with_task(task, 'csv', data_path)
            if error:
                print(f"❌ 回测失败：{error}")
                continue
            
            # 保存结果
            backtest_results[name] = result
            
            # 显示关键指标
            stats = result.stats
            total_return = stats.loc['策略', 'total_return']
            cagr = stats.loc['策略', 'cagr']
            max_dd = stats.loc['策略', 'max_drawdown']
            sharpe = stats.loc['策略', 'daily_sharpe']
            
            print(f"📊 回测结果：")
            print(f"   总收益率：{total_return:.2%}")
            print(f"   年化收益：{cagr:.2%}")
            print(f"   最大回撤：{max_dd:.2%}")
            print(f"   夏普比率：{sharpe:.2f}")
            
        except Exception as e:
            print(f"❌ 回测异常：{e}")
    
    # 生成对比表格
    if backtest_results:
        print("\n" + "=" * 80)
        print("📋 策略对比汇总")
        print("=" * 80)
        
        comparison_data = []
        for name, result in backtest_results.items():
            stats = result.stats
            comparison_data.append({
                '策略名称': name,
                '总收益率': f"{stats.loc['策略', 'total_return']:.2%}",
                '年化收益': f"{stats.loc['策略', 'cagr']:.2%}",
                '最大回撤': f"{stats.loc['策略', 'max_drawdown']:.2%}",
                '夏普比率': f"{stats.loc['策略', 'daily_sharpe']:.2f}",
                '交易次数': stats.loc['策略', 'total_trades']
            })
        
        df = pd.DataFrame(comparison_data)
        print(df.to_string(index=False))
        
        # 保存详细结果
        save_backtest_results(backtest_results)
    
    return len(backtest_results) > 0


def save_backtest_results(results):
    """保存回测结果到文件"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存对比表格
        comparison_data = []
        for name, result in results.items():
            stats = result.stats
            comparison_data.append({
                '策略名称': name,
                '总收益率': stats.loc['策略', 'total_return'],
                '年化收益': stats.loc['策略', 'cagr'],
                '最大回撤': stats.loc['策略', 'max_drawdown'],
                '夏普比率': stats.loc['策略', 'daily_sharpe'],
                '交易次数': stats.loc['策略', 'total_trades']
            })
        
        df = pd.DataFrame(comparison_data)
        csv_file = Path(__file__).parent / f"dual_ma_backtest_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 回测结果已保存到：{csv_file}")
        
    except Exception as e:
        print(f"⚠️  保存结果失败：{e}")


def generate_strategy_report():
    """生成策略报告"""
    print("\n" + "=" * 80)
    print("📝 双均线策略分析报告")
    print("=" * 80)
    
    report = """
## 双均线策略分析

### 策略原理
双均线策略是最经典的技术分析策略之一，基于不同周期移动平均线的交叉信号：
- **金叉**：短期均线上穿长期均线，买入信号
- **死叉**：短期均线下穿长期均线，卖出信号

### 策略变体
1. **经典双均线**：使用简单移动平均线(SMA)
2. **EMA双均线**：使用指数移动平均线，更敏感
3. **三均线策略**：增加中期均线，确认趋势
4. **均线+RSI**：增加RSI过滤器，避免超买超卖
5. **自适应均线**：根据市场波动率调整参数

### 参数设置建议
- **短期均线**：5-10日
- **长期均线**：20-60日
- **ETF投资**：建议5-20日周期
- **个股投资**：建议10-30日周期

### 优缺点分析
**优点：**
- 简单易懂，容易实现
- 趋势跟踪效果好
- 适合ETF等指数产品

**缺点：**
- 震荡市容易频繁交易
- 存在滞后性
- 需要配合其他指标过滤

### 使用建议
1. 选择流动性好的ETF或大盘股
2. 设置合理的止损止盈
3. 配合成交量等其他指标
4. 避免在重大消息发布期间交易
"""
    
    print(report)
    
    # 保存报告
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = Path(__file__).parent / f"dual_ma_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n💾 策略报告已保存到：{report_file}")
    except Exception as e:
        print(f"⚠️  保存报告失败：{e}")


def main():
    """主函数"""
    print("🎯 双均线策略测试系统")
    print("=" * 80)
    print("测试多种双均线策略变体，提供详细的回测分析")
    print("=" * 80)
    
    # 1. 策略验证
    if not test_strategy_validation():
        print("\n❌ 策略验证失败，请检查代码")
        return
    
    # 2. 回测对比
    if not run_backtest_comparison():
        print("\n⚠️  回测未完成，可能缺少本地数据")
        print("💡 请先更新数据：在应用中执行「💾 AI数据管理」→「开始更新」")
    
    # 3. 生成报告
    generate_strategy_report()
    
    print("\n" + "=" * 80)
    print("✅ 双均线策略测试完成！")
    print("=" * 80)
    print("\n🚀 启动Streamlit应用进行可视化测试：")
    print("   python3 -m streamlit run streamlit_app.py")
    print("   然后选择「📝 自定义策略」功能")


if __name__ == "__main__":
    main()