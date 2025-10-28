"""
指数RPS强度排名分析模块 - 基于相对强度排名的指数分析
"""
import streamlit as st
import pywencai
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .cache_manager import cached_function, display_cache_controls

def setup_index_rps_styles():
    """设置指数RPS分析的CSS样式"""
    st.markdown("""
    <style>
        /* RPS分析专用样式 */
        .rps-title {
            color: #2c3e50;
            font-size: 2.2rem;
            font-weight: bold;
            margin-bottom: 1rem;
            text-align: center;
        }
        .rps-subtitle {
            color: #3498db;
            font-size: 1.3rem;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.8rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.3rem;
        }
        .rps-metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .rps-high {
            color: #e74c3c;
            font-weight: bold;
        }
        .rps-medium {
            color: #f39c12;
            font-weight: bold;
        }
        .rps-low {
            color: #27ae60;
            font-weight: bold;
        }
        .rps-table {
            border-radius: 8px;
            overflow: hidden;
        }
    </style>
    """, unsafe_allow_html=True)

def get_date_range(days):
    """计算日期范围"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

def calculate_rps(df, change_col):
    """
    RPS计算函数 - 使用公式: RPS = (1 - 排名 / 总板块数) × 100
    RPS值越高表示相对强度越强
    """
    # 转换涨跌幅为数值
    df[change_col] = pd.to_numeric(df[change_col].astype(str).str.replace('%', ''), errors='coerce')
    
    # 计算排名（按涨跌幅降序排列）
    df['rank'] = df[change_col].rank(ascending=False, method='min')
    
    # 计算RPS
    total_count = len(df)
    df['RPS'] = ((1 - df['rank'] / total_count) * 100).round(2)
    
    # 删除临时列
    df.drop('rank', axis=1, inplace=True)
    
    return df

def get_index_data(period):
    """获取指数数据"""
    start_date, end_date = get_date_range(period)
    query = f"指数代码886开头，近{period}日涨跌幅"
    
    try:
        # 使用pywencai获取数据
        df = pywencai.get(query=query, query_type='zhishu')
        
        # 检查返回数据
        if df.empty:
            st.warning(f"未获取到近{period}日数据")
            return None
        
        # 查找涨跌幅列
        change_col = None
        for col in df.columns:
            if "区间涨跌幅" in col:
                change_col = col
                break
        
        if not change_col:
            st.warning(f"未找到近{period}日涨跌幅列")
            return None
        
        # 查找代码列
        code_cols = [col for col in df.columns if "指数代码" in col]
        if not code_cols:
            st.warning(f"未找到近{period}日代码列")
            return None
        code_col = code_cols[0]
        
        # 查找名称列
        name_cols = [col for col in df.columns if "指数简称" in col]
        if not name_cols:
            st.warning(f"未找到近{period}日名称列")
            return None
        name_col = name_cols[0]
        
        # 提取关键列
        result_df = df[[code_col, name_col, change_col]].copy()
        result_df.columns = ['指数代码', '指数简称', f'{period}日涨跌幅']
        
        # 计算RPS
        result_df = calculate_rps(result_df, f'{period}日涨跌幅')
        result_df.rename(columns={'RPS': f'RPS_{period}'}, inplace=True)
        
        return result_df
        
    except Exception as e:
        st.error(f"获取近{period}日数据失败: {str(e)}")
        return None

def format_rps_value(rps_value):
    """格式化RPS值并添加颜色"""
    if pd.isna(rps_value):
        return "N/A"
    
    if rps_value >= 80:
        return f'<span class="rps-high">{rps_value:.1f}</span>'
    elif rps_value >= 50:
        return f'<span class="rps-medium">{rps_value:.1f}</span>'
    else:
        return f'<span class="rps-low">{rps_value:.1f}</span>'

def display_rps_summary(merged_df, periods):
    """显示RPS分析摘要"""
    st.markdown('<p class="rps-subtitle">📊 RPS强度分析摘要</p>', unsafe_allow_html=True)
    
    cols = st.columns(len(periods))
    
    for i, period in enumerate(periods):
        rps_col = f'RPS_{period}'
        if rps_col in merged_df.columns:
            with cols[i]:
                # 计算统计信息
                high_rps = len(merged_df[merged_df[rps_col] >= 80])
                medium_rps = len(merged_df[(merged_df[rps_col] >= 50) & (merged_df[rps_col] < 80)])
                low_rps = len(merged_df[merged_df[rps_col] < 50])
                avg_rps = merged_df[rps_col].mean()
                
                st.markdown(f"""
                <div class="rps-metric-card">
                    <h4>{period}日RPS分析</h4>
                    <p><span class="rps-high">强势(≥80): {high_rps}个</span></p>
                    <p><span class="rps-medium">中等(50-80): {medium_rps}个</span></p>
                    <p><span class="rps-low">弱势(<50): {low_rps}个</span></p>
                    <p>平均RPS: {avg_rps:.1f}</p>
                </div>
                """, unsafe_allow_html=True)

def display_index_rps_analysis():
    """显示指数RPS强度排名分析界面"""
    # 设置样式
    setup_index_rps_styles()
    
    # 主标题
    st.markdown('<p class="rps-title">📈 指数RPS强度排名分析</p>', unsafe_allow_html=True)
    
    # 说明信息
    with st.expander("📖 RPS指标说明", expanded=False):
        st.markdown("""
        **RPS (Relative Price Strength) 相对价格强度指标说明：**
        
        - **计算公式**: RPS = (1 - 排名 / 总指数数) × 100
        - **取值范围**: 0-100，数值越高表示相对强度越强
        - **强度分级**:
          - 🔴 **强势 (RPS ≥ 80)**: 表现优于80%以上的指数
          - 🟡 **中等 (50 ≤ RPS < 80)**: 表现中等
          - 🟢 **弱势 (RPS < 50)**: 表现较弱
        
        **使用建议**:
        - RPS值持续上升的指数值得关注
        - 多周期RPS都较高的指数通常具有较强的趋势性
        - 结合成交量和基本面分析效果更佳
        """)
    
    # 参数设置
    st.markdown('<p class="rps-subtitle">⚙️ 分析参数设置</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 时间范围选择
        periods = st.multiselect(
            "选择分析周期（日）",
            [5, 10, 20, 30, 60, 120],
            default=[5, 20, 60],
            help="选择要分析的时间周期，建议选择2-4个周期进行对比分析"
        )
    
    with col2:
        # 数据获取按钮
        analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True)
    
    if not periods:
        st.warning("⚠️ 请至少选择一个分析周期")
        return
    
    # 数据获取和分析
    if analyze_button:
        with st.spinner("正在获取指数数据并计算RPS..."):
            dataframes = {}
            progress_bar = st.progress(0)
            
            for i, period in enumerate(periods):
                progress_bar.progress((i + 1) / len(periods))
                df = get_index_data(period)
                if df is not None:
                    dataframes[period] = df
            
            progress_bar.empty()
            
            if not dataframes:
                st.error("❌ 未获取到任何数据，请检查网络连接或稍后重试")
                return
            
            # 合并数据
            merged_df = None
            for i, period in enumerate(periods):
                if period in dataframes:
                    if i == 0:
                        merged_df = dataframes[period]
                    else:
                        merged_df = pd.merge(
                            merged_df,
                            dataframes[period],
                            on=['指数代码', '指数简称'],
                            how='outer'
                        )
            
            if merged_df is None or merged_df.empty:
                st.error("❌ 数据合并失败")
                return
            
            # 显示分析摘要
            display_rps_summary(merged_df, periods)
            
            # 显示详细结果
            st.markdown('<p class="rps-subtitle">📋 详细RPS排名</p>', unsafe_allow_html=True)
            
            # 按RPS值排序（使用第一个周期的RPS作为主要排序依据）
            sort_columns = [f'RPS_{p}' for p in periods if f'RPS_{p}' in merged_df.columns]
            if sort_columns:
                merged_df_sorted = merged_df.sort_values(by=sort_columns, ascending=False)
            else:
                merged_df_sorted = merged_df
            
            # 格式化显示
            display_df = merged_df_sorted.copy()
            
            # 添加排名列
            display_df.insert(0, '排名', range(1, len(display_df) + 1))
            
            # 显示数据表格
            st.dataframe(
                display_df,
                use_container_width=True,
                height=600,
                column_config={
                    "排名": st.column_config.NumberColumn("排名", width="small"),
                    "指数代码": st.column_config.TextColumn("指数代码", width="medium"),
                    "指数简称": st.column_config.TextColumn("指数简称", width="medium"),
                    **{f'RPS_{p}': st.column_config.NumberColumn(
                        f'RPS_{p}日',
                        help=f"{p}日相对强度排名",
                        format="%.1f"
                    ) for p in periods}
                }
            )
            
            # 下载功能
            st.markdown('<p class="rps-subtitle">💾 数据导出</p>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV下载
                csv = merged_df_sorted.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下载CSV数据",
                    data=csv,
                    file_name=f"指数RPS排名_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
            
            with col2:
                # Excel下载
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    merged_df_sorted.to_excel(writer, index=False, sheet_name='指数RPS分析')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📊 下载Excel数据",
                    data=excel_data,
                    file_name=f"指数RPS排名_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )
            
            # 显示分析建议
            st.markdown('<p class="rps-subtitle">💡 分析建议</p>', unsafe_allow_html=True)
            
            # 找出表现最好的指数
            if sort_columns:
                top_indices = merged_df_sorted.head(5)
                st.markdown("**表现最强的5个指数：**")
                for idx, row in top_indices.iterrows():
                    rps_values = [f"{row[col]:.1f}" for col in sort_columns if not pd.isna(row[col])]
                    st.write(f"• {row['指数简称']} ({row['指数代码']}) - RPS: {', '.join(rps_values)}")
            
            st.info("""
            **投资建议**：
            - 关注多周期RPS都较高的指数，通常具有较强的趋势延续性
            - RPS突然上升的指数可能存在短期机会
            - 结合成交量、基本面等因素综合判断
            - 注意风险控制，RPS仅为技术分析工具之一
            """)

if __name__ == "__main__":
    display_index_rps_analysis()