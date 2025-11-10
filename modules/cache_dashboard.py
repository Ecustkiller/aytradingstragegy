"""
缓存管理仪表板
提供缓存状态查看、清理等功能
"""

import streamlit as st
import os
import json
from datetime import datetime
from .smart_data_manager import smart_data_manager

def show_cache_dashboard():
    """显示缓存管理仪表板"""
    st.markdown("### 📦 缓存管理")
    
    # 获取缓存统计
    cache_stats = smart_data_manager.get_cache_stats()
    
    if 'error' in cache_stats:
        st.error(f"获取缓存统计失败: {cache_stats['error']}")
        return
    
    # 显示缓存统计
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("缓存文件数", cache_stats['cache_files'])
    
    with col2:
        st.metric("缓存大小", f"{cache_stats['total_size_mb']} MB")
    
    with col3:
        st.metric("近期请求", cache_stats['recent_requests'])
    
    with col4:
        st.metric("限流阈值", f"{cache_stats['rate_limit']}/分钟")
    
    # 缓存配置
    st.markdown("#### ⚙️ 缓存配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 限流设置
        new_rate_limit = st.number_input(
            "每分钟最大请求数", 
            min_value=10, 
            max_value=100, 
            value=smart_data_manager.max_requests_per_minute,
            help="降低此值可以减少被封IP的风险"
        )
        
        if new_rate_limit != smart_data_manager.max_requests_per_minute:
            smart_data_manager.max_requests_per_minute = new_rate_limit
            st.success(f"限流设置已更新为 {new_rate_limit} 请求/分钟")
    
    with col2:
        # 缓存清理
        clear_hours = st.selectbox(
            "清理多少小时前的缓存",
            [1, 6, 12, 24, 48, 72],
            index=3
        )
        
        if st.button("🧹 清理过期缓存"):
            with st.spinner("正在清理缓存..."):
                smart_data_manager.clear_cache(older_than_hours=clear_hours)
                st.success("缓存清理完成！")
                st.experimental_rerun()
    
    # 缓存详情
    if st.checkbox("显示缓存详情"):
        show_cache_details()

def show_cache_details():
    """显示缓存文件详情"""
    st.markdown("#### 📋 缓存文件详情")
    
    try:
        cache_dir = smart_data_manager.cache_dir
        if not os.path.exists(cache_dir):
            st.info("缓存目录不存在")
            return
        
        cache_files = []
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(cache_dir, filename)
                stat = os.stat(filepath)
                
                # 尝试读取缓存内容获取更多信息
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        data_type = "DataFrame" if 'dataframe' in cache_data else "Other"
                except:
                    data_type = "Unknown"
                
                cache_files.append({
                    '文件名': filename[:20] + '...' if len(filename) > 20 else filename,
                    '大小(KB)': round(stat.st_size / 1024, 2),
                    '修改时间': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                    '数据类型': data_type
                })
        
        if cache_files:
            import pandas as pd
            df = pd.DataFrame(cache_files)
            st.dataframe(df, width="stretch")
        else:
            st.info("暂无缓存文件")
            
    except Exception as e:
        st.error(f"读取缓存详情失败: {e}")

def show_rate_limit_status():
    """显示限流状态"""
    st.markdown("#### 🚦 限流状态")
    
    current_requests = len(smart_data_manager.request_times)
    max_requests = smart_data_manager.max_requests_per_minute
    
    # 进度条显示当前请求数
    progress = min(current_requests / max_requests, 1.0)
    
    if progress < 0.7:
        color = "normal"
        status = "正常"
    elif progress < 0.9:
        color = "warning" 
        status = "接近限制"
    else:
        color = "error"
        status = "即将限流"
    
    st.progress(progress)
    st.caption(f"当前状态: {status} ({current_requests}/{max_requests})")
    
    # 显示建议
    if progress > 0.8:
        st.warning("⚠️ 请求频率较高，建议稍作等待以避免被限流")
    elif progress < 0.3:
        st.success("✅ 当前请求频率正常，可以继续操作")

# 在主界面中集成缓存管理
def integrate_cache_management():
    """在侧边栏集成缓存管理"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📦 数据缓存")
        
        # 简化的缓存状态
        cache_stats = smart_data_manager.get_cache_stats()
        if 'error' not in cache_stats:
            st.metric("缓存文件", cache_stats['cache_files'])
            st.metric("缓存大小", f"{cache_stats['total_size_mb']} MB")
            
            # 限流状态指示器
            current_requests = len(smart_data_manager.request_times)
            max_requests = smart_data_manager.max_requests_per_minute
            progress = min(current_requests / max_requests, 1.0)
            
            if progress > 0.8:
                st.warning(f"⚠️ 请求频率: {current_requests}/{max_requests}")
            else:
                st.success(f"✅ 请求频率: {current_requests}/{max_requests}")
        
        # 快速清理按钮
        if st.button("🧹 清理1小时前缓存", key="quick_clear"):
            smart_data_manager.clear_cache(older_than_hours=1)
            st.success("缓存已清理！")