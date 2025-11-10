"""
A股估值分析模块 - 巴菲特指标
总市值/GDP比率，用于宏观择时判断
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 尝试导入AKShare
try:
    import akshare as ak
    HAS_AKSHARE = True
    AKSHARE_ERROR = None
except ImportError as e:
    HAS_AKSHARE = False
    AKSHARE_ERROR = str(e)

def get_buffett_index():
    """通过AKShare获取实时巴菲特指标数据"""
    if not HAS_AKSHARE:
        return None
    
    try:
        df = ak.stock_buffett_index_lg()
        # 数据清洗与格式转换
        latest_data = df.iloc[-1].to_dict()  # 取最新一条数据
        return {
            'date': pd.to_datetime(latest_data['日期']).strftime('%Y-%m-%d'),
            'total_market': round(latest_data['总市值'] / 1e4, 2),  # 转换为万亿元
            'gdp': round(latest_data['GDP'] / 1e4, 2),  # 转换为万亿元
            'ratio': round(latest_data['总市值'] / latest_data['GDP'] * 100, 1),
            'decade_percentile': latest_data['近十年分位数'],
            'history_percentile': latest_data['总历史分位数']
        }
    except Exception as e:
        st.error(f"获取巴菲特指标数据失败: {e}")
        return None

def get_sh_index(days=200):
    """获取上证指数历史数据（含最新交易日）"""
    if not HAS_AKSHARE:
        return None
    
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        return df[['date', 'open', 'high', 'low', 'close', 'volume']].tail(days)
    except Exception as e:
        st.error(f"获取上证指数数据失败: {e}")
        return None

def get_position_suggestion(ratio):
    """根据巴菲特指标给出仓位建议"""
    if ratio < 60:
        return "100%", "极度低估", "success", "🔥"
    elif 60 <= ratio < 70:
        return "80%-100%", "价值区间", "success", "✅"
    elif 70 <= ratio < 80:
        position = 100 - (ratio - 70) * 10  # 线性递减
        return f"{position:.0f}%", "合理区间", "warning", "⚠️"
    elif 80 <= ratio < 100:
        return "<30%", "高估区域", "error", "⚠️"
    else:
        return "<10%", "极度高估", "error", "🚨"

def display_buffett_indicator():
    """显示巴菲特指标分析主界面"""
    st.title("💰 A股估值分析 - 巴菲特指标")
    
    st.markdown("""
    ### 功能说明
    **巴菲特指标** = 股市总市值 / GDP × 100%
    
    这是沃伦·巴菲特推崇的宏观择时指标，用于判断整体市场的估值水平。
    
    **指标含义**：
    - **< 60%**：极度低估，历史性机会
    - **60-70%**：价值区间，适合建仓
    - **70-80%**：合理区间，逐步减仓
    - **80-100%**：高估区域，谨慎操作
    - **> 100%**：极度高估，风险巨大
    """)
    
    # 检查依赖
    if not HAS_AKSHARE:
        st.error("❌ AKShare库未安装或不可用")
        st.info(f"错误详情: {AKSHARE_ERROR}")
        st.code("pip install akshare", language="bash")
        return
    
    st.markdown("---")
    
    # 获取数据
    with st.spinner("正在获取最新数据..."):
        current_data = get_buffett_index()
        sh_index_data = get_sh_index(days=200)
    
    if current_data is None:
        st.error("❌ 无法获取巴菲特指标数据")
        return
    
    # 显示核心指标
    st.subheader(f"📅 {current_data['date']} 最新数据")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "巴菲特指标",
            f"{current_data['ratio']}%",
            help="总市值/GDP比率"
        )
    
    with col2:
        st.metric(
            "总市值",
            f"{current_data['total_market']} 万亿",
            help="A股市场总市值"
        )
    
    with col3:
        st.metric(
            "GDP总量",
            f"{current_data['gdp']} 万亿",
            help="国内生产总值"
        )
    
    with col4:
        st.metric(
            "历史分位数",
            f"{current_data['history_percentile']*100:.1f}%",
            help="当前指标在历史中的位置"
        )
    
    st.markdown("---")
    
    # 仓位建议
    st.subheader("🎯 智能仓位建议")
    
    position, status, color, icon = get_position_suggestion(current_data['ratio'])
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 动态进度条（根据历史分位数）
        progress_value = current_data['history_percentile']
        st.progress(
            progress_value,
            text=f"历史分位数：{progress_value*100:.1f}%"
        )
    
    with col2:
        if color == "success":
            st.success(f"{icon} {status}")
        elif color == "warning":
            st.warning(f"{icon} {status}")
        else:
            st.error(f"{icon} {status}")
    
    # 仓位建议卡片
    st.info(f"""
    ### 💡 建议仓位: **{position}**
    
    **投资策略**：
    - 当前市场估值处于 **{status}**
    - 历史分位数为 **{current_data['history_percentile']*100:.1f}%**
    - 建议股票仓位保持在 **{position}**
    """)
    
    st.markdown("---")
    
    # 上证指数K线图
    if sh_index_data is not None and not sh_index_data.empty:
        st.subheader("📈 上证指数走势（近200个交易日）")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=('K线图', '成交量')
        )
        
        # K线图
        fig.add_trace(
            go.Candlestick(
                x=sh_index_data['date'],
                open=sh_index_data['open'],
                high=sh_index_data['high'],
                low=sh_index_data['low'],
                close=sh_index_data['close'],
                increasing_line_color='red',
                decreasing_line_color='green',
                name='上证指数'
            ),
            row=1, col=1
        )
        
        # 成交量
        colors = ['red' if close >= open else 'green' 
                 for close, open in zip(sh_index_data['close'], sh_index_data['open'])]
        
        fig.add_trace(
            go.Bar(
                x=sh_index_data['date'],
                y=sh_index_data['volume'],
                name='成交量',
                marker_color=colors,
                opacity=0.5
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title='上证指数实时K线图',
            xaxis_rangeslider_visible=False,
            height=600,
            showlegend=False
        )
        
        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="点位", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 历史数据说明
    with st.expander("📚 历史参考数据"):
        st.markdown("""
        ### 历史重要节点
        
        | 时期 | 巴菲特指标 | 市场状态 |
        |------|-----------|---------|
        | 2005年 | ~30% | 历史大底，千载难逢 |
        | 2008年底 | ~50% | 金融危机底部 |
        | 2014年 | ~60% | 慢牛起点 |
        | 2015年中 | >120% | 疯牛顶部 |
        | 2018年底 | ~60% | 熊市底部 |
        | 2019-2020 | 70-90% | 震荡上行 |
        | 2021年初 | >100% | 泡沫警示 |
        
        ### 使用建议
        1. **长期投资者**：指标<70%时分批建仓，>90%时逐步减仓
        2. **波段交易者**：关注分位数，低于30%时激进，高于70%时保守
        3. **风险控制**：指标>100%时，严格控制仓位和止损
        4. **综合判断**：结合市场情绪、政策环境、国际形势等多因素决策
        """)
    
    # 数据下载
    with st.expander("📥 下载历史数据"):
        if st.button("获取完整历史数据", type="secondary"):
            with st.spinner("正在获取历史数据..."):
                try:
                    full_data = ak.stock_buffett_index_lg()
                    st.success(f"✅ 成功获取 {len(full_data)} 条历史记录")
                    
                    # 数据预览
                    st.dataframe(full_data.tail(20), width="stretch")
                    
                    # 下载按钮
                    csv = full_data.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 下载完整数据 (CSV)",
                        data=csv,
                        file_name=f"巴菲特指标历史数据_{current_data['date']}.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"❌ 获取历史数据失败: {e}")

if __name__ == "__main__":
    display_buffett_indicator()

