"""
涨停概念分析模块 - A股涨停概念统计与分析
"""
import streamlit as st
import pywencai
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
import plotly.express as px
from io import BytesIO
from .cache_manager import cached_function, display_cache_controls, cache_manager

# 设置全局显示选项
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', 100)

def setup_concept_analysis_styles():
    """设置涨停概念分析的CSS样式"""
    st.markdown("""
    <style>
        /* 主标题样式 */
        .title-text {
            color: #2c3e50;
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        /* 副标题样式 */
        .subheader-text {
            color: #3498db;
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.3rem;
        }
        /* 指标卡片样式 */
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 1.2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            height: 100%;
        }
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .metric-title {
            color: #7f8c8d;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        .metric-value {
            color: #2c3e50;
            font-size: 1.5rem;
            font-weight: bold;
        }
        /* 数据表格样式 */
        .dataframe {
            border-radius: 10px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        .dataframe th {
            background-color: #3498db !important;
            color: white !important;
            font-weight: bold !important;
        }
        .dataframe tr:nth-child(even) {
            background-color: #f8f9fa !important;
        }
        /* 连板卡片样式 */
        .promotion-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #3498db;
            transition: all 0.3s ease;
        }
        .promotion-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .promotion-title {
            color: #2c3e50;
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .promotion-rate {
            color: #3498db;
            font-size: 1rem;
            margin-bottom: 0.8rem;
            display: flex;
            justify-content: space-between;
        }
        .promotion-rate-value {
            font-weight: bold;
            font-size: 1.1rem;
        }
        .stock-item {
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            transition: all 0.2s ease;
        }
        .stock-item:hover {
            background-color: #ecf0f1;
        }
        .stock-name {
            font-weight: 500;
            color: #2c3e50;
        }
        .stock-concept {
            color: #95a5a6;
            font-size: 0.85rem;
            max-width: 150px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        /* 涨跌停数样式 - 红涨绿跌 */
        .limit-count {
            display: flex;
            justify-content: center;
            gap: 1rem;
        }
        .limit-up {
            color: #e74c3c;
            font-weight: bold;
        }
        .limit-down {
            color: #27ae60;
            font-weight: bold;
        }
        .limit-separator {
            color: #7f8c8d;
        }
        /* 加载动画 */
        .stSpinner>div {
            border-top-color: #3498db !important;
        }
        /* 空状态提示 */
        .empty-state {
            text-align: center;
            padding: 2rem;
            color: #7f8c8d;
            font-size: 1.1rem;
        }
        /* 涨跌颜色 - 红涨绿跌 */
        .positive-change {
            color: #e74c3c !important;
            font-weight: bold;
        }
        .negative-change {
            color: #27ae60 !important;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

@cached_function("concept_market", cache_hours=24)
def get_market_data(date, query_type):
    """获取市场数据"""
    query_map = {
        'limit_up': f"非ST，{date.strftime('%Y%m%d')}涨停",
        'limit_down': f"非ST,{date.strftime('%Y%m%d')}跌停",
        'poban': f"非ST,{date.strftime('%Y%m%d')}曾涨停"
    }
    try:
        # 统一使用相同的调用方式，移除loop参数
        df = pywencai.get(
            query=query_map[query_type],
            sort_key='成交金额',
            sort_order='desc'
        )
        return df if df is not None and not df.empty else None
    except Exception as e:
        st.error(f"获取{query_type}数据时出错: {str(e)}")
        return None

def get_trade_dates():
    """获取交易日数据"""
    try:
        trade_date_range = ak.tool_trade_date_hist_sina()
        trade_date_range['trade_date'] = pd.to_datetime(trade_date_range['trade_date']).dt.date
        return trade_date_range
    except Exception as e:
        # 如果akshare获取失败,使用备用方案
        st.warning(f"使用备用交易日数据 (原因: {str(e)})")
        # 从2020年开始到今天,排除周末
        from datetime import datetime, timedelta
        
        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()
        
        # 生成所有日期
        all_dates = []
        current = start_date
        while current <= end_date:
            # 排除周末 (周六=5, 周日=6)
            if current.weekday() < 5:
                all_dates.append(current.date())
            current += timedelta(days=1)
        
        # 创建DataFrame
        trade_date_range = pd.DataFrame({
            'trade_date': all_dates
        })
        
        return trade_date_range

def to_excel(df):
    """Excel导出函数"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='涨停概念分析')
    processed_data = output.getvalue()
    return processed_data

@cached_function("concept_analysis", cache_hours=24)
def analyze_monthly_concepts(selected_date):
    """近1个月涨停概念分析"""
    # 获取交易日数据
    trade_date_range = get_trade_dates()
    if trade_date_range.empty:
        st.error("无法获取交易日数据")
        return pd.DataFrame()
    
    # 确定日期范围（最近1个月）
    end_date = selected_date
    start_date = end_date - timedelta(days=30)
    valid_dates = trade_date_range[
        (trade_date_range['trade_date'] >= start_date) &
        (trade_date_range['trade_date'] <= end_date)
    ]['trade_date'].tolist()
    
    # 进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    
    # 遍历每个交易日
    for i, date in enumerate(valid_dates):
        try:
            # 更新进度
            progress = (i + 1) / len(valid_dates)
            progress_bar.progress(progress)
            status_text.text(f"正在分析 {date.strftime('%Y-%m-%d')} ({i + 1}/{len(valid_dates)})...")
            
            # 获取当日涨停数据
            df = get_market_data(date, 'limit_up')
            if df is None or df.empty:
                continue
            
            # 获取涨停原因列名
            reason_col = f'涨停原因类别[{date.strftime("%Y%m%d")}]'
            if reason_col not in df.columns:
                continue
            
            # 分割涨停原因并统计
            concepts = df[reason_col].dropna().astype(str).str.split('+').explode()
            concept_counts = concepts.value_counts().reset_index()
            concept_counts.columns = ['概念', '出现次数']
            total_stocks = len(df)
            
            # 取前10大概念并格式化
            top_concepts = []
            for _, row in concept_counts.head(10).iterrows():
                concept_str = f"{row['概念']}({row['出现次数']}/{total_stocks})"
                top_concepts.append(concept_str)
            
            # 补足10个概念
            while len(top_concepts) < 10:
                top_concepts.append("")
            
            # 添加到结果（总涨停数放在概念前面）
            result_row = {'日期': date.strftime('%Y-%m-%d'), '总涨停数': total_stocks}
            for j, concept in enumerate(top_concepts, 1):
                result_row[f'概念{j}'] = concept
            results.append(result_row)
            
        except Exception as e:
            st.error(f"分析{date}数据时出错: {str(e)}")
            continue
    
    # 清除进度条
    progress_bar.empty()
    status_text.empty()
    
    # 转换为DataFrame
    result_df = pd.DataFrame(results)
    
    if not result_df.empty:
        # 添加变化趋势箭头
        def format_change(row):
            prev = result_df.iloc[row.name - 1]['总涨停数'] if row.name > 0 else row['总涨停数']
            change = row['总涨停数'] - prev
            arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
            color = "#e74c3c" if change > 0 else "#27ae60" if change < 0 else "#7f8c8d"
            return f"<span style='color:{color}'>{row['总涨停数']} {arrow}</span>"
        
        result_df['涨停趋势'] = [format_change(row) for _, row in result_df.iterrows()]
        
        # 重新排序列（总涨停数在日期之后）
        columns = ['日期', '涨停趋势', '总涨停数'] + [f'概念{i}' for i in range(1, 11)]
        result_df = result_df[columns]
    
    return result_df

def display_concept_analysis():
    """显示涨停概念分析界面"""
    # 设置样式
    setup_concept_analysis_styles()
    
    # 主标题
    st.markdown('<p class="title-text">📈 A股涨停概念分析</p>', unsafe_allow_html=True)
    
    # 获取交易日数据
    with st.spinner("正在加载交易日数据..."):
        trade_date_range = get_trade_dates()
        if trade_date_range.empty:
            st.error("无法获取交易日数据，请检查网络连接或稍后再试。")
            return
    
    # 日期选择
    today = datetime.now().date()
    if not trade_date_range.empty:
        if today in trade_date_range['trade_date'].values:
            default_date = today
        else:
            default_date = trade_date_range[trade_date_range['trade_date'] <= today]['trade_date'].max()
    else:
        default_date = today
    
    selected_date = st.date_input(
        "📅 选择分析日期",
        value=default_date,
        min_value=trade_date_range['trade_date'].min() if not trade_date_range.empty else today - timedelta(days=30),
        max_value=trade_date_range['trade_date'].max() if not trade_date_range.empty else today,
        key="concept_date_selector"
    )
    
    # 检查选择的日期是否是交易日
    if not trade_date_range.empty and selected_date not in trade_date_range['trade_date'].values:
        st.warning("⚠️ 所选日期不是A股交易日，已自动选择最近的交易日")
        selected_date = trade_date_range[trade_date_range['trade_date'] <= selected_date]['trade_date'].max()
        st.info(f"📅 已选择: {selected_date.strftime('%Y-%m-%d')}")
    
    # 添加分析按钮
    st.markdown('<p class="subheader-text">📅 每日涨停概念分布统计</p>', unsafe_allow_html=True)
    
    # 分析按钮
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        
        # 调用近1个月涨停概念分析
        monthly_concept_df = analyze_monthly_concepts(selected_date)
        
        if not monthly_concept_df.empty:
            # 应用样式
            styled_df = monthly_concept_df.style.format({
                '涨停趋势': lambda x: x  # 保留HTML格式
            }).hide(axis="index")
            
            # 显示表格
            st.markdown("**每日涨停概念分布**")
            st.write(styled_df.to_html(escape=False), unsafe_allow_html=True)
            
            # 添加下载按钮
            excel_data = to_excel(monthly_concept_df)
            st.download_button(
                label="📥 导出Excel数据",
                data=excel_data,
                file_name=f"涨停概念分析_{selected_date.strftime('%Y%m%d')}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.warning("⚠️ 未获取到有效数据")
    
    else:
        # 显示提示信息
        st.info("💡 点击上方按钮开始分析近1个月的涨停概念分布")
        
        # 检查是否有缓存数据
        from .cache_manager import cache_manager
        cache_key = cache_manager.generate_cache_key("concept_analysis", {"args": (selected_date,), "kwargs": {}})
        cached_info = cache_manager.load_cache(cache_key, max_age_hours=0)
        
        if cached_info:
            st.success(f"📋 已有缓存数据 (分析时间: {cached_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')})")
            st.info("点击分析按钮可直接查看缓存结果，或使用缓存控制面板强制刷新")
    
    return pd.DataFrame()
