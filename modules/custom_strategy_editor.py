"""
自定义策略编辑器 - 类聚宽平台
支持在线编写策略代码、回测、查看结果
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import io
import matplotlib.pyplot as plt

# 添加AI Trader路径
AITRADER_PATH = Path(__file__).parent.parent / "aitrader_core"
if str(AITRADER_PATH) not in sys.path:
    sys.path.insert(0, str(AITRADER_PATH))


# 策略模板库
STRATEGY_TEMPLATES = {
    "均线策略": """# 双均线策略示例
def initialize(context):
    '''
    初始化函数，只运行一次
    context: 策略上下文对象
    '''
    # 设置股票池
    context.symbols = ['000001.SZ', '600519.SH', '000858.SZ']
    # 短期均线周期
    context.short_period = 5
    # 长期均线周期
    context.long_period = 20
    # 持仓数量
    context.hold_count = 2

def handle_data(context):
    '''
    每个交易日调用一次
    返回买入信号表达式和参数
    '''
    # 因子表达式：MA5 > MA20 作为买入信号
    signal = f"ma(close, {context.short_period}) > ma(close, {context.long_period})"

    return {
        'select_buy': [signal],  # 买入条件列表
        'select_sell': [],  # 卖出条件（空则持有）
        'order_by_signal': f'roc(close, {context.short_period})',  # 排序因子
        'order_by_topK': context.hold_count,  # 持仓数量
        'weight': 'WeighEqually',  # 等权重
        'period': 'RunDaily'  # 每日调仓
    }
""",

    "动量轮动策略": """# 动量轮动策略示例
def initialize(context):
    '''
    初始化函数
    '''
    # ETF池
    context.symbols = [
        '518880.SH',  # 黄金ETF
        '513100.SH',  # 纳指ETF
        '159915.SZ',  # 创业板ETF
        '512100.SH'   # 中证1000
    ]
    context.momentum_period = 20  # 动量周期
    context.hold_count = 2  # 持仓数量

def handle_data(context):
    '''
    动量评分：取最近N日涨幅最大的标的
    '''
    return {
        'select_buy': [],  # 不设条件，全选
        'select_sell': [],
        'order_by_signal': f'roc(close, {context.momentum_period})',  # 按动量排序
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunWeekly'  # 每周调仓
    }
""",

    "突破策略": """# 布林带突破策略
def initialize(context):
    '''
    初始化函数
    '''
    context.symbols = ['510300.SH', '159915.SZ']  # 沪深300、创业板
    context.boll_period = 20  # 布林带周期
    context.boll_std = 2  # 标准差倍数

def handle_data(context):
    '''
    价格突破上轨买入，跌破下轨卖出
    '''
    # 买入：收盘价 > 布林上轨
    buy_signal = f"close > boll(close, {context.boll_period}, {context.boll_std})[0]"

    # 卖出：收盘价 < 布林下轨
    sell_signal = f"close < boll(close, {context.boll_period}, {context.boll_std})[2]"

    return {
        'select_buy': [buy_signal],
        'select_sell': [sell_signal],
        'order_by_signal': '',  # 无排序，全持仓
        'order_by_topK': 0,
        'weight': 'WeighEqually',
        'period': 'RunDaily'
    }
""",

    "风险平价策略": """# 风险平价资产配置策略
def initialize(context):
    '''
    多资产配置策略
    '''
    context.symbols = [
        '159915.SZ',  # 股票：创业板ETF
        '518880.SH',  # 商品：黄金ETF
        '511010.SH',  # 债券：国债ETF
        '513100.SH'   # 海外：纳指ETF
    ]

def handle_data(context):
    '''
    使用风险平价算法分配权重
    '''
    return {
        'select_buy': [],
        'select_sell': [],
        'order_by_signal': '',
        'order_by_topK': 0,
        'weight': 'WeighERC',  # 风险平价加权
        'period': 'RunMonthly'  # 月度再平衡
    }
""",

    "多因子选股": """# 多因子选股策略
