"""
Z哥战法选股机器人
提供友好的Web界面进行策略选股
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from .zgzf_selector import STRATEGY_MAP, run_zgzf_selector, batch_select_stocks
from .data_loader import get_stock_data

def display_zgzf_strategy():
    """显示Z哥战法选股界面"""
    st.title("🎯 Z哥战法选股")
    
    st.markdown("""
    ### 📚 策略简介
    
    集成5个经典的"Z哥战法"选股策略：
    
    | 策略 | 核心逻辑 | 适用场景 |
    |------|---------|---------|
    | **少妇战法** | BBI + KDJ金叉 | 趋势确认后的买入时机 |
    | **SuperB1战法** | 均线支撑 + 放量 | 回调到均线附近的反弹机会 |
    | **补票战法** | BBI向上 + 缩量回调 | 错过上涨后的补仓时机 |
    | **填坑战法** | 波峰回调 + KDJ底部金叉 | 高位回调后的低吸机会 |
    | **上穿60放量** | 突破MA60 + 放量 | 中长期趋势反转信号 |
    
    """)
    
    st.markdown("---")
    
    # 策略选择
    st.subheader("🎨 策略配置")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        strategy_name = st.selectbox(
            "选择策略",
            list(STRATEGY_MAP.keys()),
            help="选择一个策略进行选股分析"
        )
    
    with col2:
        mode = st.radio(
            "运行模式",
            ["单股分析", "批量选股"],
            horizontal=True
        )
    
    # 策略参数配置
    st.markdown("##### ⚙️ 参数设置")
    config = {}
    
    if strategy_name == "少妇战法":
        col1, col2, col3 = st.columns(3)
        with col1:
            config['window_kdj'] = st.number_input("KDJ周期", min_value=5, max_value=30, value=9)
        with col2:
            config['check_zhixing'] = st.checkbox("启用知行约束", value=False)
        with col3:
            if config['check_zhixing']:
                config['is_shortterm'] = st.checkbox("短线模式(MA5>MA10>MA20)", value=True)
    
    elif strategy_name == "SuperB1战法":
        col1, col2 = st.columns(2)
        with col1:
            config['volume_ratio'] = st.number_input("量比阈值", min_value=1.0, max_value=3.0, value=1.2, step=0.1)
        with col2:
            config['max_pct_change'] = st.number_input("最大涨幅%", min_value=1.0, max_value=10.0, value=5.0, step=0.5)
    
    elif strategy_name == "补票战法":
        col1, col2, col3 = st.columns(3)
        with col1:
            config['bbi_range_lower'] = st.number_input("BBI下限", min_value=0.90, max_value=1.0, value=0.98, step=0.01)
        with col2:
            config['bbi_range_upper'] = st.number_input("BBI上限", min_value=1.0, max_value=1.10, value=1.02, step=0.01)
        with col3:
            config['volume_shrink'] = st.checkbox("要求缩量", value=True)
    
    elif strategy_name == "填坑战法":
        col1, col2, col3 = st.columns(3)
        with col1:
            config['lookback'] = st.number_input("回溯天数", min_value=30, max_value=120, value=60)
        with col2:
            config['retracement_pct'] = st.number_input("回调比例", min_value=0.80, max_value=0.99, value=0.95, step=0.01)
        with col3:
            config['kdj_low'] = st.number_input("KDJ上限", min_value=10, max_value=50, value=30)
    
    elif strategy_name == "上穿60放量战法":
        col1, col2 = st.columns(2)
        with col1:
            config['volume_ratio'] = st.number_input("量比阈值", min_value=1.0, max_value=5.0, value=1.5, step=0.1)
        with col2:
            config['max_pct_change'] = st.number_input("最大涨幅%", min_value=1.0, max_value=10.0, value=7.0, step=0.5)
    
    st.markdown("---")
    
    # 单股分析模式
    if mode == "单股分析":
        st.subheader("📊 单股分析")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbol = st.text_input("股票代码", value="600519", help="输入6位股票代码")
        
        with col2:
            data_source = st.selectbox("数据源", ["AKShare", "Tushare", "Ashare"])
        
        with col3:
            days = st.number_input("分析天数", min_value=60, max_value=500, value=250)
        
        if st.button("🔍 开始分析", type="primary", use_container_width=True):
            with st.spinner(f"正在获取 {symbol} 的数据..."):
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # 获取数据
                df = get_stock_data(
                    symbol=symbol,
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    data_source=data_source,
                    period_type='daily'
                )
                
                if df is None or df.empty:
                    st.error(f"❌ 无法获取 {symbol} 的数据")
                    return
                
                st.success(f"✅ 获取到 {len(df)} 条数据")
                
                # 运行策略
                passed, reason = run_zgzf_selector(df, strategy_name, config)
                
                # 显示结果
                st.markdown("---")
                st.subheader("📈 分析结果")
                
                if passed:
                    st.success(f"✅ **{symbol}** 符合 **{strategy_name}** 条件！")
                    st.info(reason)
                else:
                    st.warning(f"❌ **{symbol}** 不符合 **{strategy_name}** 条件")
                    st.info(f"原因: {reason}")
                
                # 显示最新数据
                col1, col2, col3, col4 = st.columns(4)
                latest = df.iloc[-1]
                
                with col1:
                    st.metric("最新价", f"{latest['Close']:.2f}")
                
                with col2:
                    pct_change = (latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100
                    st.metric("涨跌幅", f"{pct_change:.2f}%")
                
                with col3:
                    st.metric("成交量", f"{latest['Volume']/10000:.0f}万")
                
                with col4:
                    if 'MA60' in df.columns:
                        st.metric("MA60", f"{latest['MA60']:.2f}")
                
                # 显示数据预览
                st.markdown("---")
                st.subheader("📋 最近10日数据")
                display_cols = ['Close', 'Volume']
                if 'MA5' in df.columns:
                    display_cols.extend(['MA5', 'MA10', 'MA20'])
                if 'K' in df.columns:
                    display_cols.extend(['K', 'D', 'J'])
                if 'BBI' in df.columns:
                    display_cols.append('BBI')
                
                available_cols = [col for col in display_cols if col in df.columns]
                st.dataframe(df[available_cols].tail(10), use_container_width=True)
    
    # 批量选股模式
    else:
        st.subheader("🔍 批量选股")
        st.warning("⚠️ 批量选股功能需要预先下载股票池数据，暂未实现数据管理模块")
        st.info("""
        **使用说明**：
        1. 在"AI数据管理"模块中下载A股全量数据
        2. 或使用原项目的 `fetch_kline.py` 脚本下载数据
        3. 将数据文件放置在 `./data/` 目录
        4. 返回此处进行批量选股
        
        **后续版本将集成数据管理功能**
        """)


if __name__ == "__main__":
    display_zgzf_strategy()

