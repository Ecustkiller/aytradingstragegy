"""
竞价分析模块
集合竞价异动分析，帮助盘前选股
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.graph_objects as go

# 尝试导入依赖
try:
    import pywencai
    HAS_PYWENCAI = True
    PYWENCAI_ERROR = None
except ImportError as e:
    HAS_PYWENCAI = False
    PYWENCAI_ERROR = str(e)

try:
    from chinese_calendar import is_workday, is_holiday
    HAS_CHINESE_CALENDAR = True
except ImportError:
    HAS_CHINESE_CALENDAR = False
    # 简单的交易日判断（周一到周五）
    def is_workday(date):
        return date.weekday() < 5
    def is_holiday(date):
        return False

# 常量配置
MAX_STOCKS = 100
MAX_RETRIES = 1
RETRY_DELAY = 1

def safe_format(x, divisor=1, suffix=''):
    """安全格式化数值"""
    try:
        return f"{float(x)/divisor:.2f}{suffix}"
    except (ValueError, TypeError):
        return str(x)

def get_strategy_stocks(query, selected_date, max_retries=MAX_RETRIES):
    """获取竞价策略股票"""
    if not HAS_PYWENCAI:
        return None, "pywencai库未安装或不可用"
    
    for attempt in range(max_retries):
        try:
            result = pywencai.get(query=query, sort_key='竞价成交金额', sort_order='desc')
            
            # 检查返回值类型
            if result is None:
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None, "pywencai返回空结果，可能是查询条件无效或网络问题"
            
            # 如果返回的是字典，尝试提取DataFrame
            if isinstance(result, dict):
                df = result.get('data') if 'data' in result else pd.DataFrame()
            else:
                df = result
            
            # 检查DataFrame是否为空
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None, "策略无数据，请尝试其他日期或条件"
            
            date_str = selected_date.strftime("%Y%m%d")
            columns_to_rename = {
                '股票代码': '股票代码',
                '股票简称': '股票简称',
                f'竞价金额[{date_str}]': '竞价金额',
                f'竞价金额排名[{date_str}]': '竞价金额排名',
                f'竞价异动类型[{date_str}]': '竞价异动类型',
                f'集合竞价评级[{date_str}]': '集合竞价评级',
                f'竞价涨幅[{date_str}]': '竞价涨幅',
                '最新涨跌幅': '涨跌幅',
                '最新价': '最新价',
                f'分时区间收盘价:前复权[{date_str} 09:25:00]': '竞价价格',
                f'竞价未匹配金额[{date_str}]': '竞价未匹配金额'
            }
            
            # 只重命名存在的列
            existing_columns = {k: v for k, v in columns_to_rename.items() if k in df.columns}
            if existing_columns:
                df = df.rename(columns=existing_columns)
            
            return df[:MAX_STOCKS], None
        except AttributeError as e:
            # 专门处理 'NoneType' object has no attribute 'get' 错误
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None, f"数据格式错误: pywencai可能返回了意外的数据格式"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None, f"查询失败 (尝试{max_retries}次): {str(e)}"

def run_strategy(query, selected_date, market_cap):
    """运行竞价分析策略"""
    st.write(f"**选股日期**: {selected_date.strftime('%Y-%m-%d')}")
    st.write(f"**市值筛选**: {market_cap}亿")
    
    if not is_workday(selected_date) or is_holiday(selected_date):
        st.warning("⚠️ 所选日期不是A股交易日，请选择其他日期。")
        return
    
    with st.spinner("正在获取股票信息..."):
        df, error = get_strategy_stocks(query, selected_date)
    
    if error:
        st.error(f"❌ {error}")
        st.info("""
        **请检查以下内容**:
        1. 网络连接是否稳定
        2. pywencai库是否为最新版本
        3. 查询条件是否有效
        4. 是否拥有使用pywencai的必要权限
        """)
        return
    
    if df is None or df.empty:
        st.warning("⚠️ 没有找到符合策略的股票。")
        return
    
    # 格式化数据
    df_display = df.copy()
    if '涨跌幅' in df_display.columns:
        df_display['涨跌幅'] = df_display['涨跌幅'].apply(lambda x: safe_format(x, suffix='%'))
    if '竞价涨幅' in df_display.columns:
        df_display['竞价涨幅'] = df_display['竞价涨幅'].apply(lambda x: safe_format(x, suffix='%'))
    if '竞价金额' in df_display.columns:
        df_display['竞价金额'] = df_display['竞价金额'].apply(lambda x: safe_format(x, divisor=10000, suffix='万'))
    if '竞价未匹配金额' in df_display.columns:
        df_display['竞价未匹配金额'] = df_display['竞价未匹配金额'].apply(lambda x: safe_format(x, divisor=10000, suffix='万'))
    
    # 显示统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("符合条件股票数", len(df))
    with col2:
        if '竞价金额' in df.columns:
            total_amount = df['竞价金额'].replace('', 0).astype(str).str.replace('万', '').astype(float).sum()
            st.metric("总竞价金额", f"{total_amount:.0f}万")
    with col3:
        if '竞价异动类型' in df.columns:
            st.metric("异动类型数", df['竞价异动类型'].nunique())
    with col4:
        if '集合竞价评级' in df.columns:
            avg_rating = df['集合竞价评级'].replace('', 0).astype(float).mean()
            st.metric("平均评级", f"{avg_rating:.1f}")
    
    st.markdown("---")
    
    # 显示数据表格
    st.subheader("📊 竞价异动股票列表")
    
    # 选择要显示的列
    display_columns = ['股票代码', '股票简称', '竞价价格', '最新价', '涨跌幅', 
                      '竞价涨幅', '竞价金额', '竞价金额排名', '竞价异动类型', '集合竞价评级']
    available_columns = [col for col in display_columns if col in df_display.columns]
    
    st.dataframe(
        df_display[available_columns],
        use_container_width=True,
        height=400
    )
    
    # 可视化分析
    st.markdown("---")
    st.subheader("📈 竞价分析可视化")
    
    # 如果有竞价异动类型，显示分布图
    if '竞价异动类型' in df.columns and not df['竞价异动类型'].isna().all():
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 竞价异动类型分布")
            type_counts = df['竞价异动类型'].value_counts()
            fig = go.Figure(data=[go.Pie(labels=type_counts.index, values=type_counts.values)])
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("##### 集合竞价评级分布")
            if '集合竞价评级' in df.columns:
                rating_counts = df['集合竞价评级'].value_counts().sort_index()
                fig = go.Figure(data=[go.Bar(x=rating_counts.index, y=rating_counts.values)])
                fig.update_layout(
                    xaxis_title="评级",
                    yaxis_title="股票数量",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # 下载按钮
    st.markdown("---")
    csv = df_display.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 下载数据 (CSV)",
        data=csv,
        file_name=f"竞价分析_{selected_date.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def display_auction_analysis():
    """显示竞价分析主界面"""
    st.title("🎯 集合竞价分析")
    
    st.markdown("""
    ### 功能说明
    集合竞价分析帮助您在盘前（09:15-09:25）发现**异动股票**，提前布局当日交易机会。
    
    **核心指标**：
    - **竞价金额**：集合竞价阶段的成交金额
    - **竞价涨幅**：相比前日收盘的涨幅
    - **异动类型**：大单买入、放量拉升等
    - **竞价评级**：综合评分（1-5分）
    """)
    
    # 检查依赖
    if not HAS_PYWENCAI:
        st.error("❌ pywencai库未安装或不可用")
        st.info(f"错误详情: {PYWENCAI_ERROR}")
        st.code("pip install pywencai", language="bash")
        return
    
    if not HAS_CHINESE_CALENDAR:
        st.warning("⚠️ chinese_calendar库未安装，将使用简化的交易日判断")
        with st.expander("安装说明"):
            st.code("pip install chinesecalendar", language="bash")
    
    st.markdown("---")
    
    # 参数配置
    st.subheader("🔧 参数设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 日期选择 - 默认今天
        today = datetime.now().date()
        selected_date = st.date_input(
            "📅 选择日期",
            value=today,
            max_value=today,
            help="选择要分析的交易日"
        )
    
    with col2:
        # 市值筛选
        market_cap = st.number_input(
            "💰 市值筛选（亿）",
            min_value=0,
            max_value=10000,
            value=50,
            step=10,
            help="筛选市值大于此值的股票"
        )
    
    # 查询策略选择
    st.markdown("##### 🎯 选择查询策略")
    
    strategy_options = {
        "竞价大单买入": f"{selected_date.strftime('%Y%m%d')}竞价大单买入,市值>{market_cap}亿",
        "竞价放量拉升": f"{selected_date.strftime('%Y%m%d')}竞价放量拉升,市值>{market_cap}亿",
        "竞价异动": f"{selected_date.strftime('%Y%m%d')}竞价异动,市值>{market_cap}亿",
        "竞价涨幅>3%": f"{selected_date.strftime('%Y%m%d')}竞价涨幅>3%,市值>{market_cap}亿",
        "竞价涨幅>5%": f"{selected_date.strftime('%Y%m%d')}竞价涨幅>5%,市值>{market_cap}亿",
        "自定义查询": ""
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_strategy = st.selectbox(
            "策略模板",
            list(strategy_options.keys()),
            help="选择预设策略或自定义查询"
        )
    
    with col2:
        if st.button("🔍 开始分析", type="primary", use_container_width=True):
            st.session_state.run_auction_analysis = True
    
    # 如果选择自定义查询
    if selected_strategy == "自定义查询":
        custom_query = st.text_area(
            "✏️ 自定义查询条件",
            value=f"{selected_date.strftime('%Y%m%d')}竞价异动,市值>{market_cap}亿",
            height=80,
            help="使用问财语法编写查询条件"
        )
        query = custom_query
    else:
        query = strategy_options[selected_strategy]
        st.info(f"💡 查询条件: `{query}`")
    
    # 执行分析
    if st.session_state.get('run_auction_analysis', False):
        st.markdown("---")
        run_strategy(query, selected_date, market_cap)
        st.session_state.run_auction_analysis = False

if __name__ == "__main__":
    display_auction_analysis()

