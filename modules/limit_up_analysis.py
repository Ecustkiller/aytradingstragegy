"""
涨停连板分析模块
统计涨停、连板数据，分析晋级率
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time

# 尝试导入依赖
try:
    import pywencai
    HAS_PYWENCAI = True
    PYWENCAI_ERROR = None
except ImportError as e:
    HAS_PYWENCAI = False
    PYWENCAI_ERROR = str(e)

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# CSS样式
LIMIT_UP_STYLE = """
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .limit-up {
        color: #e74c3c;
        font-weight: bold;
    }
    .limit-down {
        color: #27ae60;
        font-weight: bold;
    }
</style>
"""

def get_trade_dates():
    """获取交易日历"""
    if not HAS_AKSHARE:
        # 简化版：返回最近的工作日
        dates = []
        current_date = datetime.now().date()
        for i in range(10):
            date = current_date - timedelta(days=i)
            if date.weekday() < 5:  # 周一到周五
                dates.append(date)
        return pd.DataFrame({'trade_date': dates})
    
    try:
        trade_date_range = ak.tool_trade_date_hist_sina()
        trade_date_range['trade_date'] = pd.to_datetime(trade_date_range['trade_date']).dt.date
        return trade_date_range
    except Exception as e:
        st.warning(f"获取交易日历失败: {e}")
        # 返回简化版
        dates = []
        current_date = datetime.now().date()
        for i in range(10):
            date = current_date - timedelta(days=i)
            if date.weekday() < 5:
                dates.append(date)
        return pd.DataFrame({'trade_date': dates})

def get_market_data(date, query_type, max_retries=2):
    """获取市场数据"""
    if not HAS_PYWENCAI:
        return None
    
    query_map = {
        'limit_up': f"非ST,{date.strftime('%Y%m%d')}涨停",
        'limit_down': f"非ST,{date.strftime('%Y%m%d')}跌停",
        'poban': f"非ST,{date.strftime('%Y%m%d')}曾涨停"
    }
    
    for attempt in range(max_retries):
        try:
            df = pywencai.get(
                query=query_map[query_type],
                sort_key='成交金额',
                sort_order='desc',
                loop=True
            )
            if df is not None and not df.empty:
                return df
            else:
                if attempt < max_retries - 1:
                    time.sleep(2)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                st.error(f"获取{query_type}数据失败: {str(e)}")
    
    return None

def get_concept_counts(df, date):
    """统计涨停概念"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    reason_col = f'涨停原因类别[{date.strftime("%Y%m%d")}]'
    if reason_col not in df.columns:
        return pd.DataFrame()
    
    try:
        concepts = df[reason_col].astype(str).str.split('+').explode().reset_index(drop=True)
        concept_counts = concepts.value_counts().reset_index()
        concept_counts.columns = ['概念', '出现次数']
        return concept_counts
    except Exception as e:
        st.warning(f"统计概念失败: {e}")
        return pd.DataFrame()