def initialize(context):
    '''
    基于多个技术因子选股
    '''
    # A股池（示例：创业板前100）
    context.symbols = ['300001.SZ', '300002.SZ', '300003.SZ']  # 实际可扩展
    context.hold_count = 5

def handle_data(context):
    '''
    多因子复合评分
    '''
    # 因子1：20日动量
    # 因子2：RSI超卖反弹
    # 因子3：MACD金叉

    buy_conditions = [
        "roc(close, 20) > 0",  # 正收益
        "rsi(close, 14) < 30",  # 超卖
        "macd(close, 12, 26, 9)[0] > macd(close, 12, 26, 9)[1]"  # MACD金叉
    ]

    return {
        'select_buy': buy_conditions,
        'buy_at_least_count': 2,  # 至少满足2个条件
        'select_sell': ["rsi(close, 14) > 70"],  # 超买卖出
        'order_by_signal': 'roc(close, 20)',  # 按动量排序
        'order_by_topK': context.hold_count,
        'weight': 'WeighEqually',
        'period': 'RunWeekly'
    }
"""
}


class StrategyContext:
    """策略上下文对象"""
    def __init__(self):
        self.symbols = []
        self.start_date = '20150101'
        self.end_date = datetime.now().strftime('%Y%m%d')
        self.benchmark = '000300.SH'
        self.initial_capital = 1000000


def execute_strategy_code(code_str, data_source='csv'):
    """
    执行用户策略代码并返回Task配置

    Args:
        code_str: 用户策略代码字符串
        data_source: 数据源类型

    Returns:
        tuple: (Task对象, 错误信息)
    """
    try:
        # 创建独立的命名空间
        namespace = {}

        # 执行用户代码
        exec(code_str, namespace)

        # 检查必要函数
        if 'initialize' not in namespace:
            return None, "错误：缺少 initialize() 函数"
        if 'handle_data' not in namespace:
            return None, "错误：缺少 handle_data() 函数"

        # 创建上下文
        context = StrategyContext()

        # 调用initialize
        namespace['initialize'](context)

        # 验证symbols
        if not context.symbols or len(context.symbols) == 0:
            return None, "错误：未设置股票池 (context.symbols)"

        # 调用handle_data获取策略参数
        strategy_params = namespace['handle_data'](context)

        # 验证返回值
        if not isinstance(strategy_params, dict):
            return None, "错误：handle_data() 必须返回字典类型"

        # 构建Task对象
        from bt_engine import Task

        task = Task()
        task.symbols = context.symbols
        task.start_date = context.start_date
        task.end_date = context.end_date
        task.benchmark = context.benchmark

        # 设置策略参数
        task.select_buy = strategy_params.get('select_buy', [])
        task.select_sell = strategy_params.get('select_sell', [])
        task.buy_at_least_count = strategy_params.get('buy_at_least_count', 0)
        task.sell_at_least_count = strategy_params.get('sell_at_least_count', 1)

        task.order_by_signal = strategy_params.get('order_by_signal', '')
        task.order_by_topK = strategy_params.get('order_by_topK', 1)
        task.order_by_dropN = strategy_params.get('order_by_dropN', 0)
        task.order_by_DESC = strategy_params.get('order_by_DESC', True)

        task.weight = strategy_params.get('weight', 'WeighEqually')
        task.weight_fixed = strategy_params.get('weight_fixed', {})
        task.period = strategy_params.get('period', 'RunDaily')
        task.period_days = strategy_params.get('period_days', None)

        return task, None

    except Exception as e:
        error_msg = f"代码执行错误：\n{traceback.format_exc()}"
        return None, error_msg


def run_backtest_with_task(task, data_source='csv', data_path=None):
    """
    运行回测

    Args:
        task: Task配置对象
        data_source: 数据源类型
        data_path: 数据路径

    Returns:
        tuple: (回测结果, 错误信息)
    """
    try:
        from bt_engine import Engine
        import os

        # 确定数据路径
        if data_path is None:
            if data_source == 'csv':
                # 使用本地数据
                home_dir = Path.home()
                data_path = home_dir / "stock_data"
            else:
                data_path = 'quotes'  # 其他数据源路径

        if not os.path.exists(data_path):
            return None, f"数据路径不存在: {data_path}"

        # 创建引擎并运行
        engine = Engine(path=str(data_path))

        # 设置手续费（万分之2.5）
        commissions = lambda q, p: max(5, abs(q) * p * 0.00025)

        result = engine.run(task, commissions=commissions)

        return result, None

    except Exception as e:
        error_msg = f"回测执行错误：\n{traceback.format_exc()}"
        return None, error_msg


def display_custom_strategy_editor():
    """显示自定义策略编辑器界面"""

    st.markdown("### 📝 自定义策略编辑器")
    st.markdown("---")

    # 使用说明折叠框
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 策略编写规范

        #### 1. 必须定义两个函数
        ```python
        def initialize(context):
            # 初始化：设置股票池、参数等
            context.symbols = ['股票代码1', '股票代码2']
            context.param1 = 值

        def handle_data(context):
            # 策略逻辑：返回交易信号和参数
            return {
                'select_buy': ['买入条件表达式'],
                'select_sell': ['卖出条件表达式'],
                'order_by_signal': '排序因子',
                'order_by_topK': 持仓数量,
                'weight': '加权方式',
                'period': '调仓周期'
            }
        ```

        #### 2. 股票代码格式
        - 上交所：`代码.SH` (如: `600519.SH`)
        - 深交所：`代码.SZ` (如: `000001.SZ`)

        #### 3. 常用因子表达式
        - 均线：`ma(close, 20)` - 20日均线
        - 动量：`roc(close, 20)` - 20日涨跌幅
        - RSI：`rsi(close, 14)` - 14日相对强弱指标
        - MACD：`macd(close, 12, 26, 9)` - 返回(DIF, DEA, MACD)
        - 布林带：`boll(close, 20, 2)` - 返回(上轨, 中轨, 下轨)
        - KDJ：`kdj(high, low, close, 9, 3, 3)` - 返回(K, D, J)

        #### 4. 加权方式
        - `WeighEqually` - 等权重
        - `WeighERC` - 风险平价
        - `WeighInvVol` - 波动率倒数加权
        - `WeighSpecified` - 指定权重（需提供weight_fixed）

        #### 5. 调仓周期
        - `RunDaily` - 每日
        - `RunWeekly` - 每周
        - `RunMonthly` - 每月
        - `RunQuarterly` - 每季度
        - `RunYearly` - 每年
        """)

    # 左右两列布局
    col1, col2 = st.columns([3, 1])

    with col2:
        st.markdown("#### 📚 策略模板")

        # 模板选择
        template_names = ["空白模板"] + list(STRATEGY_TEMPLATES.keys())
        selected_template = st.selectbox(
            "选择模板",
            template_names,
            key="template_selector"
        )

        # 加载模板按钮
        if st.button("📥 加载模板", use_container_width=True):
            if selected_template != "空白模板":
                st.session_state['strategy_code'] = STRATEGY_TEMPLATES[selected_template]
                st.success(f"✅ 已加载：{selected_template}")
                st.rerun()

        st.markdown("---")

        # 回测参数
        st.markdown("#### ⚙️ 回测参数")

        # 数据源选择
        data_source_options = {
            "💾 本地CSV": "csv",
            "🌐 Ashare实时": "ashare",
            "📊 Tushare": "tushare",
            "🔧 AKShare": "akshare"
        }

        data_source_label = st.selectbox(
            "数据源",
            list(data_source_options.keys()),
            key="data_source_selector"
        )
        data_source = data_source_options[data_source_label]

        # 时间范围
        default_start = datetime(2015, 1, 1)
        default_end = datetime.now()

        start_date = st.date_input(
            "开始日期",
            value=default_start,
            max_value=default_end,
            key="backtest_start_date"
        )

        end_date = st.date_input(
            "结束日期",
            value=default_end,
            max_value=datetime.now(),
            key="backtest_end_date"
        )

        # 基准指数
        benchmark = st.text_input(
            "基准指数",
            value="000300.SH",
            help="沪深300: 000300.SH, 上证50: 000016.SH, 创业板: 399006.SZ"
        )

        st.markdown("---")

        # 运行回测按钮
        run_backtest_btn = st.button(
            "🚀 运行回测",
            use_container_width=True,
            type="primary"
        )

    with col1:
        st.markdown("#### 💻 策略代码")

        # 初始化代码
        if 'strategy_code' not in st.session_state:
            st.session_state['strategy_code'] = STRATEGY_TEMPLATES["均线策略"]

        # 代码编辑器
        strategy_code = st.text_area(
            "Python代码",
            value=st.session_state['strategy_code'],
            height=500,
            key="code_editor",
            help="在此编写策略代码"
        )

        # 保存代码到session
        st.session_state['strategy_code'] = strategy_code

        # 代码验证按钮
        col_a, col_b, col_c = st.columns([1, 1, 2])
        with col_a:
            if st.button("✅ 验证代码", use_container_width=True):
                task, error = execute_strategy_code(strategy_code, data_source)
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.success("✅ 代码验证通过！")
                    with st.expander("📋 策略配置预览"):
                        st.json({
                            "股票池": task.symbols,
                            "买入条件": task.select_buy,
                            "卖出条件": task.select_sell,
                            "排序因子": task.order_by_signal,
                            "持仓数量": task.order_by_topK,
                            "加权方式": task.weight,
                            "调仓周期": task.period
                        })

        with col_b:
            if st.button("🗑️ 清空代码", use_container_width=True):
                st.session_state['strategy_code'] = ""
                st.rerun()

    # 运行回测
    if run_backtest_btn:
        st.markdown("---")
        st.markdown("### 📊 回测结果")

        with st.spinner("⏳ 正在执行回测..."):
            # 解析策略代码
            task, error = execute_strategy_code(strategy_code, data_source)

            if error:
                st.error(f"❌ 策略解析失败：\n{error}")
                return

            # 更新时间参数
            task.start_date = start_date.strftime('%Y%m%d')
            task.end_date = end_date.strftime('%Y%m%d')
            task.benchmark = benchmark

            # 执行回测
            if data_source == 'csv':
                data_path = Path.home() / "stock_data"
            else:
                # TODO: 支持其他数据源
                st.warning("⚠️ 当前仅支持本地CSV数据源，其他数据源开发中...")
                data_path = Path.home() / "stock_data"

            result, error = run_backtest_with_task(task, data_source, data_path)

            if error:
                st.error(f"❌ 回测失败：\n{error}")
                return

            # 显示结果
            display_backtest_results(result)


