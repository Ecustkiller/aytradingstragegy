"""
板块与个股联动分析模块
基于AKShare数据的行业板块分析和成分股查询系统
"""

import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import warnings
from .cache_manager import cached_function, display_cache_controls, cache_manager
warnings.filterwarnings('ignore')

@st.cache_data(ttl=3600)
def get_industry_data(start_date: str, end_date: str) -> pd.DataFrame:
    """获取行业板块数据"""
    try:
        industry_list = ak.stock_board_industry_name_em()
        data = []

        progress_bar = st.progress(0)
        total_industries = len(industry_list)
        
        for idx, (_, row) in enumerate(industry_list.iterrows()):
            try:
                # 更新进度条
                progress_bar.progress((idx + 1) / total_industries)
                
                # 获取板块历史数据
                hist_data = ak.stock_board_industry_hist_em(
                    symbol=row["板块名称"],
                    start_date=start_date,
                    end_date=end_date,
                    adjust="hfq"
                )

                if not hist_data.empty:
                    # 计算指标
                    start_price = hist_data.iloc[0]['收盘']
                    end_price = hist_data.iloc[-1]['收盘']
                    change_pct = (end_price - start_price) / start_price * 100
                    total_amount = hist_data['成交额'].sum()

                    data.append({
                        "板块名称": row["板块名称"],
                        "起始价": start_price,
                        "收盘价": end_price,
                        "区间涨跌幅(%)": change_pct,
                        "总成交额(亿)": total_amount / 1e8,
                        "日均换手率(%)": hist_data['换手率'].mean()
                    })
            except Exception as e:
                continue
        
        progress_bar.empty()
        return pd.DataFrame(data)
        
    except Exception as e:
        st.error(f"获取板块数据失败: {str(e)}")
        return pd.DataFrame()

@cached_function("industry_stocks", cache_hours=2)
def get_industry_stocks(board_name: str) -> pd.DataFrame:
    """获取板块成分股"""
    try:
        df = ak.stock_board_industry_cons_em(symbol=board_name)
        if not df.empty:
            # 数据清洗
            numeric_cols = ['最新价', '涨跌幅', '换手率']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 选择需要的列
            required_cols = ['代码', '名称', '最新价', '涨跌幅', '换手率']
            available_cols = [col for col in required_cols if col in df.columns]
            
            return df[available_cols].dropna()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"获取成分股数据失败: {str(e)}")
        return pd.DataFrame()

@cached_function("realtime_industry", cache_hours=0.5)
def get_realtime_industry_ranking():
    """获取实时板块排名"""
    try:
        df = ak.stock_board_industry_name_em()
        if not df.empty:
            # 获取实时涨跌幅数据
            realtime_data = []
            for _, row in df.iterrows():
                try:
                    # 获取板块实时数据
                    board_data = ak.stock_board_industry_spot_em()
                    board_info = board_data[board_data['板块名称'] == row['板块名称']]
                    
                    if not board_info.empty:
                        realtime_data.append({
                            "板块名称": row['板块名称'],
                            "最新价": board_info.iloc[0].get('最新价', 0),
                            "涨跌幅(%)": board_info.iloc[0].get('涨跌幅', 0),
                            "涨跌额": board_info.iloc[0].get('涨跌额', 0),
                            "换手率(%)": board_info.iloc[0].get('换手率', 0),
                            "量比": board_info.iloc[0].get('量比', 0),
                            "总市值(亿)": board_info.iloc[0].get('总市值', 0) / 1e8 if board_info.iloc[0].get('总市值', 0) else 0
                        })
                except:
                    continue
            
            return pd.DataFrame(realtime_data)
        return pd.DataFrame()
    except Exception as e:
        # 如果实时数据获取失败，返回基础板块列表
        try:
            return ak.stock_board_industry_name_em()
        except:
            return pd.DataFrame()

