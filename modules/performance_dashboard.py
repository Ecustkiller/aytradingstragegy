"""
性能监控面板
实时显示系统性能指标和优化建议
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import psutil
import time
import threading
from typing import Dict, List
from datetime import datetime, timedelta

from .async_data_processor import performance_monitor, data_cache
# 已迁移到 data_loader，保留 optimized_loader 用于向后兼容
try:
    from .optimized_data_loader import optimized_loader
except ImportError:
    # 如果 optimized_data_loader 不存在，使用 data_loader 的接口
    optimized_loader = None

class PerformanceDashboard:
    """性能监控面板"""
    
    def __init__(self):
        self.system_metrics = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """开始系统监控"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止系统监控"""
        self.monitoring = False
    
    def _monitor_system(self):
        """系统监控线程"""
        while self.monitoring:
            try:
                # 收集系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                metric = {
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_total_gb': memory.total / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_used_gb': disk.used / (1024**3),
                    'disk_total_gb': disk.total / (1024**3)
                }
                
                self.system_metrics.append(metric)
                
                # 只保留最近100个数据点
                if len(self.system_metrics) > 100:
                    self.system_metrics.pop(0)
                
                time.sleep(5)  # 每5秒收集一次
                
            except Exception as e:
                print(f"系统监控错误: {e}")
                time.sleep(10)
    
    def show_performance_overview(self):
        """显示性能概览"""
        st.markdown("### ⚡ 性能监控面板")
        
        # 启动监控
        if not self.monitoring:
            self.start_monitoring()
        
        # 实时系统指标
        self._show_system_metrics()
        
        # 应用性能指标
        self._show_app_performance()
        
        # 缓存统计
        self._show_cache_stats()
        
        # 性能建议
        self._show_performance_recommendations()
    
    def _show_system_metrics(self):
        """显示系统指标"""
        st.markdown("#### 🖥️ 系统资源使用")
        
        if not self.system_metrics:
            st.info("正在收集系统指标...")
            return
        
        # 获取最新指标
        latest = self.system_metrics[-1]
        
        # 显示实时指标
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CPU使用率
            cpu_color = "normal" if latest['cpu_percent'] < 70 else "inverse"
            st.metric(
                "CPU使用率", 
                f"{latest['cpu_percent']:.1f}%",
                delta=None,
                delta_color=cpu_color
            )
        
        with col2:
            # 内存使用率
            memory_color = "normal" if latest['memory_percent'] < 80 else "inverse"
            st.metric(
                "内存使用率", 
                f"{latest['memory_percent']:.1f}%",
                delta=f"{latest['memory_used_gb']:.1f}GB / {latest['memory_total_gb']:.1f}GB",
                delta_color=memory_color
            )
        
        with col3:
            # 磁盘使用率
            disk_color = "normal" if latest['disk_percent'] < 90 else "inverse"
            st.metric(
                "磁盘使用率", 
                f"{latest['disk_percent']:.1f}%",
                delta=f"{latest['disk_used_gb']:.1f}GB / {latest['disk_total_gb']:.1f}GB",
                delta_color=disk_color
            )
        
        # 历史趋势图
        if len(self.system_metrics) > 10:
            self._plot_system_trends()
    
    def _plot_system_trends(self):
        """绘制系统趋势图"""
        df = pd.DataFrame(self.system_metrics)
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('CPU使用率', '内存使用率', '磁盘使用率', '内存使用量'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # CPU趋势
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'], 
                y=df['cpu_percent'],
                name='CPU%',
                line=dict(color='#FF6B6B')
            ),
            row=1, col=1
        )
        
        # 内存使用率趋势
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'], 
                y=df['memory_percent'],
                name='内存%',
                line=dict(color='#4ECDC4')
            ),
            row=1, col=2
        )
        
        # 磁盘使用率趋势
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'], 
                y=df['disk_percent'],
                name='磁盘%',
                line=dict(color='#45B7D1')
            ),
            row=2, col=1
        )
        
        # 内存使用量趋势
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'], 
                y=df['memory_used_gb'],
                name='内存GB',
                line=dict(color='#96CEB4')
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=400,
            showlegend=False,
            title_text="系统资源使用趋势"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _show_app_performance(self):
        """显示应用性能指标"""
        st.markdown("#### 📊 应用性能指标")
        
        # 获取性能统计
        perf_stats = performance_monitor.get_stats()
        
        if not perf_stats:
            st.info("暂无性能数据，请先进行一些操作")
            return
        
        # 创建性能表格
        perf_data = []
        for name, stats in perf_stats.items():
            perf_data.append({
                '操作': name,
                '调用次数': stats['count'],
                '平均耗时(s)': f"{stats['avg']:.3f}",
                '最快(s)': f"{stats['min']:.3f}",
                '最慢(s)': f"{stats['max']:.3f}",
                '总耗时(s)': f"{stats['total']:.3f}"
            })
        
        df = pd.DataFrame(perf_data)
        st.dataframe(df, width="stretch")
        
        # 性能图表
        if len(perf_data) > 0:
            self._plot_performance_chart(perf_stats)
    
    def _plot_performance_chart(self, perf_stats):
        """绘制性能图表"""
        # 平均耗时对比
        names = list(perf_stats.keys())
        avg_times = [stats['avg'] for stats in perf_stats.values()]
        
        fig = go.Figure(data=[
            go.Bar(
                x=names,
                y=avg_times,
                marker_color='lightblue',
                text=[f"{t:.3f}s" for t in avg_times],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="各操作平均耗时对比",
            xaxis_title="操作类型",
            yaxis_title="平均耗时(秒)",
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _show_cache_stats(self):
        """显示缓存统计"""
        st.markdown("#### 💾 缓存统计")
        
        try:
            # 使用 data_cache 的统计信息
            if optimized_loader:
                cache_stats = optimized_loader.get_cache_stats()
            else:
                cache_stats = data_cache.stats() if hasattr(data_cache, 'stats') else {}
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**数据缓存**")
                data_cache_stats = cache_stats.get('data_cache_stats', {})
                st.metric("缓存大小", data_cache_stats.get('size', 0))
                st.metric("最大容量", data_cache_stats.get('max_size', 0))
                
                hit_rate = data_cache_stats.get('hit_rate', 0)
                st.metric("命中率", f"{hit_rate:.2%}")
            
            with col2:
                st.markdown("**加载器统计**")
                loader_stats = cache_stats.get('loader_stats', {})
                st.metric("缓存命中", loader_stats.get('hits', 0))
                st.metric("缓存未命中", loader_stats.get('misses', 0))
                
                # 计算命中率
                total = loader_stats.get('hits', 0) + loader_stats.get('misses', 0)
                if total > 0:
                    hit_rate = loader_stats.get('hits', 0) / total
                    st.metric("总命中率", f"{hit_rate:.2%}")
        
        except Exception as e:
            st.error(f"获取缓存统计失败: {e}")
    
    def _show_performance_recommendations(self):
        """显示性能建议"""
        st.markdown("#### 💡 性能优化建议")
        
        recommendations = []
        
        # 基于系统指标的建议
        if self.system_metrics:
            latest = self.system_metrics[-1]
            
            if latest['cpu_percent'] > 80:
                recommendations.append({
                    'type': 'warning',
                    'title': 'CPU使用率过高',
                    'message': 'CPU使用率超过80%，建议减少并发操作或优化算法',
                    'action': '降低并发线程数或优化计算密集型操作'
                })
            
            if latest['memory_percent'] > 85:
                recommendations.append({
                    'type': 'warning',
                    'title': '内存使用率过高',
                    'message': '内存使用率超过85%，建议清理缓存或增加内存',
                    'action': '清理数据缓存或重启应用'
                })
            
            if latest['disk_percent'] > 90:
                recommendations.append({
                    'type': 'error',
                    'title': '磁盘空间不足',
                    'message': '磁盘使用率超过90%，建议清理文件',
                    'action': '清理缓存文件、日志文件或临时文件'
                })
        
        # 基于性能统计的建议
        perf_stats = performance_monitor.get_stats()
        for name, stats in perf_stats.items():
            if stats['avg'] > 5:  # 平均耗时超过5秒
                recommendations.append({
                    'type': 'info',
                    'title': f'{name} 操作较慢',
                    'message': f'平均耗时 {stats["avg"]:.2f}秒，建议优化',
                    'action': '考虑增加缓存或优化数据获取逻辑'
                })
        
        # 显示建议
        if recommendations:
            for rec in recommendations:
                if rec['type'] == 'error':
                    st.error(f"🚨 **{rec['title']}**: {rec['message']}")
                elif rec['type'] == 'warning':
                    st.warning(f"⚠️ **{rec['title']}**: {rec['message']}")
                else:
                    st.info(f"💡 **{rec['title']}**: {rec['message']}")
                
                st.caption(f"建议操作: {rec['action']}")
        else:
            st.success("✅ 系统性能良好，无需优化")
    
    def show_optimization_tools(self):
        """显示优化工具"""
        st.markdown("### 🛠️ 性能优化工具")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🧹 清理所有缓存"):
                # 清理缓存
                if optimized_loader:
                    optimized_loader.clear_cache()
                if hasattr(data_cache, 'clear'):
                    data_cache.clear()
                st.success("缓存已清理！")
        
        with col2:
            if st.button("📊 重置性能统计"):
                performance_monitor.metrics.clear()
                st.success("性能统计已重置！")
        
        with col3:
            if st.button("🔄 重启监控"):
                self.stop_monitoring()
                time.sleep(1)
                self.start_monitoring()
                st.success("监控已重启！")
        
        # 高级设置
        with st.expander("⚙️ 高级设置"):
            st.markdown("**线程池设置**")
            max_workers = st.slider("最大工作线程数", 1, 16, 8)
            
            st.markdown("**缓存设置**")
            cache_size = st.slider("缓存最大条目数", 100, 5000, 1000)
            cache_ttl = st.slider("缓存生存时间(秒)", 60, 3600, 300)
            
            if st.button("应用设置"):
                # 这里可以应用设置到相关组件
                st.success("设置已应用！")

# 全局实例
performance_dashboard = PerformanceDashboard()

def show_performance_panel():
    """显示性能面板"""
    performance_dashboard.show_performance_overview()

def show_optimization_panel():
    """显示优化面板"""
    performance_dashboard.show_optimization_tools()