def display_backtest_results(result):
    """显示回测结果"""

    # 关键指标
    stats = result.stats

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = stats.loc['策略', 'total_return']
        st.metric("总收益率", f"{total_return:.2%}")

    with col2:
        cagr = stats.loc['策略', 'cagr']
        st.metric("年化收益率", f"{cagr:.2%}")

    with col3:
        max_dd = stats.loc['策略', 'max_drawdown']
        st.metric("最大回撤", f"{max_dd:.2%}")

    with col4:
        sharpe = stats.loc['策略', 'daily_sharpe']
        st.metric("夏普比率", f"{sharpe:.2f}")

    st.markdown("---")

    # 收益曲线图
    st.markdown("#### 📈 累计收益曲线")

    fig, ax = plt.subplots(figsize=(12, 6))
    result.plot(ax=ax)
    ax.set_xlabel("日期")
    ax.set_ylabel("累计收益")
    ax.legend(["策略", "基准"])
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close()

    # 详细统计表
    st.markdown("#### 📋 详细统计")

    # 格式化stats表格
    stats_display = stats.copy()
    stats_display = stats_display.round(4)
    st.dataframe(stats_display, use_container_width=True)

    # 交易记录
    st.markdown("#### 📝 交易记录")

    transactions = result.get_transactions()
    if not transactions.empty:
        st.dataframe(transactions, use_container_width=True)

        # 下载按钮
        csv = transactions.to_csv(index=True).encode('utf-8-sig')
        st.download_button(
            label="📥 下载交易记录",
            data=csv,
            file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("无交易记录")


if __name__ == "__main__":
    # 测试
    display_custom_strategy_editor()
