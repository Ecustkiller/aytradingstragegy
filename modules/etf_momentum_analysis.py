"""
ETF动量分析模块
基于三大核心因子的ETF动量评分与可视化系统
"""

import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from datetime import datetime, timedelta
import warnings
from .cache_manager import cached_function, display_cache_controls
warnings.filterwarnings('ignore')

# 初始化ETF数据库（A股+港股）
ETF_DATABASE = {
    "银行ETF": "512800",
    "黄金ETF": "518880", 
    "港股创新药ETF": "513120",
    "港股互联网ETF": "513770",
    "半导体ETF": "512480",
    "煤炭ETF": "515220",
    "沪深300ETF": "510300",
    "中证500ETF": "510500",
    "创50ETF": "159681",
    "科创芯片50ETF": "588200",
    "新能源ETF": "516160",
    "医药ETF": "512120",
    "军工ETF": "512660",
    "消费ETF": "159928",
    "地产ETF": "512200",
    "证券ETF": "512880",
    "5G ETF": "515050",
    "芯片ETF": "159995",
    "白酒ETF": "512690",
    "食品ETF": "515710"
}

class ETFMomentumAnalyzer:
    """ETF动量分析器"""
    
    def __init__(self):
        self.etf_database = ETF_DATABASE
        
    @st.cache_data(ttl=600)
    def fetch_etf_data(_self, symbol, start_date):
        """获取ETF历史数据"""
"""
ETF动量分析模块
基于三大核心因子的ETF动量评分与可视化系统
"""

import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 初始化ETF数据库（A股+港股）
ETF_DATABASE = {
    "银行ETF": "512800",
    "黄金ETF": "518880", 
    "港股创新药ETF": "513120",
    "港股互联网ETF": "513770",
    "半导体ETF": "512480",
    "煤炭ETF": "515220",
    "沪深300ETF": "510300",
    "中证500ETF": "510500",
    "创50ETF": "159681",
    "科创芯片50ETF": "588200",
    "新能源ETF": "516160",
    "医药ETF": "512120",
    "军工ETF": "512660",
    "消费ETF": "159928",
    "地产ETF": "512200",
    "证券ETF": "512880",
    "5G ETF": "515050",
    "芯片ETF": "159995",
    "白酒ETF": "512690",
    "食品ETF": "515710"
}

class ETFMomentumAnalyzer:
    """ETF动量分析器"""
    
    def __init__(self):
        self.etf_database = ETF_DATABASE
        
"""
ETF动量分析模块
基于三大核心因子的ETF动量评分与可视化系统
"""

import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 初始化ETF数据库（A股+港股）
ETF_DATABASE = {
    "银行ETF": "512800",
    "黄金ETF": "518880", 
    "港股创新药ETF": "513120",
    "港股互联网ETF": "513770",
    "半导体ETF": "512480",
    "煤炭ETF": "515220",
    "沪深300ETF": "510300",
    "中证500ETF": "510500",
    "创50ETF": "159681",
    "科创芯片50ETF": "588200",
    "新能源ETF": "516160",
    "医药ETF": "512120",
    "军工ETF": "512660",
    "消费ETF": "159928",
    "地产ETF": "512200",
    "证券ETF": "512880",
    "5G ETF": "515050",
    "芯片ETF": "159995",
    "白酒ETF": "512690",
    "食品ETF": "515710"
}

@st.cache_data(ttl=600)
def fetch_etf_data(symbol, start_date):
    """获取ETF历史数据"""
    try:
        # 使用AKShare获取ETF历史数据
        df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust="qfq")
        
        # 列名标准化处理
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open', 
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        # 日期处理
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 筛选日期范围
        return df[df.index >= pd.to_datetime(start_date)]
        
    except Exception as e:
        print(f"获取ETF数据失败 {symbol}: {str(e)}")
        return pd.DataFrame()

