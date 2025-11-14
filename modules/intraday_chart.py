"""
股票分时图绘制模块
类似同花顺的专业分时图展示
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np

# 导入logger
try:
    from .logger_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'aitrader_core' / 'datafeed'))
    from Ashare import get_price, get_realtime_quotes_sina
    HAS_ASHARE = True
except ImportError as e:
    logger.warning(f"导入Ashare失败: {e}")
    HAS_ASHARE = False


def get_intraday_data(stock_code, count=240):
    """
    获取分时数据（1分钟线）
    
    参数：
        stock_code: 股票代码
        count: 获取数据条数，默认240（一个交易日约240分钟）
    
    返回：
        DataFrame: 包含时间、开高低收、成交量
    """
    if not HAS_ASHARE:
        return None
    
    try:
        # 格式化代码
        xcode = stock_code.replace('.XSHG', '').replace('.XSHE', '')
        if not (xcode.startswith('sh') or xcode.startswith('sz')):
            if xcode.startswith('6'):
                xcode = 'sh' + xcode
            elif xcode.startswith('0') or xcode.startswith('3'):
                xcode = 'sz' + xcode
        
        # 获取1分钟数据
        df = get_price(xcode, frequency='1m', count=count)
        
        if df.empty:
            return None
        
        # 重置索引，将时间作为列
        df = df.reset_index()
        df.columns = ['time', 'open', 'close', 'high', 'low', 'volume']
        
        return df
        
    except Exception as e:
        print(f"获取分时数据失败: {e}")
        return None


def calculate_avg_price(df):
    """
    计算均价线
    
    参数：
        df: 包含价格和成交量的DataFrame
    
    返回：
        Series: 均价序列
    """
    if df is None or df.empty:
        return None
    
    # 计算累计成交额和累计成交量
    df['amount'] = df['close'] * df['volume']
    cumsum_amount = df['amount'].cumsum()
    cumsum_volume = df['volume'].cumsum()
    
    # 均价 = 累计成交额 / 累计成交量
    avg_price = cumsum_amount / cumsum_volume
    avg_price = avg_price.replace([np.inf, -np.inf], np.nan).fillna(method='ffill')
    
    return avg_price


def create_intraday_chart(stock_code, stock_name, df, prev_close=None):
    """
    创建专业的分时图
    
    参数：
        stock_code: 股票代码
        stock_name: 股票名称
        df: 分时数据DataFrame
        prev_close: 昨收价（用于计算涨跌幅）
    
    返回：
        plotly figure对象
    """
    if df is None or df.empty:
        return None
    
    # 获取昨收价
    if prev_close is None:
        try:
            quotes = get_realtime_quotes_sina(stock_code)
            xcode = stock_code.replace('.XSHG', '').replace('.XSHE', '')
            if not (xcode.startswith('sh') or xcode.startswith('sz')):
                if xcode.startswith('6'):
                    xcode = 'sh' + xcode
                elif xcode.startswith('0') or xcode.startswith('3'):
                    xcode = 'sz' + xcode
            
            if xcode in quotes:
                prev_close = quotes[xcode]['prev_close']
            else:
                prev_close = df['close'].iloc[0]
        except:
            prev_close = df['close'].iloc[0]
    
    # 计算均价线
    avg_price = calculate_avg_price(df)
    
    # 计算涨跌幅百分比
    change_pct = ((df['close'] - prev_close) / prev_close * 100)
    
    # 【关键修改】创建连续的X轴索引，而不是使用真实时间
    # 这样可以避免午休时间的断层，使图形连续
    df['x_index'] = range(len(df))
    
    # 格式化时间标签用于显示
    df['time_str'] = pd.to_datetime(df['time']).dt.strftime('%H:%M')
    
    # 创建自定义的X轴刻度标签（每30分钟显示一次）
    tick_interval = 30  # 每30分钟一个刻度
    tick_indices = []
    tick_labels = []
    
    for i in range(0, len(df), tick_interval):
        tick_indices.append(i)
        tick_labels.append(df['time_str'].iloc[i])
    
    # 添加最后一个点
    if len(df) - 1 not in tick_indices:
        tick_indices.append(len(df) - 1)
        tick_labels.append(df['time_str'].iloc[-1])
    
    # 创建子图：上方价格图，下方成交量图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{stock_name}({stock_code}) 分时图', '成交量')
    )
    
    # 价格线（白色）- 使用连续索引
    fig.add_trace(
        go.Scatter(
            x=df['x_index'],
            y=df['close'],
            mode='lines',
            name='价格',
            line=dict(color='#FFFFFF', width=1.5),
            customdata=df['time_str'],
            hovertemplate='时间: %{customdata}<br>价格: %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # 均价线（黄色）- 使用连续索引
    if avg_price is not None:
        fig.add_trace(
            go.Scatter(
                x=df['x_index'],
                y=avg_price,
                mode='lines',
                name='均价',
                line=dict(color='#FFD700', width=1.2, dash='dot'),
                customdata=df['time_str'],
                hovertemplate='时间: %{customdata}<br>均价: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # 昨收价参考线（灰色虚线）
    fig.add_hline(
        y=prev_close,
        line=dict(color='#808080', width=1, dash='dash'),
        row=1, col=1,
        annotation_text=f"昨收: {prev_close:.2f}",
        annotation_position="right"
    )
    
    # 成交量柱状图（红涨绿跌）- 使用连续索引
    colors = ['#FF4444' if close >= prev_close else '#00CC00' 
              for close in df['close']]
    
    fig.add_trace(
        go.Bar(
            x=df['x_index'],
            y=df['volume'],
            name='成交量',
            marker_color=colors,
            customdata=df['time_str'],
            hovertemplate='时间: %{customdata}<br>成交量: %{y:.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # 计算价格Y轴范围（以昨收价为中心，对称显示）
    max_change = max(abs(df['close'].max() - prev_close), 
                     abs(df['close'].min() - prev_close))
    y_range = [prev_close - max_change * 1.1, prev_close + max_change * 1.1]
    
    # 更新布局 - 专业的深色主题
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0.5)',
            font=dict(color='white')
        ),
        hovermode='x unified',
        plot_bgcolor='#0A0E27',  # 深蓝色背景
        paper_bgcolor='#0A0E27',
        font=dict(color='white', size=12),
        margin=dict(l=60, r=60, t=80, b=40)
    )
    
    # 更新价格图Y轴
    fig.update_yaxes(
        title_text="价格",
        range=y_range,
        gridcolor='#1E2A47',
        showgrid=True,
        zeroline=False,
        row=1, col=1
    )
    
    # 更新成交量Y轴
    fig.update_yaxes(
        title_text="成交量",
        gridcolor='#1E2A47',
        showgrid=True,
        row=2, col=1
    )
    
    # 更新X轴 - 使用自定义刻度标签
    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_indices,
        ticktext=tick_labels,
        gridcolor='#1E2A47',
        showgrid=True,
        row=2, col=1
    )
    
    # 同时更新价格图的X轴（虽然共享，但需要确保一致）
    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_indices,
        ticktext=tick_labels,
        gridcolor='#1E2A47',
        showgrid=True,
        row=1, col=1
    )
    
    # 添加当前价格和涨跌幅信息
    current_price = df['close'].iloc[-1]
    current_change = current_price - prev_close
    current_change_pct = (current_change / prev_close * 100)
    
    change_color = '#FF4444' if current_change >= 0 else '#00CC00'
    change_symbol = '+' if current_change >= 0 else ''
    
    fig.add_annotation(
        text=f"<b>当前价: {current_price:.2f}</b><br>"
             f"<span style='color:{change_color}'>{change_symbol}{current_change:.2f} "
             f"({change_symbol}{current_change_pct:.2f}%)</span>",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        bgcolor='rgba(0,0,0,0.7)',
        bordercolor=change_color,
        borderwidth=2,
        font=dict(size=14, color='white'),
        align='left',
        xanchor='left',
        yanchor='top'
    )
    
    return fig


def display_intraday_chart(stock_code, stock_name):
    """
    显示分时图（Streamlit组件）
    
    参数：
        stock_code: 股票代码
        stock_name: 股票名称
    """
    if not HAS_ASHARE:
        st.error("❌ Ashare库未安装，无法显示分时图")
        return
    
    with st.spinner(f"正在加载 {stock_name}({stock_code}) 的分时数据..."):
        # 获取分时数据
        df = get_intraday_data(stock_code, count=240)
        
        if df is None or df.empty:
            st.error(f"❌ 无法获取 {stock_name}({stock_code}) 的分时数据")
            st.info("💡 提示：分时数据仅在交易时间可用，非交易时间可能无法获取")
            return
        
        # 创建并显示分时图
        fig = create_intraday_chart(stock_code, stock_name, df)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("最高", f"{df['high'].max():.2f}")
            
            with col2:
                st.metric("最低", f"{df['low'].min():.2f}")
            
            with col3:
                st.metric("振幅", f"{((df['high'].max() - df['low'].min()) / df['close'].iloc[0] * 100):.2f}%")
            
            with col4:
                total_volume = df['volume'].sum()
                if total_volume >= 100000000:
                    volume_str = f"{total_volume / 100000000:.2f}亿"
                elif total_volume >= 10000:
                    volume_str = f"{total_volume / 10000:.2f}万"
                else:
                    volume_str = f"{total_volume:.0f}"
                st.metric("成交量", volume_str)
            
            # 显示数据更新时间
            last_time = df['time'].iloc[-1]
            st.caption(f"数据更新时间: {last_time}")
        else:
            st.error("❌ 绘制分时图失败")


# 测试代码
if __name__ == "__main__":
    st.set_page_config(page_title="分时图测试", layout="wide")
    st.title("📈 股票分时图测试")
    
    # 测试股票
    test_stocks = {
        "平安银行": "000001",
        "贵州茅台": "600519",
        "上证指数": "sh000001"
    }
    
    selected = st.selectbox("选择股票", list(test_stocks.keys()))
    
    if st.button("显示分时图"):
        display_intraday_chart(test_stocks[selected], selected)
