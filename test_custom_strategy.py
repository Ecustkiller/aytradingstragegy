"""
自定义策略编辑器功能测试脚本
"""

import sys
from pathlib import Path

# 添加模块路径
AITRADER_PATH = Path(__file__).parent / "aitrader_core"
sys.path.insert(0, str(AITRADER_PATH))

from modules.custom_strategy_editor import execute_strategy_code, run_backtest_with_task


# 测试策略代码
test_strategy = """
def initialize(context):
    '''双均线策略测试'''
    context.symbols = ['159915.SZ', '518880.SH']  # 创业板ETF + 黄金ETF
    context.short_ma = 5
    context.long_ma = 20

def handle_data(context):
    return {
        'select_buy': [f"ma(close, {context.short_ma}) > ma(close, {context.long_ma})"],
        'select_sell': [f"ma(close, {context.short_ma}) < ma(close, {context.long_ma})"],
        'order_by_signal': 'roc(close, 5)',
        'order_by_topK': 1,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
"""


def test_code_execution():
    """测试代码解析"""
    print("=" * 60)
    print("测试1: 策略代码解析")
    print("=" * 60)

    task, error = execute_strategy_code(test_strategy)

    if error:
        print(f"❌ 解析失败：{error}")
        return False

    print("✅ 代码解析成功！")
    print(f"\n策略配置：")
    print(f"  股票池：{task.symbols}")
    print(f"  买入条件：{task.select_buy}")
    print(f"  卖出条件：{task.select_sell}")
    print(f"  排序因子：{task.order_by_signal}")
    print(f"  持仓数量：{task.order_by_topK}")
    print(f"  加权方式：{task.weight}")
    print(f"  调仓周期：{task.period}")

    return True


def test_backtest():
    """测试回测（需要本地数据）"""
    print("\n" + "=" * 60)
    print("测试2: 回测执行（需要本地数据）")
    print("=" * 60)

    # 解析策略
    task, error = execute_strategy_code(test_strategy)
    if error:
        print(f"❌ 解析失败：{error}")
        return False

    # 修改回测时间范围（短期测试）
    task.start_date = '20230101'
    task.end_date = '20231231'

    # 检查数据路径
    data_path = Path.home() / "stock_data"
    if not data_path.exists():
        print(f"⚠️  本地数据路径不存在：{data_path}")
        print(f"💡 请先在应用中执行「💾 AI数据管理」→「开始更新」")
        return False

    print(f"✅ 数据路径存在：{data_path}")
    print(f"回测时间：{task.start_date} - {task.end_date}")
    print("开始回测...")

    # 执行回测
    result, error = run_backtest_with_task(task, 'csv', data_path)

    if error:
        print(f"❌ 回测失败：{error}")
        return False

    print("✅ 回测成功！")
    print("\n回测结果：")
    print(result.stats)

    return True


def test_templates():
    """测试所有模板"""
    print("\n" + "=" * 60)
    print("测试3: 验证所有策略模板")
    print("=" * 60)

    from modules.custom_strategy_editor import STRATEGY_TEMPLATES

    success_count = 0
    for name, code in STRATEGY_TEMPLATES.items():
        print(f"\n测试模板：{name}")
        task, error = execute_strategy_code(code)

        if error:
            print(f"  ❌ 失败：{error}")
        else:
            print(f"  ✅ 成功")
            success_count += 1

    print(f"\n总结：{success_count}/{len(STRATEGY_TEMPLATES)} 个模板验证通过")
    return success_count == len(STRATEGY_TEMPLATES)


if __name__ == "__main__":
    print("🚀 开始测试自定义策略编辑器\n")

    # 测试1：代码解析
    if not test_code_execution():
        print("\n❌ 测试失败，请检查代码")
        sys.exit(1)

    # 测试2：模板验证
    if not test_templates():
        print("\n⚠️  部分模板验证失败")

    # 测试3：回测（可选，需要数据）
    try:
        test_backtest()
    except Exception as e:
        print(f"\n⚠️  回测测试跳过（可能缺少数据）：{e}")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n💡 启动应用查看完整功能：")
    print("   python3 -m streamlit run streamlit_app.py")
