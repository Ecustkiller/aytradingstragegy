"""
AI Trader 集成模块
整合 AI Trader v3.3 的策略回测和数据管理功能
"""

import streamlit as st
import subprocess
import os
import sys
from pathlib import Path
import pandas as pd

# AI Trader 核心模块路径 (项目内置)
AITRADER_PATH = Path(__file__).parent.parent / "aitrader_core"

# 添加AI Trader路径到sys.path（用于导入模块）
if str(AITRADER_PATH) not in sys.path:
    sys.path.insert(0, str(AITRADER_PATH))


def check_aitrader_data():
    """检查AI Trader数据状态"""
    stock_data_dir = Path.home() / "stock_data"
    
    if stock_data_dir.exists():
        csv_files = list(stock_data_dir.glob("*.csv"))
        return len(csv_files), stock_data_dir
    return 0, stock_data_dir


def update_data_with_progress():
    """带进度显示的数据更新"""
    script_path = AITRADER_PATH / "update_daily_stock_data.py"
    
    if not script_path.exists():
        st.error(f"❌ 更新脚本不存在: {script_path}")
        return
    
    st.info("🔄 正在更新A股数据...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        process = subprocess.Popen(
            ['python3', str(script_path)],
            cwd=str(AITRADER_PATH),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        total_files = 5646  # 大约的股票数量
        current = 0
        
        for line in process.stdout:
            # 解析进度
            if '进度:' in line and '/' in line:
                try:
                    parts = line.split('进度:')[1].split('/')[0].strip()
                    current = int(parts)
                    progress = min(int((current / total_files) * 100), 99)
                    progress_bar.progress(progress)
                    status_text.text(f"已处理: {current}/{total_files} 只股票")
                except:
                    pass
            elif '数据更新完成' in line:
                progress_bar.progress(100)
                status_text.text("✅ 更新完成！")
        
        process.wait()
        
        if process.returncode == 0:
            st.success("✅ 数据更新成功！")
            st.balloons()
            
            # 重新检查数据
            stock_count, _ = check_aitrader_data()
            st.info(f"📊 当前数据量: {stock_count} 只股票")
        else:
            st.error(f"❌ 更新失败，返回码: {process.returncode}")
            
    except Exception as e:
        st.error(f"❌ 更新出错: {e}")
    finally:
        progress_bar.empty()
        status_text.empty()


def run_strategy_backtest(strategy_config):
    """
    直接运行策略回测并在界面显示结果
    strategy_config: 策略配置字典
    """
    import sys
    import matplotlib.pyplot as plt
    import io
    from PIL import Image
    
    # 添加AI Trader路径
    sys.path.insert(0, str(AITRADER_PATH))
    
    try:
        from bt_engine import Task, Engine
        import pandas as pd
        
        st.info(f"🚀 正在运行: {strategy_config['name']}")
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 步骤1: 加载数据
        status_text.text("📊 正在加载数据...")
        progress_bar.progress(20)
        
        # 步骤2: 配置策略
        status_text.text("⚙️ 正在配置策略...")
        progress_bar.progress(40)
        
        # 根据策略类型创建任务
        t = Task()
        
        if "V13" in strategy_config['name']:
            # V13策略配置
            t.name = 'V13动量轮动策略'
            t.start_date = '20150101'
            t.symbols = ['518880.SH', '513100.SH', '159915.SZ', '512100.SH']  # ✅ 修正：512100是上交所
            t.order_by_signal = 'momentum_score_v13(close,20)'
            t.order_by_topK = 1
            t.weight = 'WeighEqually'
            t.period = 'RunDaily'
            t.benchmark = '510300.SH'
            
        elif "聚宽年化" in strategy_config['name']:
            # 聚宽策略配置
            t.name = '聚宽年化收益评分'
            t.start_date = '20150101'
            t.symbols = ['159915.SZ', '510300.SH', '510500.SH', '159919.SZ']
            t.order_by_signal = 'momentum_score_jq(close,25)'
            t.order_by_topK = 2
            t.weight = 'WeighEqually'
            t.period = 'RunWeekly'
            t.benchmark = '510300.SH'
            
        elif "全天候" in strategy_config['name']:
            # 全天候风险平价策略配置
            t.name = '全天候风险平价策略'
            t.start_date = '20180101'
            t.symbols = [
                '159915.SZ',  # 创业板ETF (股票)
                '518880.SH',  # 黄金ETF (商品)
                '511010.SH',  # 国债ETF (债券)
                '513100.SH'   # 纳指ETF (外盘)
            ]
            t.buy_signal = None
            t.order_by_signal = None
            t.order_by_topK = None
            t.weight = 'WeighERC'  # 风险平价
            t.period = 'RunMonthly'
            t.benchmark = '510300.SH'
            
        elif "创业板择时" in strategy_config['name']:
            # 创业板择时策略配置
            t.name = '创业板择时策略'
            t.start_date = '20150101'
            t.symbols = ['159915.SZ']  # 创业板ETF
            t.buy_signal = 'roc(close,20)>0'
            t.order_by_signal = None
            t.order_by_topK = None
            t.weight = 'WeighEqually'
            t.period = 'RunDaily'
            t.benchmark = '510300.SH'
            
        elif "个股" in strategy_config['name']:
            # 个股测试配置
            t.name = '个股动量轮动'
            t.start_date = '20240101'
            # 随机选择20只股票
            import random
            stock_data_dir = Path.home() / "stock_data"
            if stock_data_dir.exists():
                csv_files = list(stock_data_dir.glob("*.csv"))
                if len(csv_files) > 20:
                    random.seed(42)
                    selected = random.sample(csv_files, 20)
                    t.symbols = [f.stem.split('_')[0] + ('.SH' if f.stem.startswith('6') else '.SZ') for f in selected]
            t.order_by_signal = 'momentum_score_jq(close,25)'
            t.order_by_topK = 5
            t.weight = 'WeighEqually'
            t.period = 'RunWeekly'
            t.benchmark = '510300.SH'
        
        else:
            st.error(f"❌ 未找到策略 '{strategy_config['name']}' 的配置")
            return False
            
        # 步骤3: 运行回测
        status_text.text("🔄 正在回测...")
        progress_bar.progress(60)
        
        # 选择数据路径
        if "个股" in strategy_config['name']:
            engine = Engine(path=str(Path.home() / "stock_data"))
        else:
            engine = Engine()
        
        result = engine.run(t)
        
        progress_bar.progress(80)
        status_text.text("📈 正在生成图表...")
        
        # 步骤4: 显示结果
        progress_bar.progress(100)
        status_text.text("✅ 回测完成！")
        
        st.success(f"✅ {strategy_config['name']} 回测完成！")
        
        # 显示业绩统计
        st.subheader("📊 回测结果")
        
        stats = result.stats
        strategy_col = stats.columns[0]
        benchmark_col = stats.columns[1] if len(stats.columns) > 1 else None
        
        # 关键指标卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_return = stats.loc['total_return', strategy_col]
            st.metric("总收益率", f"{total_return:.2%}")
        
        with col2:
            cagr = stats.loc['cagr', strategy_col]
            st.metric("年化收益", f"{cagr:.2%}")
        
        with col3:
            max_dd = stats.loc['max_drawdown', strategy_col]
            st.metric("最大回撤", f"{max_dd:.2%}")
        
        with col4:
            sharpe = stats.loc['daily_sharpe', strategy_col]
            st.metric("夏普比率", f"{sharpe:.2f}")
        
        # 详细统计表
        with st.expander("📋 查看详细统计", expanded=False):
            st.dataframe(stats, use_container_width=True)
        
        # 绘制图表
        st.subheader("📈 收益曲线")
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # 累计收益曲线
        result.prices.plot(ax=ax1, linewidth=2)
        ax1.set_title('累计收益曲线', fontsize=14, fontweight='bold')
        ax1.set_xlabel('日期', fontsize=12)
        ax1.set_ylabel('净值', fontsize=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 回撤曲线
        drawdown = result.prices / result.prices.cummax() - 1
        drawdown.plot(ax=ax2, linewidth=2)
        ax2.set_title('回撤曲线', fontsize=14, fontweight='bold')
        ax2.set_xlabel('日期', fontsize=12)
        ax2.set_ylabel('回撤', fontsize=12)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        
        plt.tight_layout()
        
        # 在Streamlit中显示图表
        st.pyplot(fig)
        
        # 清理
        plt.close(fig)
        progress_bar.empty()
        status_text.empty()
        
        return True
        
    except Exception as e:
        st.error(f"❌ 回测失败: {str(e)}")
        import traceback
        with st.expander("查看错误详情"):
            st.code(traceback.format_exc())
        return False


def display_aitrader_backtest():
    """显示AI Trader策略回测界面"""
    st.header("📈 策略回测")
    
    # 数据源选择 - 按钮组
    st.markdown("### 📡 数据源选择")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 初始化session_state中的数据源
    if 'selected_data_source' not in st.session_state:
        st.session_state.selected_data_source = '本地CSV'
    
    with col1:
        if st.button("💾 本地CSV\n(Baostock)", use_container_width=True, 
                    type="primary" if st.session_state.selected_data_source == '本地CSV' else "secondary"):
            st.session_state.selected_data_source = '本地CSV'
    
    with col2:
        if st.button("🌐 实时数据\n(Ashare)", use_container_width=True,
                    type="primary" if st.session_state.selected_data_source == 'Ashare' else "secondary"):
            st.session_state.selected_data_source = 'Ashare'
    
    with col3:
        if st.button("📊 Tushare\n(专业版)", use_container_width=True,
                    type="primary" if st.session_state.selected_data_source == 'Tushare' else "secondary"):
            st.session_state.selected_data_source = 'Tushare'
    
    with col4:
        if st.button("🔧 AKShare\n(在线)", use_container_width=True,
                    type="primary" if st.session_state.selected_data_source == 'AKShare' else "secondary"):
            st.session_state.selected_data_source = 'AKShare'
    
    # 显示当前选择的数据源
    data_source_emoji = {
        '本地CSV': '💾',
        'Ashare': '🌐',
        'Tushare': '📊',
        'AKShare': '🔧'
    }
    
    data_source_desc = {
        '本地CSV': '使用已下载的历史数据 (快速稳定)',
        'Ashare': '实时获取最新数据 (推荐)',
        'Tushare': '专业金融数据源 (高质量,积分制)',
        'AKShare': '开源在线数据 (免费,实时)'
    }
    
    st.info(f"{data_source_emoji[st.session_state.selected_data_source]} **{st.session_state.selected_data_source}**: {data_source_desc[st.session_state.selected_data_source]}")
    
    st.divider()
    
    # 策略配置字典
    STRATEGY_CONFIGS = {
        "V13动量轮动策略": {
            "desc": "4只ETF动量轮动 | 20日动量评分 | 双阈值超买识别",
            "symbols": ['518880.SH', '513100.SH', '159915.SZ', '512100.SH'],
            "order_by_signal": 'momentum_score_v13(close,20)',
            "order_by_topK": 1,
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "聚宽年化收益评分轮动": {
            "desc": "4只ETF轮动 | 25日动量 × R² | 周度调仓",
            "symbols": ['159915.SZ', '510300.SH', '510500.SH', '159919.SZ'],
            "order_by_signal": 'momentum_score_jq(close,25)',
            "order_by_topK": 2,
            "weight": 'WeighEqually',
            "period": 'RunWeekly',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "全天候风险平价策略": {
            "desc": "多资产配置 | 风险平价加权 | 月度再平衡",
            "symbols": ['159915.SZ', '518880.SH', '511010.SH', '513100.SH'],
            "order_by_signal": None,
            "order_by_topK": None,
            "weight": 'WeighERC',
            "period": 'RunMonthly',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "创业板择时策略": {
            "desc": "单标的择时 | ROC信号 | 日线交易",
            "symbols": ['159915.SZ'],
            "buy_signal": 'roc(close,20)>0',
            "order_by_signal": None,
            "order_by_topK": None,
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "创业板布林带策略": {
            "desc": "布林带突破 | 上轨买入下轨卖出 | 日线交易",
            "symbols": ['159915.SZ'],
            "select_buy": ['close>bbands_up(close,20,2)'],
            "select_sell": ['close<bbands_down(close,20,2)'],
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '159915.SZ',
            "data_type": "etf"
        },
        "上证50双均线策略": {
            "desc": "双均线择时 | MA20>MA120做多 | 日线交易",
            "symbols": ['510050.SH'],
            "select_buy": ['ma(close,20)>ma(close,120)'],
            "select_sell": ['ma(close,20)<ma(close,120)'],
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '510050.SH',
            "data_type": "etf"
        },
        "沪深300RSRS择时": {
            "desc": "RSRS择时 | 阻力支撑相对强度 | 日线交易",
            "symbols": ['159915.SZ'],
            "select_buy": ['RSRS(high,low,18)>1.0'],
            "select_sell": ['RSRS(high,low,18)<0.8'],
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "大小盘轮动策略": {
            "desc": "创业板vs沪深300 | ROC动量轮动 | 日线交易",
            "symbols": ['159915.SZ', '510300.SH'],
            "select_buy": ['roc(close,20)>0.02'],
            "select_sell": ['roc(close,20)<-0.02'],
            "order_by_signal": 'roc(close,20)',
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "优质资产动量轮动": {
            "desc": "7资产轮动 | 医药黄金纳指等 | 日线交易",
            "symbols": ['511220.SH', '512010.SH', '518880.SH', '163415.SZ', '159928.SZ', '161903.SZ', '513100.SH'],
            "select_buy": ['roc(close,20)>0.02'],
            "select_sell": ['roc(close,20)<-0.02'],
            "order_by_signal": 'roc(close,20)',
            "order_by_topK": 7,
            "weight": 'WeighEqually',
            "period": 'RunDaily',
            "benchmark": '510300.SH',
            "data_type": "etf"
        },
        "个股动量轮动策略": {
            "desc": "随机20只A股 | 持仓前5 | 周度调仓",
            "symbols": None,  # 动态生成
            "order_by_signal": 'momentum_score_jq(close,25)',
            "order_by_topK": 5,
            "weight": 'WeighEqually',
            "period": 'RunWeekly',
            "benchmark": '510300.SH',
            "data_type": "stock"
        }
    }
    
    # 简洁的主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 策略选择
        selected_strategy = st.selectbox(
            "📊 选择策略",
            options=list(STRATEGY_CONFIGS.keys()),
            help="选择要回测的策略"
        )
        
        # 显示策略描述
        strategy_info = STRATEGY_CONFIGS[selected_strategy]
        st.caption(f"💡 {strategy_info['desc']}")
    
    with col2:
        # 数据状态
        stock_count, _ = check_aitrader_data()
        st.metric("📊 数据库", f"{stock_count} 只")
    
    # 回测参数
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input(
            "开始日期",
            value=pd.to_datetime("2015-01-01"),
            help="回测开始日期"
        )
    
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=pd.to_datetime("today"),
            help="回测结束日期"
        )
    
    with col3:
        st.write("")  # 占位
        st.write("")  # 占位
        run_backtest = st.button("🚀 开始回测", type="primary", use_container_width=True)
    
    st.divider()
    
    # 运行回测
    if run_backtest:
        try:
            from bt_engine import Task, Engine
            import matplotlib.pyplot as plt
            
            st.info(f"🚀 正在回测: {selected_strategy}")
            
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 配置Task
            t = Task()
            t.name = selected_strategy
            t.start_date = start_date.strftime('%Y%m%d')
            t.end_date = end_date.strftime('%Y%m%d')
            
            # 根据策略配置参数
            config = strategy_info
            t.symbols = config['symbols']
            t.order_by_signal = config.get('order_by_signal')
            t.order_by_topK = config.get('order_by_topK')
            t.weight = config['weight']
            t.period = config['period']
            t.benchmark = config['benchmark']
            
            # 如果有buy_signal
            if 'buy_signal' in config and config['buy_signal']:
                t.buy_signal = config['buy_signal']
            
            # 如果有select_buy和select_sell
            if 'select_buy' in config and config['select_buy']:
                t.select_buy = config['select_buy']
            if 'select_sell' in config and config['select_sell']:
                t.select_sell = config['select_sell']
            
            # 个股策略动态生成股票池
            if config['data_type'] == 'stock':
                import random
                stock_data_dir = Path.home() / "stock_data"
                if stock_data_dir.exists():
                    csv_files = list(stock_data_dir.glob("*.csv"))
                    if len(csv_files) > 20:
                        random.seed(42)
                        selected = random.sample(csv_files, 20)
                        t.symbols = [f.stem.split('_')[0] + ('.SH' if f.stem.startswith('6') else '.SZ') for f in selected]
            
            status_text.text("📊 正在加载数据...")
            progress_bar.progress(20)
            
            # 选择数据路径
            if config['data_type'] == 'stock':
                engine = Engine(path=str(Path.home() / "stock_data"))
            else:
                engine = Engine()  # ETF用项目data/quotes
            
            status_text.text("🔄 正在运行回测...")
            progress_bar.progress(50)
            
            # 运行回测
            result = engine.run(t)
            
            status_text.text("📈 正在生成图表...")
            progress_bar.progress(80)
            
            # 显示结果
            progress_bar.progress(100)
            status_text.text("✅ 回测完成！")
            
            st.success(f"✅ {selected_strategy} 回测完成！")
            
            # 显示业绩指标
            st.subheader("📊 回测结果")
            
            stats = result.stats
            strategy_col = stats.columns[0]
            
            # 关键指标
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_return = stats.loc['total_return', strategy_col]
                st.metric("总收益率", f"{total_return:.2%}")
            
            with col2:
                cagr = stats.loc['cagr', strategy_col]
                st.metric("年化收益", f"{cagr:.2%}")
            
            with col3:
                max_dd = stats.loc['max_drawdown', strategy_col]
                st.metric("最大回撤", f"{max_dd:.2%}")
            
            with col4:
                sharpe = stats.loc['daily_sharpe', strategy_col]
                st.metric("夏普比率", f"{sharpe:.2f}")
            
            # 详细统计
            with st.expander("📋 查看详细统计", expanded=False):
                st.dataframe(stats, use_container_width=True)
            
            # 图表
            st.subheader("📈 收益曲线")
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['STHeiti', 'Arial Unicode MS', 'Songti SC', 'SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 累计收益
            ax1.plot(result.prices.index, result.prices[strategy_col], label='策略', linewidth=2, color='#1f77b4')
            if len(result.prices.columns) > 1:
                ax1.plot(result.prices.index, result.prices.iloc[:, 1], label='基准', linewidth=2, color='#ff7f0e', alpha=0.7)
            ax1.set_title('累计收益曲线', fontsize=14, pad=10)
            ax1.set_xlabel('日期')
            ax1.set_ylabel('累计收益')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 回撤
            if hasattr(result, 'get_transactions'):
                drawdown = (result.prices[strategy_col] / result.prices[strategy_col].cummax() - 1)
                ax2.fill_between(drawdown.index, 0, drawdown * 100, color='#d62728', alpha=0.3)
                ax2.plot(drawdown.index, drawdown * 100, color='#d62728', linewidth=1.5)
                ax2.set_title('回撤曲线', fontsize=14, pad=10)
                ax2.set_xlabel('日期')
                ax2.set_ylabel('回撤 (%)')
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            
            # 交易记录
            st.subheader("📝 交易记录")
            
            if hasattr(result, 'get_transactions'):
                try:
                    transactions = result.get_transactions()
                    if not transactions.empty:
                        st.dataframe(transactions.tail(20), use_container_width=True)
                        
                        # 导出按钮
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            csv_data = transactions.to_csv(index=True).encode('utf-8-sig')
                            st.download_button(
                                label="📥 下载完整交易记录",
                                data=csv_data,
                                file_name=f"{selected_strategy}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_交易记录.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.info("暂无交易记录")
                except Exception as e:
                    st.warning(f"无法获取交易记录: {str(e)}")
            
            progress_bar.empty()
            status_text.empty()
            
            # 保存到session_state用于对比
            if 'backtest_results' not in st.session_state:
                st.session_state.backtest_results = {}
            
            st.session_state.backtest_results[selected_strategy] = {
                'stats': stats,
                'prices': result.prices,
                'date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            st.error(f"❌ 回测失败: {str(e)}")
            import traceback
            with st.expander("查看错误详情"):
                st.code(traceback.format_exc())
    
    # 策略对比功能
    st.divider()
    
    if 'backtest_results' in st.session_state and len(st.session_state.backtest_results) > 1:
        st.subheader("📊 多策略对比")
        
        # 创建对比表格
        compare_data = []
        for strategy_name, result_data in st.session_state.backtest_results.items():
            stats = result_data['stats']
            strategy_col = stats.columns[0]
            
            compare_data.append({
                '策略名称': strategy_name,
                '总收益率': f"{stats.loc['total_return', strategy_col]:.2%}",
                '年化收益': f"{stats.loc['cagr', strategy_col]:.2%}",
                '最大回撤': f"{stats.loc['max_drawdown', strategy_col]:.2%}",
                '夏普比率': f"{stats.loc['daily_sharpe', strategy_col]:.2f}",
                '回测时间': result_data['date']
            })
        
        compare_df = pd.DataFrame(compare_data)
        st.dataframe(compare_df, use_container_width=True, hide_index=True)
        
        # 收益曲线对比
        with st.expander("📈 收益曲线对比", expanded=False):
            fig, ax = plt.subplots(figsize=(12, 6))
            
            for strategy_name, result_data in st.session_state.backtest_results.items():
                prices = result_data['prices']
                strategy_col = prices.columns[0]
                # 归一化为相对收益
                normalized = (prices[strategy_col] / prices[strategy_col].iloc[0] - 1) * 100
                ax.plot(normalized.index, normalized, label=strategy_name, linewidth=2)
            
            ax.set_title('多策略收益对比 (%)', fontsize=14, pad=10)
            ax.set_xlabel('日期')
            ax.set_ylabel('收益率 (%)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        
        # 清除历史记录按钮
        if st.button("🗑️ 清除对比记录"):
            st.session_state.backtest_results = {}
            st.rerun()
    
    # 实时信号和使用说明
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚡ 实时交易信号")
        if st.button("📡 获取V13实时信号", use_container_width=True):
            script_path = "V13策略_修正公式_实时信号.py"
            if (AITRADER_PATH / script_path).exists():
                run_aitrader_script(script_path, "V13策略实时信号")
    
    with col2:
        st.markdown("### 🔧 数据更新")
        if st.button("🔄 更新ETF数据", use_container_width=True):
            run_aitrader_script("update_etf_data.py", "更新ETF数据")
    
    # 使用说明
    with st.expander("💡 使用说明"):
        st.markdown("""
        ### 📖 回测说明
        
        1. **选择策略**: 从下拉框选择要回测的策略
        2. **设置日期**: 选择回测的开始和结束日期
        3. **开始回测**: 点击"🚀 开始回测"按钮
        4. **查看结果**: 回测完成后查看收益曲线和统计指标
        
        ### 📊 数据说明
        
        - **ETF策略**: 使用项目内`data/quotes`目录数据
        - **个股策略**: 使用`~/stock_data`目录数据
        - **数据更新**: 使用Ashare实时数据源
        
        ### 💡 策略添加
        
        如需添加新策略，请修改`aitrader_integration.py`中的`STRATEGY_CONFIGS`字典
        """)


def display_aitrader_data_management():
    """显示AI Trader数据管理界面"""
    st.header("📊 AI Trader 数据管理中心")
    
    stock_count, data_dir = check_aitrader_data()
    
    # 数据状态概览
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📁 股票数量", f"{stock_count} 只")
    
    with col2:
        if stock_count > 0:
            st.metric("✅ 数据状态", "正常")
        else:
            st.metric("⚠️ 数据状态", "无数据")
    
    with col3:
        st.metric("📂 数据目录", "~/stock_data")
    
    st.divider()
    
    # 数据操作
    st.subheader("🔧 数据操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔄 更新全量数据")
        st.caption("增量更新所有A股数据到最新交易日")
        
        if st.button("开始更新", use_container_width=True, type="primary"):
            # 运行数据更新
            update_data_with_progress()
        
        st.info("""
        **更新说明:**
        - 首次运行约13分钟
        - 日常增量更新约2-3分钟
        - 自动跳过停牌股票
        - 支持断点续传
        """)
    
    with col2:
        st.markdown("### 📊 数据统计")
        st.caption("数据库详细信息")
        
        if stock_count > 0:
            st.success(f"✅ 已下载 {stock_count} 只股票数据")
            st.caption(f"数据路径: `{data_dir}`")
            
            # 尝试获取最新更新时间
            try:
                log_file = AITRADER_PATH / "logs" / "update_20251028.log"
                if log_file.exists():
                    import time
                    mtime = os.path.getmtime(log_file)
                    update_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                    st.info(f"📅 最近更新: {update_time}")
            except:
                pass
        else:
            st.warning("⚠️ 未检测到数据")
            st.caption("请点击左侧'开始更新'按钮")
    
    st.divider()
    
    # 数据说明
    st.subheader("💡 数据说明")
    
    tab1, tab2, tab3 = st.tabs(["数据源", "数据格式", "使用场景"])
    
    with tab1:
        st.markdown("""
        ### 📡 数据源: Baostock
        
        - **免费开源**: 无需注册，完全免费
        - **数据全面**: 覆盖沪深A股全市场
        - **质量可靠**: 包含复权、除权等处理
        - **更新及时**: 每日收盘后可获取最新数据
        
        **包含字段:**
        - 日期、开盘价、最高价、最低价、收盘价
        - 成交量、成交额
        - 涨跌幅、换手率等
        """)
    
    with tab2:
        st.markdown("""
        ### 📝 数据格式
        
        **文件命名:** `股票代码_股票名.csv`
        
        例如:
        - `000001_平安银行.csv`
        - `600519_贵州茅台.csv`
        
        **CSV结构:**
        ```csv
        date,open,high,low,close,volume,amount,...
        2024-01-01,12.34,12.56,12.30,12.45,1000000,12450000,...
        ```
        
        **数据清洗:**
        - ✅ 自动去除NaN值
        - ✅ 日期格式标准化
        - ✅ 数值类型转换
        - ✅ 排除ST股票（可选）
        """)
    
    with tab3:
        st.markdown("""
        ### 🎯 使用场景
        
        1. **策略回测**
           - ETF策略回测
           - 个股策略回测
           - 组合优化回测
        
        2. **因子研究**
           - 技术因子计算
           - 基本面因子分析
           - 多因子模型构建
        
        3. **选股筛选**
           - 动量选股
           - 价值选股
           - 成长选股
        
        4. **风险分析**
           - 波动率计算
           - 相关性分析
           - 风险度量
        """)