def display_industry_analysis():
    """显示板块与个股联动分析界面"""
    
    st.header("📊 板块与个股联动分析")
    st.markdown("基于AKShare数据的行业板块分析和成分股查询系统")
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📈 板块排行榜", "🔍 成分股查询", "⚡ 实时板块"])
    
    with tab1:
        st.subheader("📈 板块排行榜")
        
        # 参数设置
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=7),
                min_value=datetime(2020, 1, 1),
                help="分析起始日期"
            )
        
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                max_value=datetime.now(),
                help="分析结束日期"
            )
        
        with col3:
            sort_by = st.selectbox(
                "排序指标",
                options=['区间涨跌幅(%)', '总成交额(亿)', '日均换手率(%)'],
                index=0,
                help="选择排序依据"
            )
        
        # 排序设置
        col1, col2 = st.columns(2)
        with col1:
            ascending = st.checkbox("升序排列", value=False)
        with col2:
            show_count = st.slider("显示数量", min_value=10, max_value=50, value=20)
        
        # 获取板块数据按钮
        if st.button("📊 获取板块排行榜", type="primary", use_container_width=True):
            
            if start_date >= end_date:
                st.error("❌ 开始日期必须早于结束日期")
                return
            
            with st.spinner('正在加载板块数据，请稍候...'):
                start_str = start_date.strftime("%Y%m%d")
                end_str = end_date.strftime("%Y%m%d")
                industry_df = get_industry_data(start_str, end_str)
            
            if industry_df.empty:
                st.error("❌ 数据加载失败，请调整日期范围或稍后重试")
                return
            
            # 排序和筛选
            sorted_df = industry_df.sort_values(sort_by, ascending=ascending).head(show_count)
            
            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_change = sorted_df['区间涨跌幅(%)'].mean()
                st.metric("平均涨跌幅", f"{avg_change:.2f}%")
            
            with col2:
                positive_count = len(sorted_df[sorted_df['区间涨跌幅(%)'] > 0])
                st.metric("上涨板块", f"{positive_count}个")
            
            with col3:
                total_amount = sorted_df['总成交额(亿)'].sum()
                st.metric("总成交额", f"{total_amount:.1f}亿")
            
            with col4:
                max_change = sorted_df['区间涨跌幅(%)'].max()
                st.metric("最大涨幅", f"{max_change:.2f}%")
            
            # 显示排行榜
            st.subheader(f"📋 板块排行榜 ({start_date} 至 {end_date})")
            
            # 格式化显示
            display_df = sorted_df.copy()
            display_df.index = range(1, len(display_df) + 1)
            
            st.dataframe(
                display_df,
                column_config={
                    "板块名称": st.column_config.TextColumn("板块名称", width="medium"),
                    "起始价": st.column_config.NumberColumn("起始价", format="%.2f"),
                    "收盘价": st.column_config.NumberColumn("收盘价", format="%.2f"),
                    "区间涨跌幅(%)": st.column_config.NumberColumn(
                        "区间涨跌幅(%)", 
                        format="%.2f%%",
                        help="区间涨跌幅度"
                    ),
                    "总成交额(亿)": st.column_config.NumberColumn(
                        "总成交额(亿)", 
                        format="%.1f亿",
                        help="区间总成交金额"
                    ),
                    "日均换手率(%)": st.column_config.NumberColumn(
                        "日均换手率(%)", 
                        format="%.2f%%"
                    )
                },
                use_container_width=True
            )
            
            # 导出功能
            csv_data = sorted_df.to_csv(encoding='utf-8-sig')
            st.download_button(
                label="📥 下载板块数据",
                data=csv_data,
                file_name=f"industry_ranking_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
    
    with tab2:
        st.subheader("🔍 板块成分股查询")
        
        # 板块选择
        col1, col2 = st.columns(2)
        
        with col1:
            # 获取板块列表
            try:
                industry_list = ak.stock_board_industry_name_em()
                board_options = industry_list['板块名称'].tolist() if not industry_list.empty else []
            except:
                board_options = []
            
            if not board_options:
                st.error("❌ 无法获取板块列表，请检查网络连接")
                return
            
            selected_board = st.selectbox(
                "选择板块",
                options=board_options,
                index=0,
                help="选择要查询的行业板块"
            )
        
        with col2:
            sort_stocks_by = st.selectbox(
                "成分股排序",
                options=['涨跌幅', '最新价', '换手率'],
                index=0,
                help="选择成分股排序方式"
            )
        
        # 查询成分股按钮
        if st.button("🔍 查询成分股", type="primary", use_container_width=True):
            
            with st.spinner(f'正在查询 {selected_board} 成分股...'):
                stocks_df = get_industry_stocks(selected_board)
            
            if stocks_df.empty:
                st.warning(f"⚠️ 未能获取 {selected_board} 的成分股数据，请稍后重试")
                return
            
            # 排序
            if sort_stocks_by in stocks_df.columns:
                stocks_df = stocks_df.sort_values(sort_stocks_by, ascending=False)
            
            # 显示统计信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("成分股数量", f"{len(stocks_df)}只")
            
            with col2:
                if '涨跌幅' in stocks_df.columns:
                    positive_stocks = len(stocks_df[stocks_df['涨跌幅'] > 0])
                    st.metric("上涨股票", f"{positive_stocks}只")
            
            with col3:
                if '涨跌幅' in stocks_df.columns:
                    avg_change = stocks_df['涨跌幅'].mean()
                    st.metric("平均涨跌幅", f"{avg_change:.2f}%")
            
            with col4:
                if '换手率' in stocks_df.columns:
                    avg_turnover = stocks_df['换手率'].mean()
                    st.metric("平均换手率", f"{avg_turnover:.2f}%")
            
            # 显示成分股列表
            st.subheader(f"📋 {selected_board} 成分股列表")
            
            # 重置索引为排名
            display_stocks = stocks_df.copy()
            display_stocks.index = range(1, len(display_stocks) + 1)
            
            # 格式化显示
            st.dataframe(
                display_stocks,
                column_config={
                    "代码": st.column_config.TextColumn("股票代码", width="small"),
                    "名称": st.column_config.TextColumn("股票名称", width="medium"),
                    "最新价": st.column_config.NumberColumn("最新价(元)", format="%.2f"),
                    "涨跌幅": st.column_config.NumberColumn("涨跌幅(%)", format="%.2f%%"),
                    "换手率": st.column_config.NumberColumn("换手率(%)", format="%.2f%%")
                },
                use_container_width=True
            )
            
            # 导出功能
            csv_data = display_stocks.to_csv(encoding='utf-8-sig')
            st.download_button(
                label="📥 下载成分股数据",
                data=csv_data,
                file_name=f"{selected_board}_stocks_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with tab3:
        st.subheader("⚡ 实时板块排名")
        
        # 刷新设置
        col1, col2 = st.columns(2)
        
        with col1:
            auto_refresh = st.checkbox("自动刷新", value=False, help="每30秒自动刷新数据")
        
        with col2:
            show_realtime_count = st.slider("显示数量", min_value=10, max_value=30, value=15)
        
        # 获取实时数据按钮
        if st.button("⚡ 获取实时排名", type="primary", use_container_width=True) or auto_refresh:
            
            with st.spinner('正在获取实时板块数据...'):
                realtime_df = get_realtime_industry_ranking()
            
            if realtime_df.empty:
                st.warning("⚠️ 暂时无法获取实时数据，请稍后重试")
                return
            
            # 如果有涨跌幅数据，按涨跌幅排序
            if '涨跌幅(%)' in realtime_df.columns:
                realtime_df = realtime_df.sort_values('涨跌幅(%)', ascending=False)
            
            # 显示前N个
            display_realtime = realtime_df.head(show_realtime_count).copy()
            display_realtime.index = range(1, len(display_realtime) + 1)
            
            # 显示实时排名
            st.dataframe(
                display_realtime,
                column_config={
                    "板块名称": st.column_config.TextColumn("板块名称", width="medium"),
                    "最新价": st.column_config.NumberColumn("最新价", format="%.2f"),
                    "涨跌幅(%)": st.column_config.NumberColumn("涨跌幅(%)", format="%.2f%%"),
                    "涨跌额": st.column_config.NumberColumn("涨跌额", format="%.2f"),
                    "换手率(%)": st.column_config.NumberColumn("换手率(%)", format="%.2f%%"),
                    "量比": st.column_config.NumberColumn("量比", format="%.2f"),
                    "总市值(亿)": st.column_config.NumberColumn("总市值(亿)", format="%.1f亿")
                },
                use_container_width=True
            )
            
            # 自动刷新
            if auto_refresh:
                time.sleep(30)
                st.rerun()
    
    # 使用说明
    st.markdown("---")
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 🎯 功能说明
        
        **板块与个股联动分析系统** 基于AKShare数据，提供三大核心功能：
        
        #### 📈 板块排行榜
        - 自定义时间区间的板块表现分析
        - 支持按涨跌幅、成交额、换手率排序
        - 提供详细的板块统计信息
        - 支持数据导出功能
        
        #### 🔍 成分股查询
        - 查询任意板块的成分股列表
        - 显示个股的实时价格和涨跌幅
        - 支持按不同指标排序
        - 提供板块内个股统计分析
        
        #### ⚡ 实时板块排名
        - 实时板块涨跌幅排名
        - 支持自动刷新功能
        - 显示量比、换手率等关键指标
        - 快速把握市场热点板块
        
        #### 💡 使用建议
        - 结合板块排行榜找出强势行业
        - 通过成分股查询挖掘板块内优质个股
        - 利用实时排名把握盘中热点轮动
        - 关注成交额和换手率活跃的板块
        
        #### ⚠️ 注意事项
        - 数据来源于AKShare，存在一定延迟
        - 板块分析需结合基本面和技术面
        - 短期热点板块波动较大，注意风险控制
        """)

if __name__ == "__main__":
    display_industry_analysis()