class ETFMomentumAnalyzer:
    """ETF动量分析器"""
    
    def __init__(self):
        self.etf_database = ETF_DATABASE
    
    def calculate_momentum_scores(self, df, date, trend_window=25):
        """
        计算ETF三大核心因子得分
        :param df: 包含OHLCV数据的DataFrame
        :param date: 指定评估日期
        :param trend_window: 趋势计算窗口
        :return: 字典格式的评分结果
        """
        try:
            # 筛选指定日期前的数据
            df_sub = df[df.index <= date].iloc[-trend_window * 2:]
            if len(df_sub) < trend_window:
                return {"错误": "数据不足"}
            
            # 1. 趋势强度因子（线性回归斜率+R²）
            x = np.arange(len(df_sub))
            y = np.log(df_sub['close'])
            slope, _, r_value, _, _ = stats.linregress(x, y)
            trend_score = (slope * 250) * (r_value ** 2)  # 年化斜率×R平方
            
            # 2. 动量因子（5日+10日收益率）
            roc_5 = (df_sub['close'].iloc[-1] / df_sub['close'].iloc[-6] - 1) * 100 if len(df_sub) >= 6 else 0
            roc_10 = (df_sub['close'].iloc[-1] / df_sub['close'].iloc[-11] - 1) * 100 if len(df_sub) >= 11 else 0
            momentum_score = 0.6 * roc_5 + 0.4 * roc_10  # 短期动量加权
            
            # 3. 量能因子（成交量均线比）
            vol_ma_short = df_sub['volume'].rolling(5).mean().iloc[-1]
            vol_ma_long = df_sub['volume'].rolling(20).mean().iloc[-1]
            volume_score = np.log(vol_ma_short / vol_ma_long) if vol_ma_long > 0 else 0
            
            # 综合得分（归一化到0-100分）
            total_score = 40 * trend_score + 35 * momentum_score + 25 * volume_score
            
            return {
                '趋势强度': round(trend_score, 2),
                '动量得分': round(momentum_score, 2), 
                '量能指标': round(volume_score, 2),
                '综合评分': max(0, min(100, round(total_score, 2)))
            }
            
        except Exception as e:
            print(f"计算动量得分失败: {str(e)}")
            return {"错误": str(e)}
    
    def generate_plotly_chart(self, df, etf_name, days=60):
        """生成带移动平均线的K线图"""
        try:
            df = df.tail(days).copy()
            
            # 确保数据格式正确
            if 'close' not in df.columns:
                return None
            
            # 计算移动平均线
            df['MA5'] = df['close'].rolling(5).mean()
            df['MA20'] = df['close'].rolling(20).mean()
            
            # 创建子图：主图为K线图，副图为成交量
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                row_heights=[0.7, 0.3],
                specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
            )
            
            # 添加K线图
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='K线',
                    increasing_line_color='#ef5350',  # 上涨红色
                    decreasing_line_color='#26a69a'  # 下跌绿色
                ),
                row=1, col=1
            )
            
            # 添加5日均线
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['MA5'],
                    name='5日均线',
                    line=dict(color='#1f77b4', width=1.5),
                    opacity=0.8
                ),
                row=1, col=1
            )
            
            # 添加20日均线
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['MA20'],
                    name='20日均线',
                    line=dict(color='#ff7f0e', width=1.5),
                    opacity=0.8
                ),
                row=1, col=1
            )
            
            # 添加成交量柱状图
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='成交量',
                    marker_color='#7f7f7f',
                    opacity=0.6
                ),
                row=2, col=1
            )
            
            # 设置布局
            fig.update_layout(
                title=f'{etf_name} - 最近{days}个交易日走势',
                xaxis_title='日期',
                yaxis_title='价格',
                showlegend=True,
                hovermode='x unified',
                template='plotly_white',
                height=600,
                margin=dict(l=50, r=50, t=60, b=50)
            )
            
            # 设置Y轴标题
            fig.update_yaxes(title_text="价格", row=1, col=1)
            fig.update_yaxes(title_text="成交量", row=2, col=1)
            
            # 禁用范围选择器
            fig.update_layout(xaxis_rangeslider_visible=False)
            
            return fig
            
        except Exception as e:
            print(f"生成图表失败: {str(e)}")
            return None

