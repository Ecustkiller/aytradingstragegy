"""
Z哥战法数据管理模块
负责本地CSV数据的下载、存储和加载
"""
import os
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# 数据存储目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'zgzf_data')

def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"✅ 创建数据目录: {DATA_DIR}")
    return DATA_DIR

def get_stock_list_from_index(index_code: str) -> Optional[List[str]]:
    """
    从指数获取成分股列表
    
    Args:
        index_code: 指数代码 (000300=沪深300, 000905=中证500, 000016=上证50)
    
    Returns:
        股票代码列表
    """
    try:
        import akshare as ak
        
        index_map = {
            "000300": "沪深300",
            "000905": "中证500",
            "000016": "上证50"
        }
        
        print(f"📊 正在获取{index_map.get(index_code, index_code)}成分股...")
        df = ak.index_stock_cons_csindex(symbol=index_code)
        
        if df is not None and not df.empty:
            stock_list = df['成分券代码'].tolist()
            print(f"✅ 获取到 {len(stock_list)} 只成分股")
            return stock_list
        else:
            print("❌ 获取成分股失败")
            return None
    except Exception as e:
        print(f"❌ 获取成分股出错: {e}")
        return None

def download_stock_data_to_csv(
    stock_code: str,
    start_date: str,
    end_date: str,
    data_source: str = "AKShare"
) -> bool:
    """
    下载单只股票数据并保存为CSV
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        data_source: 数据源
    
    Returns:
        是否成功
    """
    try:
        from .data_loader import get_stock_data
        
        df = get_stock_data(
            symbol=stock_code,
            start=start_date,
            end=end_date,
            data_source=data_source,
            period_type='daily'
        )
        
        if df is None or df.empty:
            return False
        
        # 保存到CSV
        ensure_data_dir()
        csv_path = os.path.join(DATA_DIR, f"{stock_code}.csv")
        
        # 保存时包含日期索引
        df.to_csv(csv_path, encoding='utf-8-sig')
        
        return True
    except Exception as e:
        print(f"❌ {stock_code} 下载失败: {e}")
        return False

def batch_download_stocks(
    stock_list: List[str],
    start_date: str,
    end_date: str,
    data_source: str = "AKShare",
    progress_callback=None
) -> Dict[str, str]:
    """
    批量下载股票数据
    
    Args:
        stock_list: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        data_source: 数据源
        progress_callback: 进度回调函数 (current, total, code)
    
    Returns:
        {'success': [...], 'failed': [...]}
    """
    success_list = []
    failed_list = []
    
    total = len(stock_list)
    
    for idx, code in enumerate(stock_list):
        if progress_callback:
            progress_callback(idx + 1, total, code)
        
        if download_stock_data_to_csv(code, start_date, end_date, data_source):
            success_list.append(code)
        else:
            failed_list.append(code)
        
        # 避免请求过快
        time.sleep(0.1)
    
    return {
        'success': success_list,
        'failed': failed_list
    }

def load_stock_data_from_csv(stock_code: str) -> Optional[pd.DataFrame]:
    """
    从CSV加载股票数据
    
    Args:
        stock_code: 股票代码
    
    Returns:
        DataFrame或None
    """
    try:
        csv_path = os.path.join(DATA_DIR, f"{stock_code}.csv")
        
        if not os.path.exists(csv_path):
            return None
        
        # 读取CSV，第一列作为索引（日期）
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        
        return df
    except Exception as e:
        print(f"❌ {stock_code} 加载失败: {e}")
        return None

def get_local_stock_list() -> List[str]:
    """
    获取本地已下载的股票列表
    
    Returns:
        股票代码列表
    """
    ensure_data_dir()
    
    stock_list = []
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.csv'):
            stock_code = filename.replace('.csv', '')
            stock_list.append(stock_code)
    
    return sorted(stock_list)

def load_all_local_stocks() -> Dict[str, pd.DataFrame]:
    """
    加载所有本地股票数据
    
    Returns:
        {股票代码: DataFrame} 字典
    """
    stock_list = get_local_stock_list()
    stock_data_dict = {}
    
    for code in stock_list:
        df = load_stock_data_from_csv(code)
        if df is not None and not df.empty and len(df) >= 60:
            stock_data_dict[code] = df
    
    return stock_data_dict

def get_data_info() -> Dict:
    """
    获取本地数据统计信息
    
    Returns:
        {'count': int, 'oldest': str, 'newest': str, 'total_size': str}
    """
    stock_list = get_local_stock_list()
    
    if not stock_list:
        return {
            'count': 0,
            'oldest': 'N/A',
            'newest': 'N/A',
            'total_size': '0 MB'
        }
    
    # 计算总大小
    total_size = 0
    oldest_date = None
    newest_date = None
    
    for code in stock_list:
        csv_path = os.path.join(DATA_DIR, f"{code}.csv")
        if os.path.exists(csv_path):
            total_size += os.path.getsize(csv_path)
            
            # 获取日期范围
            try:
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                if not df.empty:
                    file_oldest = df.index.min()
                    file_newest = df.index.max()
                    
                    if oldest_date is None or file_oldest < oldest_date:
                        oldest_date = file_oldest
                    if newest_date is None or file_newest > newest_date:
                        newest_date = file_newest
            except:
                continue
    
    return {
        'count': len(stock_list),
        'oldest': oldest_date.strftime('%Y-%m-%d') if oldest_date else 'N/A',
        'newest': newest_date.strftime('%Y-%m-%d') if newest_date else 'N/A',
        'total_size': f"{total_size / 1024 / 1024:.2f} MB"
    }

