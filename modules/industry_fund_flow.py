"""
行业资金流向热力图模块 - 展示行业资金流向市场地图
数据来源：同花顺 (data.10jqka.com.cn)
"""
import streamlit as st
import plotly.express as px
import pandas as pd
import io
import requests
from bs4 import BeautifulSoup
import py_mini_racer
from .logger_config import get_logger
from .error_handler import safe_execute

logger = get_logger(__name__)


@st.cache_data(ttl=600)
def get_zijindongxiang_data():
    """
    获取行业资金流向数据
    
    Returns:
        pd.DataFrame: 行业资金流向数据
    """
    try:
        from akshare.datasets import get_ths_js
        js_file_path = get_ths_js("ths.js")
    except ImportError:
        st.error("请安装 akshare 库: pip install akshare")
        logger.error("akshare 库未安装")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"无法获取 ths.js 文件: {e}")
        logger.error(f"获取 ths.js 文件失败: {e}", exc_info=True)
        return pd.DataFrame()
    
    def _get_file_content_ths(file_path: str) -> str:
        """读取 ths.js 文件内容"""
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    
    try:
        js_code = py_mini_racer.MiniRacer()
        js_content = _get_file_content_ths(js_file_path)
        js_code.eval(js_content)
        v_code = js_code.call("v")
        
        headers = {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "hexin-v": v_code,
            "Host": "data.10jqka.com.cn",
            "Pragma": "no-cache",
            "Referer": "http://data.10jqka.com.cn/funds/hyzjl/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
        
        initial_url = "http://data.10jqka.com.cn/funds/hyzjl/field/tradezdf/order/desc/ajax/1/free/1/"
        
        r = requests.get(initial_url, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, features="lxml")
        raw_page = soup.find(name="span", attrs={"class": "page_info"}).text
        page_num = int(raw_page.split("/")[1])
        
        logger.info(f"获取到 {page_num} 页数据")
        
        url_template = "http://data.10jqka.com.cn/funds/hyzjl/field/tradezdf/order/desc/ajax/1/free/{}/"
        big_df = pd.DataFrame()
        
        progress_bar = st.progress(0, text="正在抓取数据...")
        
        for i, page in enumerate(range(1, page_num + 1)):
            current_url = url_template.format(page)
            try:
                r = requests.get(current_url, headers=headers, timeout=30)
                r.raise_for_status()
                temp_df = pd.read_html(io.StringIO(r.text))[0]
                big_df = pd.concat(objs=[big_df, temp_df], ignore_index=True)
                logger.debug(f"第 {page} 页抓取成功，共 {len(temp_df)} 条数据")
            except Exception as e:
                logger.warning(f"第 {page} 页抓取失败，已跳过。错误: {e}")
                st.warning(f"第 {page} 页抓取失败，已跳过。错误: {e}")
                continue
            finally:
                progress_bar.progress((i + 1) / page_num, text=f"正在抓取第 {i + 1}/{page_num} 页...")
        
        progress_bar.empty()
        
        # 关键修复：在返回数据前进行去重
        if not big_df.empty:
            original_count = len(big_df)
            big_df.drop_duplicates(inplace=True)
            removed_count = original_count - len(big_df)
            if removed_count > 0:
                logger.info(f"去重完成：原始 {original_count} 条，去重后 {len(big_df)} 条，移除 {removed_count} 条重复数据")
        
        logger.info(f"数据获取完成，共 {len(big_df)} 条数据")
        return big_df
        
    except Exception as e:
        logger.error(f"获取行业资金流向数据失败: {e}", exc_info=True)
        st.error(f"获取数据失败: {e}")
        return pd.DataFrame()


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """清洗数值序列"""
    if series.dtype == 'object':
        series = series.astype(str).str.replace('%', '', regex=False)
        series = series.str.replace('--', '0', regex=False)
        series = series.str.replace(',', '', regex=False)
    return pd.to_numeric(series, errors='coerce')


def display_industry_fund_flow():
    """显示行业资金流向热力图界面"""
    st.title("行业资金流向市场地图")
    st.markdown("数据来源：同花顺 (data.10jqka.com.cn)")
    
    # 侧边栏控件
    with st.sidebar:
        st.header("控制面板")
        
        chart_type = st.radio("选择图表类型", ("市场地图", "散点图"), index=0)
        
        color_by_option = st.selectbox("热力图颜色代表", ("净额(亿)", "流入资金(亿)"), index=0)
        size_by_option = st.selectbox("热力图大小代表", ("净额(亿)", "流入资金(亿)"), index=0)
        
        st.markdown("---")
        st.subheader("图表排序依据")
        
        sort_options = {
            "行业名称": "行业名称",
            "行业涨跌幅(%)": "行业涨跌幅",
            "净额(亿)": "净额(亿)",
            "流入资金(亿)": "流入资金(亿)",
            "公司家数": "公司家数",
            "领涨股涨跌幅(%)": "领涨股涨跌幅",
        }
        sort_by_col = st.selectbox("排序依据", options=list(sort_options.keys()), index=2)
        sort_ascending = st.checkbox("升序排列", value=False)
        
        st.markdown("---")
        if st.button("🔄 刷新数据", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # 数据加载与处理
    with st.spinner("正在加载数据，请稍候..."):
        df = get_zijindongxiang_data()
    
    if df.empty:
        st.error("未能获取到数据，请检查网络连接或稍后重试。")
        st.info("💡 **提示：**\n- 检查网络连接\n- 确认 akshare 库已安装\n- 稍后重试")
        return
    
    # 数据清洗和准备
    column_map = {
        '行业': '行业名称',
        '涨跌幅': '行业涨跌幅',
        '流入资金(亿)': '流入资金(亿)',
        '流出资金(亿)': '流出资金(亿)',
        '净额(亿)': '净额(亿)',
        '公司家数': '公司家数',
        '领涨股': '领涨股',
        '涨跌幅.1': '领涨股涨跌幅',
        '当前价(元)': '当前价(元)',
    }
    df.rename(columns=column_map, inplace=True)
    
    numeric_cols_to_clean = [
        '行业涨跌幅', '流入资金(亿)', '流出资金(亿)', '净额(亿)',
        '公司家数', '领涨股涨跌幅', '当前价(元)'
    ]
    
    for col in numeric_cols_to_clean:
        if col in df.columns:
            df[col] = clean_numeric_series(df[col])
    
    # 根据用户选择对数据进行排序，用于图表
    df_plot = df.sort_values(by=sort_options[sort_by_col], ascending=sort_ascending)
    df_table = df_plot.copy()

    # 绘制图表
    st.subheader(f"行业资金流向 ({chart_type})")

    # 确定颜色和大小列
    if color_by_option == "净额(亿)":
        color_col = '净额(亿)'
    else:
        color_col = '流入资金(亿)'

    if size_by_option == "净额(亿)":
        size_col = '净额(亿)'
    else:
        size_col = '流入资金(亿)'

    # 确保数值列的正确类型
    numeric_columns = ['净额(亿)', '流入资金(亿)', '行业涨跌幅', '公司家数']
    for col in numeric_columns:
        if col in df_plot.columns:
            df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce').fillna(0)

    # 添加绝对值列用于大小，确保为正值
    df_plot['净额(亿)_abs'] = df_plot['净额(亿)'].abs()
    df_plot[size_col + '_abs'] = df_plot[size_col].abs()

    # 确保行业名称列为字符串类型
    df_plot['行业名称'] = df_plot['行业名称'].astype(str)

    # 清理无效数据
    df_plot.dropna(subset=[color_col, size_col + '_abs', '行业名称'], inplace=True)

    # 额外的数据清理：确保没有无穷大值
    df_plot = df_plot.replace([float('inf'), float('-inf')], float('nan')).dropna()
    
    if df_plot.empty:
        st.error("绘图数据为空，可能是因为关键列（如净额或涨跌幅）包含无效数据。")
        return
    
    # 绘制市场地图
    if chart_type == "市场地图":
        st.caption("注意：市场地图的布局由算法根据块的大小和颜色自动决定，不完全等同于列表排序。")

        try:
            # 准备数据 - 确保数据格式正确
            plot_data = df_plot.copy()

            # 重置索引以避免索引相关的错误
            plot_data = plot_data.reset_index(drop=True)

            # 简化数据结构，只保留必要的列
            simplified_data = {
                '行业名称': plot_data['行业名称'].tolist(),
                'values': plot_data[size_col + '_abs'].tolist(),
                'colors': plot_data[color_col].tolist(),
                '行业涨跌幅': plot_data['行业涨跌幅'].tolist(),
                '净额(亿)': plot_data['净额(亿)'].tolist(),
                '领涨股': plot_data['领涨股'].tolist(),
                '领涨股涨跌幅': plot_data['领涨股涨跌幅'].tolist()
            }

            # 创建简化的DataFrame
            import plotly.graph_objects as go
            fig = go.Figure(go.Treemap(
                labels=simplified_data['行业名称'],
                values=simplified_data['values'],
                parents=["所有行业"] * len(simplified_data['行业名称']),
                marker_colors=simplified_data['colors'],
                hovertemplate='<b>%{label}</b><br>行业涨跌幅: %{customdata[0]:.2f}%<br>净额: %{customdata[1]:.2f} 亿<br>领涨股: %{customdata[2]} (%{customdata[3]:.2f}%)<extra></extra>',
                customdata=list(zip(simplified_data['行业涨跌幅'], simplified_data['净额(亿)'], simplified_data['领涨股'], simplified_data['领涨股涨跌幅'])),
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title=color_by_option)
            ))

            # 更新布局
            fig.update_layout(
                title=f"行业资金流向 - 颜色: {color_by_option} | 大小: {size_by_option} (绝对值)",
                margin=dict(t=80, l=25, r=25, b=25),
                font=dict(size=12)
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            logger.error(f"绘制市场地图失败: {e}", exc_info=True)
            st.error(f"绘制图表失败: {e}")
            st.info("💡 **可能的解决方案：**\n- 尝试刷新数据\n- 检查网络连接\n- 稍后重试")

            # 提供备用的简单表格显示
            st.subheader("📊 数据表格（备用显示）")
            st.dataframe(df_plot[['行业名称', '行业涨跌幅', '净额(亿)', '流入资金(亿)', '公司家数']].head(20))
    
    # 绘制散点图
    elif chart_type == "散点图":
        try:
            # 准备数据 - 确保数据格式正确
            plot_data = df_plot.copy()

            # 重置索引以避免索引相关的错误
            plot_data = plot_data.reset_index(drop=True)

            # 使用 plotly.graph_objects 直接创建图表
            import plotly.graph_objects as go

            fig = go.Figure()

            # 添加散点轨迹
            fig.add_trace(go.Scatter(
                x=plot_data['公司家数'],
                y=plot_data['行业名称'],
                mode='markers',
                marker=dict(
                    size=plot_data[size_col + '_abs'] / plot_data[size_col + '_abs'].max() * 30 + 5,  # 归一化大小
                    color=plot_data[color_col],
                    colorscale='RdYlGn_r',
                    showscale=True,
                    colorbar=dict(title=color_by_option),
                    sizemode='diameter',
                    line=dict(width=1, color='DarkSlateGrey')
                ),
                customdata=plot_data[['行业涨跌幅', '净额(亿)', '领涨股', '领涨股涨跌幅']].values,
                hovertemplate='<b>%{y}</b><br>公司家数: %{x}<br>行业涨跌幅: %{customdata[0]:.2f}%<br>净额: %{customdata[1]:.2f} 亿<br>领涨股: %{customdata[2]} (%{customdata[3]:.2f}%)<extra></extra>',
                name='行业'
            ))

            # 更新布局
            fig.update_layout(
                title=f"行业资金流向散点图 - 颜色: {color_by_option} | 大小: {size_by_option} (绝对值) | X轴: 公司家数",
                xaxis_title='公司家数',
                yaxis_title='行业名称',
                height=800,
                yaxis=dict(categoryorder='array', categoryarray=plot_data['行业名称'].tolist()),
                font=dict(size=12),
                margin=dict(l=150, r=50, t=80, b=50)
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            logger.error(f"绘制散点图失败: {e}", exc_info=True)
            st.error(f"绘制图表失败: {e}")
            st.info("💡 **可能的解决方案：**\n- 尝试刷新数据\n- 检查网络连接\n- 稍后重试")

            # 提供备用的简单表格显示
            st.subheader("📊 数据表格（备用显示）")
            st.dataframe(df_plot[['行业名称', '行业涨跌幅', '净额(亿)', '流入资金(亿)', '公司家数']].head(20))
    
    # 显示原始数据表格
    st.subheader("详细数据表")
    st.dataframe(df_table, use_container_width=True)
    
    # 数据下载
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df_table.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下载CSV文件",
            data=csv,
            file_name=f"行业资金流向_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