def display_etf_momentum_analysis():
    """显示ETF动量分析界面"""
    
    st.header("📊 ETF动量评分与可视化系统")
    st.markdown("基于三大核心因子的ETF动量分析：趋势强度、动量得分、量能指标")
    
    # 创建分析器实例
    analyzer = ETFMomentumAnalyzer()
    
    # 参数设置区域
    st.subheader("📋 分析参数设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 日期选择器
        max_date = datetime.now() - timedelta(days=1)
        selected_date = st.date_input(
            "选择评估日期",
            value=max_date,
            max_value=max_date,
            help="选择进行动量评分的基准日期"
        )
        
        # 数据开始日期
        start_date = st.date_input(
            "数据开始日期",
            value=selected_date - timedelta(days=365),
            help="历史数据的开始日期，建议至少1年"
        )
    
    with col2:
        # ETF多选
        selected_etfs = st.multiselect(
            "选择ETF进行分析",
            options=list(ETF_DATABASE.keys()),
            default=["银行ETF", "港股创新药ETF", "沪深300ETF"],
            help="可以选择多个ETF进行对比分析"
        )
        
        # 趋势计算窗口
        trend_window = st.slider(
            "趋势计算窗口(交易日)",
            min_value=20,
            max_value=60,
            value=25,
            help="用于计算趋势强度的时间窗口"
        )
    
    # 高级设置
    with st.expander("🔧 高级设置", expanded=False):
        st.markdown("**因子权重调整**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend_weight = st.slider("趋势强度权重", 0, 100, 40, help="趋势强度因子的权重")
        with col2:
            momentum_weight = st.slider("动量得分权重", 0, 100, 35, help="动量得分因子的权重")
        with col3:
            volume_weight = st.slider("量能指标权重", 0, 100, 25, help="量能指标因子的权重")
        
        # 图表设置
        chart_days = st.slider("K线图显示天数", 30, 120, 60, help="K线图显示的交易日数量")
        
        # 缓存控制
        if st.button("🗑️ 清除数据缓存"):
            st.cache_data.clear()
            st.success("缓存已清除")
    
    # 分析按钮
    if st.button("🚀 开始ETF动量分析", type="primary", width="stretch"):
        
        if not selected_etfs:
            st.warning("⚠️ 请至少选择一个ETF进行分析")
            return
        
        # 初始化结果存储
        results = []
        charts = []
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 遍历选中的ETF
        for i, etf_name in enumerate(selected_etfs):
            progress = (i + 1) / len(selected_etfs)
            progress_bar.progress(progress)
            status_text.text(f"正在分析 {etf_name}... ({i+1}/{len(selected_etfs)})")
            
            # 获取ETF代码
            symbol = ETF_DATABASE[etf_name]
            
            # 获取数据
            df = fetch_etf_data(symbol, start_date.strftime("%Y-%m-%d"))
            
            if df.empty:
                st.warning(f"⚠️ {etf_name}({symbol}) 数据获取失败，跳过")
                continue
            
            # 计算动量得分
            scores = analyzer.calculate_momentum_scores(
                df, 
                selected_date.strftime("%Y-%m-%d"), 
                trend_window
            )
            
            if "错误" in scores:
                st.warning(f"⚠️ {etf_name} 动量计算失败: {scores['错误']}")
                continue
            
            # 动态调整权重计算综合得分
            if trend_weight + momentum_weight + volume_weight > 0:
                total_weight = trend_weight + momentum_weight + volume_weight
                adjusted_score = (
                    (trend_weight / total_weight) * scores["趋势强度"] +
                    (momentum_weight / total_weight) * scores["动量得分"] +
                    (volume_weight / total_weight) * scores["量能指标"]
                )
                scores["综合评分"] = max(0, min(100, round(adjusted_score, 2)))
            
            # 生成图表
            fig = analyzer.generate_plotly_chart(df, etf_name, chart_days)
            
            # 获取最新价格信息
            latest_price = df['close'].iloc[-1] if not df.empty else 0
            price_change = ((df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100) if len(df) > 1 else 0
            
            # 存储结果
            results.append({
                "ETF名称": etf_name,
                "代码": symbol,
                "最新价格": round(latest_price, 3),
                "涨跌幅(%)": round(price_change, 2),
                "趋势强度": scores["趋势强度"],
                "动量得分": scores["动量得分"],
                "量能指标": scores["量能指标"],
                "综合评分": scores["综合评分"]
            })
            
            if fig:
                charts.append((etf_name, fig))
        
        # 清除进度条
        progress_bar.empty()
        status_text.empty()
        
        if not results:
            st.error("❌ 所有ETF数据获取失败，请检查网络连接或重试")
            return
        
        # 展示评分结果
        st.subheader("📊 ETF动量评分结果")
        
        df_results = pd.DataFrame(results)
        
        # 计算推荐权重
        total_score = df_results["综合评分"].sum()
        if total_score > 0:
            df_results["推荐权重(%)"] = (df_results["综合评分"] / total_score * 100).round(2)
        else:
            df_results["推荐权重(%)"] = 0
        
        # 添加评级
        def get_rating(score):
            if score >= 80:
                return "🟢 优秀"
            elif score >= 60:
                return "🟡 良好"
            elif score >= 40:
                return "🟠 一般"
            else:
                return "🔴 较差"
        
        df_results["评级"] = df_results["综合评分"].apply(get_rating)
        
        # 按综合评分排序
        df_results = df_results.sort_values("综合评分", ascending=False)
        
        # 显示结果表格
        st.dataframe(
            df_results,
            width="stretch",
            hide_index=True
        )
        
        # 显示最佳ETF建议
        if len(df_results) > 0:
            best_etf = df_results.iloc[0]
            st.success(f"""
            🎯 **投资建议**：
            - **最优ETF**: {best_etf['ETF名称']} ({best_etf['代码']})
            - **综合评分**: {best_etf['综合评分']} 分
            - **建议权重**: {best_etf['推荐权重(%)']}%
            - **当前价格**: ¥{best_etf['最新价格']} ({best_etf['涨跌幅(%)']}%)
            """)
        
        # 统计信息
        st.subheader("📈 分析统计")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("分析ETF数量", len(df_results))
        with col2:
            excellent_count = len(df_results[df_results['综合评分'] >= 80])
            st.metric("优秀评级数量", excellent_count)
        with col3:
            avg_score = df_results['综合评分'].mean()
            st.metric("平均综合评分", f"{avg_score:.2f}")
        with col4:
            max_score = df_results['综合评分'].max()
            st.metric("最高评分", f"{max_score:.2f}")
        
        # 展示图表
        if charts:
            st.subheader("📈 K线趋势分析")
            
            # 创建标签页
            if len(charts) > 1:
                tabs = st.tabs([name for name, _ in charts])
                for i, (etf_name, fig) in enumerate(charts):
                    with tabs[i]:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 显示该ETF的详细信息
                        etf_info = df_results[df_results['ETF名称'] == etf_name].iloc[0]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("综合评分", f"{etf_info['综合评分']:.2f}")
                        with col2:
                            st.metric("趋势强度", f"{etf_info['趋势强度']:.2f}")
                        with col3:
                            st.metric("动量得分", f"{etf_info['动量得分']:.2f}")
            else:
                # 只有一个图表时直接显示
                etf_name, fig = charts[0]
                st.plotly_chart(fig, use_container_width=True)
        
        # 数据导出
        st.subheader("💾 数据导出")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV导出
            csv_data = df_results.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载评分数据(CSV)",
                data=csv_data,
                file_name=f"etf_momentum_scores_{selected_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # 实时行情查看
            if st.button("📊 查看ETF实时行情", width="stretch"):
                try:
                    with st.spinner("获取实时行情数据..."):
                        spot_data = ak.fund_etf_spot_em()
                        
                        # 筛选分析的ETF
                        analyzed_codes = df_results['代码'].tolist()
                        filtered_spot = spot_data[spot_data['代码'].isin(analyzed_codes)]
                        
                        if not filtered_spot.empty:
                            st.dataframe(
                                filtered_spot[["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额"]],
                                width="stretch",
                                hide_index=True
                            )
                        else:
                            st.info("未找到相关ETF的实时行情数据")
                            
                except Exception as e:
                    st.error(f"获取实时行情失败: {str(e)}")
    
    # 使用说明
    st.markdown("---")
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 🎯 功能说明
        
        **ETF动量评分系统** 基于三大核心因子对ETF进行量化评分：
        
        #### 📊 评分因子
        1. **趋势强度** (40%权重)：基于线性回归斜率和R²值，衡量价格趋势的强度和稳定性
        2. **动量得分** (35%权重)：结合5日和10日收益率，评估短期价格动量
        3. **量能指标** (25%权重)：通过成交量均线比值，判断资金流入流出情况
        
        #### 🏆 评级标准
        - **🟢 优秀** (80-100分)：强势上涨，建议重点关注
        - **🟡 良好** (60-79分)：表现良好，可适量配置
        - **🟠 一般** (40-59分)：表现平平，谨慎操作
        - **🔴 较差** (0-39分)：表现较差，建议回避
        
        #### 💡 使用建议
        - 结合基本面分析，不要单纯依赖技术指标
        - 注意分散投资，控制单一ETF仓位
        - 定期重新评估，动态调整投资组合
        - 关注市场环境变化，适时调整策略
        
        #### ⚠️ 风险提示
        - 历史表现不代表未来收益
        - 投资有风险，入市需谨慎
        - 本工具仅供参考，不构成投资建议
        """)

if __name__ == "__main__":
    display_etf_momentum_analysis()