def clear_all_data():
    """清空所有本地数据"""
    stock_list = get_local_stock_list()
    
    for code in stock_list:
        csv_path = os.path.join(DATA_DIR, f"{code}.csv")
        try:
            os.remove(csv_path)
        except:
            pass
    
    print(f"✅ 已清空 {len(stock_list)} 个数据文件")


def display_data_management():
    """显示数据管理界面"""
    st.title("📦 Z哥战法 - 数据管理")
    
    st.markdown("""
    ### 数据管理说明
    
    批量选股需要提前下载股票数据到本地。本地数据的优势：
    - ⚡ **速度快**：无需实时请求API
    - 💰 **省成本**：减少API调用次数
    - 🔒 **稳定性**：不受网络波动影响
    
    **使用流程**：
    1. 选择股票池（沪深300/中证500/上证50）
    2. 点击"下载数据"批量下载
    3. 返回"Z哥战法选股"进行批量筛选
    """)
    
    st.markdown("---")
    
    # 当前数据统计
    st.subheader("📊 本地数据统计")
    
    info = get_data_info()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("股票数量", info['count'])
    
    with col2:
        st.metric("最早日期", info['oldest'])
    
    with col3:
        st.metric("最新日期", info['newest'])
    
    with col4:
        st.metric("占用空间", info['total_size'])
    
    if info['count'] > 0:
        with st.expander("📋 查看已下载股票列表"):
            stock_list = get_local_stock_list()
            # 每行显示10个
            cols_per_row = 10
            for i in range(0, len(stock_list), cols_per_row):
                row_stocks = stock_list[i:i+cols_per_row]
                st.text(", ".join(row_stocks))
    
    st.markdown("---")
    
    # 数据下载
    st.subheader("📥 批量下载数据")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stock_pool = st.selectbox(
            "选择股票池",
            ["沪深300", "中证500", "上证50", "自定义列表"]
        )
    
    with col2:
        data_source = st.selectbox("数据源", ["AKShare", "Tushare"])
    
    with col3:
        days = st.number_input("历史天数", min_value=30, max_value=1000, value=365, step=30)
    
    # 自定义列表
    if stock_pool == "自定义列表":
        custom_list = st.text_area(
            "输入股票代码（每行一个或逗号分隔）",
            value="600519\n000858\n601318",
            height=100
        )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 开始下载", type="primary", use_container_width=True):
            # 获取股票列表
            stock_list = []
            
            if stock_pool == "自定义列表":
                raw_input = custom_list.replace(',', '\n')
                stock_list = [s.strip() for s in raw_input.split('\n') if s.strip()]
            else:
                # 获取指数成分股
                index_map = {
                    "沪深300": "000300",
                    "中证500": "000905",
                    "上证50": "000016"
                }
                
                with st.spinner(f"正在获取{stock_pool}成分股..."):
                    stock_list = get_stock_list_from_index(index_map[stock_pool])
                
                if not stock_list:
                    st.error("获取成分股失败")
                    st.stop()
            
            if not stock_list:
                st.warning("股票列表为空")
                st.stop()
            
            st.info(f"📊 准备下载 {len(stock_list)} 只股票的数据...")
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(current, total, code):
                progress_bar.progress(current / total)
                status_text.text(f"正在下载: {code} ({current}/{total})")
            
            # 批量下载
            result = batch_download_stocks(
                stock_list,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                data_source,
                progress_callback
            )
            
            progress_bar.empty()
            status_text.empty()
            
            # 显示结果
            st.success(f"✅ 成功下载 {len(result['success'])} 只股票")
            
            if result['failed']:
                with st.expander(f"⚠️ {len(result['failed'])} 只股票下载失败"):
                    st.write(", ".join(result['failed']))
            
            # 刷新统计信息
            st.rerun()
    
    with col2:
        if st.button("🗑️ 清空所有数据", use_container_width=True):
            if info['count'] > 0:
                with st.spinner("正在清空数据..."):
                    clear_all_data()
                st.success("✅ 数据已清空")
                st.rerun()
            else:
                st.info("暂无数据需要清空")
    
    st.markdown("---")
    
    # 使用提示
    st.info("""
    💡 **下一步**：
    1. 下载完成后，返回"Z哥战法选股"模块
    2. 选择"批量选股"模式
    3. 选择"从本地数据"
    4. 开始筛选！
    """)


if __name__ == "__main__":
    display_data_management()