def analyze_continuous_limit_up(df, date):
    """分析连续涨停数据"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    date_str = date.strftime("%Y%m%d")
    days_col = f'连续涨停天数[{date_str}]'
    reason_col = f'涨停原因类别[{date_str}]'
    
    # 准备列映射
    column_mapping = {
        days_col: '连续涨停天数',
        '股票代码': '股票代码',
        '股票简称': '股票简称',
        '最新价': '最新价',
        reason_col: '涨停原因',
        f'首次涨停时间[{date_str}]': '首次涨停时间',
        f'最终涨停时间[{date_str}]': '最终涨停时间',
        f'几天几板[{date_str}]': '几天几板',
        f'a股市值(不含限售股)[{date_str}]': '总市值'
    }
    
    # 只保留存在的列
    available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
    if not available_columns:
        return pd.DataFrame()
    
    # 处理数据
    result_df = df[list(available_columns.keys())].copy()
    result_df.columns = [available_columns[col] for col in result_df.columns]
    
    # 填充缺失值
    if '涨停原因' in result_df.columns:
        result_df['涨停原因'] = result_df['涨停原因'].fillna('未知')
    
    if '连续涨停天数' in result_df.columns:
        result_df['连续涨停天数'] = pd.to_numeric(result_df['连续涨停天数'], errors='coerce').fillna(1)
        result_df = result_df.sort_values('连续涨停天数', ascending=False)
    
    return result_df.reset_index(drop=True)

def calculate_promotion_rates(current_df, previous_df, current_date, previous_date):
    """计算连板晋级率"""
    if current_df is None or previous_df is None or current_df.empty or previous_df.empty:
        return pd.DataFrame()
    
    current_days_col = f'连续涨停天数[{current_date.strftime("%Y%m%d")}]'
    previous_days_col = f'连续涨停天数[{previous_date.strftime("%Y%m%d")}]'
    
    if current_days_col not in current_df.columns or previous_days_col not in previous_df.columns:
        return pd.DataFrame()
    
    # 转换为数值
    current_df[current_days_col] = pd.to_numeric(current_df[current_days_col], errors='coerce')
    previous_df[previous_days_col] = pd.to_numeric(previous_df[previous_days_col], errors='coerce')
    
    max_days = int(max(
        current_df[current_days_col].max() or 0,
        previous_df[previous_days_col].max() or 0
    ))
    
    promotion_data = []
    
    for days in range(1, max_days + 1):
        prev_count = len(previous_df[previous_df[previous_days_col] == days])
        current_count = len(current_df[current_df[current_days_col] == days + 1])
        
        promotion_rate = (current_count / prev_count * 100) if prev_count > 0 else 0
        
        promotion_data.append({
            '连板天数': f'{days}板',
            '昨日数量': prev_count,
            '今日晋级': current_count,
            '晋级率': f'{promotion_rate:.1f}%'
        })
    
    return pd.DataFrame(promotion_data)

def display_limit_up_analysis():
    """显示涨停连板分析主界面"""
    st.title("📈 涨停连板分析")
    
    st.markdown("""
    ### 功能说明
    **涨停连板分析** 帮助您快速掌握市场热点和连板情况。
    
    **核心功能**：
    - **涨停/跌停统计**：当日涨停、跌停、破板数量
    - **连板分析**：连续涨停天数统计和排名
    - **概念热度**：涨停股票的概念分布
    - **晋级率分析**：各连板数的晋级成功率
    """)
    
    st.markdown(LIMIT_UP_STYLE, unsafe_allow_html=True)
    
    # 检查依赖
    if not HAS_PYWENCAI:
        st.error("❌ pywencai库未安装或不可用")
        st.info(f"错误详情: {PYWENCAI_ERROR}")
        st.code("pip install pywencai", language="bash")
        return
    
    st.markdown("---")
    
    # 日期选择
    st.subheader("📅 选择分析日期")
    
    # 获取交易日
    trade_dates = get_trade_dates()
    if trade_dates.empty:
        st.error("❌ 无法获取交易日历")
        return
    
    trade_dates_list = trade_dates['trade_date'].tolist()
    today = datetime.now().date()
    
    # 默认选择最近的交易日
    default_date = trade_dates_list[0] if trade_dates_list else today
    
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input(
            "分析日期",
            value=default_date,
            max_value=today,
            help="选择要分析的交易日"
        )
    
    with col2:
        if st.button("🔍 开始分析", type="primary", width="stretch"):
            st.session_state.run_limit_up_analysis = True
    
    # 执行分析
    if st.session_state.get('run_limit_up_analysis', False):
        st.markdown("---")
        
        with st.spinner("正在获取数据..."):
            limit_up_df = get_market_data(selected_date, 'limit_up')
            limit_down_df = get_market_data(selected_date, 'limit_down')
            poban_df = get_market_data(selected_date, 'poban')
        
        # 涨跌停统计
        st.subheader("📊 市场概况")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            limit_up_count = len(limit_up_df) if limit_up_df is not None else 0
            st.metric("涨停数", limit_up_count, help="当日涨停股票数量")
        
        with col2:
            limit_down_count = len(limit_down_df) if limit_down_df is not None else 0
            st.metric("跌停数", limit_down_count, help="当日跌停股票数量")
        
        with col3:
            poban_count = len(poban_df) if poban_df is not None else 0
            po_count = poban_count - limit_up_count
            st.metric("破板数", po_count, help="曾涨停但未封住的股票")
        
        with col4:
            ratio = (limit_up_count / (limit_up_count + limit_down_count) * 100) if (limit_up_count + limit_down_count) > 0 else 0
            st.metric("涨跌比", f"{ratio:.1f}%", help="涨停/(涨停+跌停)")
        
        st.markdown("---")
        
        # 连板分析
        if limit_up_df is not None and not limit_up_df.empty:
            st.subheader("🔥 连板分析")
            
            continuous_df = analyze_continuous_limit_up(limit_up_df, selected_date)
            
            if not continuous_df.empty and '连续涨停天数' in continuous_df.columns:
                # 连板统计
                board_counts = continuous_df['连续涨停天数'].value_counts().sort_index(ascending=False)
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown("##### 连板数量分布")
                    for days, count in board_counts.items():
                        st.markdown(f"**{int(days)}连板**: {count}只")
                
                with col2:
                    st.markdown("##### 连板分布图")
                    fig = px.bar(
                        x=[f"{int(d)}板" for d in board_counts.index],
                        y=board_counts.values,
                        labels={'x': '连板数', 'y': '股票数量'}
                    )
                    fig.update_traces(marker_color='#e74c3c')
                    st.plotly_chart(fig, width="stretch")
                
                # 显示连板股票列表
                st.markdown("---")
                st.markdown("##### 📋 连板股票明细")
                
                display_columns = [col for col in ['连续涨停天数', '股票代码', '股票简称', '最新价', '涨停原因', '几天几板', '总市值'] 
                                 if col in continuous_df.columns]
                
                st.dataframe(
                    continuous_df[display_columns].head(50),
                    width="stretch",
                    height=400
                )
        
        # 概念热度
        st.markdown("---")
        st.subheader("🎯 热点概念分析")
        
        if limit_up_df is not None and not limit_up_df.empty:
            concept_counts = get_concept_counts(limit_up_df, selected_date)
            
            if not concept_counts.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### 📊 概念排行榜（Top 15）")
                    st.dataframe(
                        concept_counts.head(15),
                        width="stretch",
                        height=400
                    )
                
                with col2:
                    st.markdown("##### 📈 概念热度图")
                    fig = px.bar(
                        concept_counts.head(10),
                        x='出现次数',
                        y='概念',
                        orientation='h',
                        color='出现次数',
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, width="stretch")
        
        # 晋级率分析（需要前一日数据）
        if len(trade_dates_list) >= 2:
            st.markdown("---")
            st.subheader("📈 连板晋级率分析")
            
            previous_date = trade_dates_list[1]
            
            with st.spinner("正在计算晋级率..."):
                previous_limit_up_df = get_market_data(previous_date, 'limit_up')
                
                if limit_up_df is not None and previous_limit_up_df is not None:
                    promotion_df = calculate_promotion_rates(
                        limit_up_df, previous_limit_up_df,
                        selected_date, previous_date
                    )
                    
                    if not promotion_df.empty:
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown(f"##### 晋级率统计 ({previous_date} → {selected_date})")
                            st.dataframe(promotion_df, width="stretch")
                        
                        with col2:
                            st.markdown("##### 晋级率趋势图")
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=promotion_df['连板天数'],
                                y=[float(r.rstrip('%')) for r in promotion_df['晋级率']],
                                mode='lines+markers',
                                marker=dict(size=10, color='#3498db'),
                                line=dict(width=2)
                            ))
                            fig.update_layout(
                                xaxis_title="连板天数",
                                yaxis_title="晋级率 (%)",
                                height=300
                            )
                            st.plotly_chart(fig, width="stretch")
        
        # 下载按钮
        st.markdown("---")
        if limit_up_df is not None and not limit_up_df.empty:
            csv = limit_up_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载涨停数据 (CSV)",
                data=csv,
                file_name=f"涨停数据_{selected_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        st.session_state.run_limit_up_analysis = False

if __name__ == "__main__":
    display_limit_up_analysis()

