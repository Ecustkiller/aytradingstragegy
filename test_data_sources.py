#!/usr/bin/env python3
"""
测试数据源回测功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.custom_strategy_editor import run_backtest_with_task, run_backtest_with_akshare

def test_dual_ma_strategy():
    """双均线策略"""
    def initialize(context):
        context.symbols = ['600519.SH', '000001.SZ']
        context.short_ma = 5
        context.long_ma = 20
        context.hold_count = 1

    def handle_data(context):
        buy_signal = f"ma(close, {context.short_ma}) > ma(close, {context.long_ma})"
        sell_signal = f"ma(close, {context.short_ma}) < ma(close, {context.long_ma})"
        
        return {
            'select_buy': [buy_signal],
            'select_sell': [sell_signal],
            'order_by_signal': f'roc(close, {context.short_ma})',
            'order_by_topK': context.hold_count,
            'weight': 'WeighEqually',
            'period': 'RunDaily'
        }
    
    return initialize, handle_data

def test_data_sources():
    """测试各种数据源"""
    print("🧪 测试数据源回测功能")
    print("=" * 50)
    
    # 创建策略任务
    initialize, handle_data = test_dual_ma_strategy()
    
try:
        # 创建Task对象
        from aitrader_core.bt_engine import Task
        task = Task()
        
        # 执行initialize函数
        class Context:
            pass
        context = Context()
        initialize(context)
        
        # 执行handle_data函数
        strategy_params = handle_data(context)
        
        # 设置任务参数
        task.name = '双均线测试策略'
        task.symbols = context.symbols
        task.start_date = '20240101'
        task.end_date = '20240331'
        task.benchmark = '000300.SH'
        
        task.select_buy = strategy_params.get('select_buy', [])
        task.select_sell = strategy_params.get('select_sell', [])
        task.order_by_signal = strategy_params.get('order_by_signal', 'roc(close, 5)')
        task.order_by_topK = strategy_params.get('order_by_topK', 1)
        task.weight = strategy_params.get('weight', 'WeighEqually')
        task.period = strategy_params.get('period', 'RunDaily')
        task.period_days = strategy_params.get('period_days', None)
        
        print(f"📊 策略名称: {task.name}")
        print(f"📈 股票池: {task.symbols}")
        print(f"📅 回测时间: {task.start_date} - {task.end_date}")
        print(f"💰 基准: {task.benchmark}")
        
        # 测试CSV数据源
        print("\n1️⃣ 测试CSV数据源...")
        result, error = run_backtest_with_task(task, 'csv')
        if error:
            print(f"❌ CSV数据源失败: {error}")
        else:
            print("✅ CSV数据源成功")
            if hasattr(result, 'stats'):
                total_return = result.stats.loc['策略', 'total_return']
                print(f"   📈 总收益率: {total_return:.2%}")
        
        # 测试AKShare数据源
        print("\n2️⃣ 测试AKShare数据源...")
        result, error = run_backtest_with_akshare(task)
        if error:
            print(f"❌ AKShare数据源失败: {error}")
        else:
            print("✅ AKShare数据源成功")
            if hasattr(result, 'stats'):
                total_return = result.stats.loc['策略', 'total_return']
                print(f"   📈 总收益率: {total_return:.2%}")
        
        print("\n🎉 数据源测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_sources()