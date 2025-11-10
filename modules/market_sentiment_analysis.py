"""
市场情绪分析模块 - 基于多维度指标的市场情绪监控
"""
import streamlit as st
import pywencai
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
from .cache_manager import cached_function, display_cache_controls

def setup_sentiment_analysis_styles():
    """设置市场情绪分析的CSS样式"""
    st.markdown("""
    <style>
        /* 市场情绪分析专用样式 */
        .sentiment-title {
            color: #2c3e50;
            font-size: 2.3rem;
            font-weight: bold;
            margin-bottom: 1rem;
            text-align: center;
        }
        .sentiment-subtitle {
            color: #3498db;
            font-size: 1.4rem;
            font-weight: 600;
            margin-top: 1.2rem;
            margin-bottom: 0.8rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.3rem;
        }
        .sentiment-card {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 1.2rem;
            box-shadow: 0 3px 6px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        .sentiment-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 12px rgba(0,0,0,0.15);
        }
        .sentiment-hot {
            color: #e74c3c;
            font-weight: bold;
        }
        .sentiment-normal {
            color: #f39c12;
            font-weight: bold;
        }
        .sentiment-cold {
            color: #27ae60;
            font-weight: bold;
        }
        .sentiment-warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 0.8rem;
            margin: 0.5rem 0;
        }
        .sentiment-info {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 5px;
            padding: 0.8rem;
            margin: 0.5rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

def parse_market_data_from_columns(df):
    """从pywencai返回的数据中解析市场情绪数据"""
    results = []
    
    # 获取所有可能的日期
    dates = set()
    import re
    
    for col in df.columns:
        # 从列名中提取日期 - 支持多种格式
        date_patterns = [
            r'(\d{8})',  # 20250819
            r'(\d{4}-\d{2}-\d{2})',  # 2025-08-19
            r'(\d{4}/\d{2}/\d{2})'   # 2025/08/19
        ]
        
        for pattern in date_patterns:
            date_matches = re.findall(pattern, col)
            for date_match in date_matches:
                try:
                    if len(date_match) == 8:  # YYYYMMDD
                        date_obj = datetime.strptime(date_match, '%Y%m%d')
                    elif '-' in date_match:  # YYYY-MM-DD
                        date_obj = datetime.strptime(date_match, '%Y-%m-%d')
                    elif '/' in date_match:  # YYYY/MM/DD
                        date_obj = datetime.strptime(date_match, '%Y/%m/%d')
                    else:
                        continue
                    dates.add(date_obj)
                except:
                    continue
    
    # 如果没有找到日期，尝试从数据行中获取
    if not dates and not df.empty:
        # 检查是否有日期列
        date_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['date', '日期', 'day', '时间'])]
        if date_columns:
            try:
                for _, row in df.iterrows():
                    date_val = row[date_columns[0]]
                    if pd.notna(date_val):
                        if isinstance(date_val, str):
                            # 尝试解析字符串日期
                            for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
                                try:
                                    date_obj = datetime.strptime(date_val, fmt)
                                    dates.add(date_obj)
                                    break
                                except:
                                    continue
                        elif hasattr(date_val, 'date'):
                            dates.add(date_val.date())
            except:
                pass
    
    # 如果还是没有日期，生成最近几天的日期
    if not dates:
        st.warning("未能从数据中提取日期信息，使用默认日期范围")
        end_date = datetime.now()
        for i in range(min(10, len(df))):  # 最多10天
            dates.add(end_date - timedelta(days=i))
    
    # 按日期排序
    dates = sorted(dates, reverse=True)
    
    # 解析每一天的数据
    for i, date_obj in enumerate(dates):
        date_str = date_obj.strftime('%Y%m%d')
        
        ztjs = 0  # 涨停家数
        df_num = 0  # 跌停家数
        lbgd = 1  # 连板高度
        
        # 方法1: 从列名中解析（基于日期）
        for col in df.columns:
            col_lower = col.lower()
            
            # 涨停数据
            if date_str in col and '涨停' in col:
                if '次数' in col or '家数' in col or '数量' in col:
                    try:
                        value = pd.to_numeric(df[col].iloc[0], errors='coerce')
                        if pd.notna(value):
                            ztjs = max(ztjs, int(value))
                    except:
                        pass
            
            # 跌停数据
            if date_str in col and '跌停' in col:
                if '时间' not in col and '明细' not in col and '首次' not in col and '最终' not in col:
                    try:
                        value = pd.to_numeric(df[col].iloc[0], errors='coerce')
                        if pd.notna(value):
                            df_num = max(df_num, int(value))
                    except:
                        pass
            
            # 连板高度
            if date_str in col and ('连续涨停天数' in col or '连板' in col):
                try:
                    value = pd.to_numeric(df[col].iloc[0], errors='coerce')
                    if pd.notna(value):
                        lbgd = max(lbgd, int(value))
                except:
                    pass
        
        # 方法2: 如果没有找到基于日期的数据，尝试从行数据中获取
        if ztjs == 0 and df_num == 0 and lbgd == 1 and i < len(df):
            row = df.iloc[i]
            
            # 查找涨停相关列
            for col in df.columns:
                if '涨停' in col and ('次数' in col or '家数' in col or '数量' in col):
                    try:
                        value = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(value):
                            ztjs = max(ztjs, int(value))
                    except:
                        pass
            
            # 查找跌停相关列
            for col in df.columns:
                if '跌停' in col and '时间' not in col and '明细' not in col:
                    try:
                        value = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(value):
                            df_num = max(df_num, int(value))
                    except:
                        pass
            
            # 查找连板相关列
            for col in df.columns:
                if '连续涨停天数' in col or '连板' in col:
                    try:
                        value = pd.to_numeric(row[col], errors='coerce')
                        if pd.notna(value):
                            lbgd = max(lbgd, int(value))
                    except:
                        pass
        
        results.append({
            'Day': date_obj.strftime('%Y-%m-%d'),
            'ztjs': ztjs,
            'df_num': df_num,
            'lbgd': lbgd
        })
    
    result_df = pd.DataFrame(results)
    
    # 过滤掉全为0的数据行（除了连板高度默认为1）
    result_df = result_df[~((result_df['ztjs'] == 0) & (result_df['df_num'] == 0) & (result_df['lbgd'] == 1))]
    
    return result_df

def get_daily_market_stats(date_str):
    """获取指定日期的市场统计数据"""
    try:
        # 查询当日涨停股票数量
        zt_query = f"非ST，{date_str}涨停"
        zt_df = pywencai.get(query=zt_query)
        
        # 安全检查：确保返回的不是None且不为空
        if zt_df is not None and not zt_df.empty:
            ztjs = len(zt_df)
        else:
            ztjs = 0
        
        # 查询当日跌停股票数量  
        dt_query = f"非ST，{date_str}跌停"
        dt_df = pywencai.get(query=dt_query)
        
        # 安全检查：确保返回的不是None且不为空
        if dt_df is not None and not dt_df.empty:
            df_num = len(dt_df)
        else:
            df_num = 0
        
        # 查询连板高度（获取涨停股票的连续涨停天数）
        lbgd = 1
        if zt_df is not None and not zt_df.empty:
            # 尝试多种可能的连板列名
            lb_columns = [col for col in zt_df.columns if any(keyword in col for keyword in 
                         ['连续涨停天数', '连板天数', '连续涨停', '连板', '涨停天数'])]
            
            if lb_columns:
                try:
                    # 使用第一个找到的连板列
                    lb_col = lb_columns[0]
                    max_lb = pd.to_numeric(zt_df[lb_col], errors='coerce').max()
                    if pd.notna(max_lb) and max_lb > 0:
                        lbgd = int(max_lb)
                except Exception:
                    pass
            
            # 如果没有找到连板列，尝试通过其他方式估算
            if lbgd == 1 and ztjs > 0:
                # 简单估算：如果涨停数量很多，可能有连板
                if ztjs >= 50:
                    lbgd = 3  # 估算有3天连板
                elif ztjs >= 30:
                    lbgd = 2  # 估算有2天连板
        
        return ztjs, df_num, lbgd
        
    except Exception as e:
        # 更详细的错误信息，但不显示给用户（避免刷屏）
        # st.warning(f"获取 {date_str} 数据失败: {str(e)}")
        return 0, 0, 1

def get_market_sentiment_data(days=30):
    """获取市场情绪相关数据"""
    try:
        end_date = datetime.now()
        results = []
        
        st.info("正在获取市场统计数据，这可能需要一些时间...")
        progress_bar = st.progress(0)
        
        # 获取最近几天的数据
        for i in range(days):
            current_date = end_date - timedelta(days=i)
            date_str = current_date.strftime('%Y%m%d')
            
            # 更新进度
            progress = (i + 1) / days
            progress_bar.progress(progress)
            
            # 跳过周末（可选，因为A股周末不交易）
            if current_date.weekday() >= 5:  # 5=周六, 6=周日
                continue
            
            try:
                # 获取当日市场统计
                ztjs, df_num, lbgd = get_daily_market_stats(date_str)
                
                results.append({
                    'Day': current_date.strftime('%Y-%m-%d'),
                    'ztjs': ztjs,
                    'df_num': df_num,
                    'lbgd': lbgd
                })
                
                # 显示进度信息（只显示有数据的日期）
                if (ztjs > 0 or df_num > 0) and i % 5 == 0:  # 每5天显示一次进度
                    st.info(f"已处理 {current_date.strftime('%Y-%m-%d')}: 涨停{ztjs}只, 跌停{df_num}只, 连板{lbgd}天")
                
            except Exception as e:
                # 记录失败但不显示警告（避免刷屏）
                # 添加默认数据以保持连续性
                results.append({
                    'Day': current_date.strftime('%Y-%m-%d'),
                    'ztjs': 0,
                    'df_num': 0,
                    'lbgd': 1
                })
                continue
        
        progress_bar.empty()
        
        if not results:
            st.error("未获取到任何有效数据")
            return None
        
        # 转换为DataFrame并按日期排序
        df = pd.DataFrame(results)
        df = df.sort_values('Day').reset_index(drop=True)
        
        # 统计数据质量
        total_days = len(df)
        valid_df = df[(df['ztjs'] > 0) | (df['df_num'] > 0) | (df['lbgd'] > 1)]
        valid_days = len(valid_df)
        success_rate = (valid_days / total_days * 100) if total_days > 0 else 0
        
        if valid_df.empty:
            st.error("❌ 获取的数据中没有有效的市场统计信息")
            st.info("可能原因：网络问题、接口限制或查询的日期范围包含过多节假日")
            return df  # 返回原始数据，让用户看到问题
        
        # 显示数据获取结果
        if success_rate >= 80:
            st.success(f"✅ 数据获取成功！有效数据 {valid_days}/{total_days} 天 ({success_rate:.1f}%)")
        elif success_rate >= 50:
            st.warning(f"⚠️ 数据部分获取成功：有效数据 {valid_days}/{total_days} 天 ({success_rate:.1f}%)")
        else:
            st.error(f"❌ 数据获取质量较差：有效数据 {valid_days}/{total_days} 天 ({success_rate:.1f}%)")
            st.info("建议：减少分析天数或稍后重试")
        
        # 显示数据概览
        if len(valid_df) > 0:
            latest = valid_df.iloc[-1]
            avg_zt = valid_df['ztjs'].mean()
            avg_dt = valid_df['df_num'].mean()
            max_lb = valid_df['lbgd'].max()
            
            st.info(f"""
            **数据概览:**
            - 最新数据: {latest['Day']} (涨停:{latest['ztjs']}只, 跌停:{latest['df_num']}只, 连板:{latest['lbgd']}天)
            - 平均涨停: {avg_zt:.1f}只/天
            - 平均跌停: {avg_dt:.1f}只/天  
            - 最高连板: {max_lb}天
            """)
        
        return valid_df
        
    except Exception as e:
        st.error(f"获取市场情绪数据失败: {str(e)}")
        st.info("💡 建议勾选'使用演示数据'来体验功能")
        return None

def calculate_sentiment_indicators(df):
    """计算市场情绪指标"""
    try:
        if df is None or df.empty:
            st.error("输入数据为空")
            return None
            
        # 确保数据列存在并处理
        required_columns = ['Day', 'ztjs', 'df_num', 'lbgd']
        
        # 检查必要列是否存在
        for col in required_columns:
            if col not in df.columns:
                st.error(f"缺少必要列: {col}")
                st.info(f"当前数据列: {list(df.columns)}")
                return None
        
        # 数据清洗和转换
        df = df.copy()  # 避免修改原始数据
        df['ztjs'] = pd.to_numeric(df['ztjs'], errors='coerce').fillna(0).astype(int)
        df['df_num'] = pd.to_numeric(df['df_num'], errors='coerce').fillna(0).astype(int)
        df['lbgd'] = pd.to_numeric(df['lbgd'], errors='coerce').fillna(1).astype(int)
        
        # 数据合理性检查
        df['ztjs'] = np.clip(df['ztjs'], 0, 500)  # 涨停数量合理范围
        df['df_num'] = np.clip(df['df_num'], 0, 500)  # 跌停数量合理范围
        df['lbgd'] = np.clip(df['lbgd'], 1, 20)  # 连板高度合理范围
        
        # 计算情绪温度指标 (0-100)
        # 改进的计算公式，更符合市场实际情况
        
        # 1. 涨停占比 (0-60分)
        total_limit = df['ztjs'] + df['df_num']
        df['zt_ratio'] = np.where(total_limit > 0, df['ztjs'] / total_limit, 0.5)
        zt_score = df['zt_ratio'] * 60
        
        # 2. 市场活跃度 (0-25分) - 基于涨停绝对数量
        activity_score = np.minimum(df['ztjs'] / 50 * 25, 25)  # 50只涨停为满分
        
        # 3. 连板强度 (0-15分)
        lb_score = np.minimum(df['lbgd'] / 8 * 15, 15)  # 8天连板为满分
        
        # 4. 风险惩罚 (0到-10分)
        risk_penalty = np.maximum(-10, -df['df_num'] / 30 * 10)  # 30只跌停扣满分
        
        # 综合情绪温度
        df['strong'] = (zt_score + activity_score + lb_score + risk_penalty).round(1)
        
        # 确保情绪温度在0-100范围内
        df['strong'] = np.clip(df['strong'], 0, 100)
        
        # 添加辅助计算列（用于调试和分析）
        df['zt_ratio'] = df['zt_ratio'].round(3)
        
        # 数据质量检查
        valid_count = len(df[(df['ztjs'] > 0) | (df['df_num'] > 0)])
        if valid_count == 0:
            st.warning("⚠️ 所有数据的涨停和跌停数量都为0，可能数据获取有问题")
        elif valid_count < len(df) * 0.5:
            st.warning(f"⚠️ 只有 {valid_count}/{len(df)} 天有有效数据，数据质量可能不佳")
        
        st.success(f"✅ 情绪指标计算完成，有效数据 {valid_count}/{len(df)} 天")
        
        return df
        
    except Exception as e:
        st.error(f"计算情绪指标失败: {str(e)}")
        import traceback
        st.error(f"详细错误: {traceback.format_exc()}")
        return None

def create_mock_data(days=30):
    """创建模拟数据用于演示"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 生成模拟数据
    np.random.seed(42)
    base_zt = 30
    base_dt = 15
    base_lb = 3
    
    data = []
    for i, date in enumerate(dates):
        # 添加一些趋势和随机性
        trend_factor = np.sin(i * 0.2) * 0.3 + 1
        noise = np.random.normal(0, 0.2)
        
        ztjs = max(0, int(base_zt * trend_factor + np.random.normal(0, 8)))
        df_num = max(0, int(base_dt / trend_factor + np.random.normal(0, 5)))
        lbgd = max(1, int(base_lb * trend_factor + np.random.normal(0, 2)))
        
        data.append({
            'Day': date.strftime('%Y-%m-%d'),
            'ztjs': ztjs,
            'df_num': df_num,
            'lbgd': lbgd
        })
    
    df = pd.DataFrame(data)
    return calculate_sentiment_indicators(df)

def analyze_sentiment_level(strong_value):
    """分析情绪水平"""
    if strong_value >= 75:
        return "过热", "sentiment-hot", "🔥"
    elif strong_value >= 60:
        return "偏热", "sentiment-normal", "📈"
    elif strong_value >= 40:
        return "正常", "sentiment-normal", "😐"
    elif strong_value >= 25:
        return "偏冷", "sentiment-normal", "📉"
    else:
        return "过冷", "sentiment-cold", "🧊"

def display_sentiment_summary(df):
    """显示情绪分析摘要"""
    if df is None or df.empty:
        return
        
    st.markdown('<p class="sentiment-subtitle">📊 市场情绪概览</p>', unsafe_allow_html=True)
    
    # 获取最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # 计算变化
    strong_change = latest['strong'] - prev['strong']
    zt_change = latest['ztjs'] - prev['ztjs']
    dt_change = latest['df_num'] - prev['df_num']
    lb_change = latest['lbgd'] - prev['lbgd']
    
    # 分析当前情绪水平
    sentiment_level, sentiment_class, sentiment_icon = analyze_sentiment_level(latest['strong'])
    
    # 创建4列布局
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="sentiment-card">
            <h4>{sentiment_icon} 情绪温度</h4>
            <h2 class="{sentiment_class}">{latest['strong']:.1f}</h2>
            <p>状态: <span class="{sentiment_class}">{sentiment_level}</span></p>
            <p>变化: {strong_change:+.1f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        zt_color = "sentiment-hot" if latest['ztjs'] > 50 else "sentiment-normal"
        st.markdown(f"""
        <div class="sentiment-card">
            <h4>📈 涨停家数</h4>
            <h2 class="{zt_color}">{latest['ztjs']:.0f}</h2>
            <p>活跃度: {'高' if latest['ztjs'] > 50 else '中' if latest['ztjs'] > 20 else '低'}</p>
            <p>变化: {zt_change:+.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        lb_color = "sentiment-hot" if latest['lbgd'] >= 5 else "sentiment-normal"
        st.markdown(f"""
        <div class="sentiment-card">
            <h4>🔗 连板高度</h4>
            <h2 class="{lb_color}">{latest['lbgd']:.0f}</h2>
            <p>龙头: {'强势' if latest['lbgd'] >= 5 else '一般' if latest['lbgd'] >= 3 else '较弱'}</p>
            <p>变化: {lb_change:+.0f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        dt_color = "sentiment-cold" if latest['df_num'] > 30 else "sentiment-normal"
        st.markdown(f"""
        <div class="sentiment-card">
            <h4>📉 亏钱效应</h4>
            <h2 class="{dt_color}">{latest['df_num']:.0f}</h2>
            <p>风险: {'高' if latest['df_num'] > 30 else '中' if latest['df_num'] > 15 else '低'}</p>
            <p>变化: {dt_change:+.0f}</p>
        </div>
        """, unsafe_allow_html=True)

def create_sentiment_charts(df):
    """创建市场情绪分析图表"""
    if df is None or df.empty:
        return None
        
    # 创建2x2的子图布局（4个独立折线图）
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("情绪温度趋势", "涨停家数趋势", "连板高度趋势", "亏钱效应趋势"),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    # 1. 情绪温度折线图（左上）
    fig.add_trace(
        go.Scatter(
            x=df['Day'],
            y=df['strong'],
            name='情绪温度',
            mode='lines+markers',
            line=dict(color='#636EFA', width=2),
            marker=dict(size=6),
            hovertemplate='日期: %{x}<br>情绪温度: %{y:.1f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # 添加警戒线
    fig.add_hline(y=75, line_dash="dot", line_color="red", row=1, col=1,
                  annotation_text="过热警戒线", annotation_position="top right")
    fig.add_hline(y=25, line_dash="dot", line_color="green", row=1, col=1,
                  annotation_text="过冷警戒线", annotation_position="bottom right")
    fig.update_yaxes(title_text="情绪指数(0-100)", range=[0, 100], row=1, col=1)
    
    # 2. 涨停家数折线图（右上）
    fig.add_trace(
        go.Scatter(
            x=df['Day'],
            y=df['ztjs'],
            name='涨停家数',
            mode='lines+markers',
            line=dict(color='#00C853', width=2),
            marker=dict(size=6, symbol='diamond'),
            hovertemplate='日期: %{x}<br>涨停家数: %{y:.0f}<extra></extra>'
        ),
        row=1, col=2
    )
    
    # 添加活跃警戒线
    fig.add_hline(y=50, line_dash="dot", line_color="orange", row=1, col=2,
                  annotation_text="情绪活跃线", annotation_position="top right")
    fig.update_yaxes(title_text="涨停数量", row=1, col=2)
    
    # 3. 连板高度折线图（左下）
    fig.add_trace(
        go.Scatter(
            x=df['Day'],
            y=df['lbgd'],
            name='连板高度',
            mode='lines+markers',
            line=dict(color='#FF6D00', width=2, dash='dot'),
            marker=dict(size=7, symbol='triangle-up'),
            hovertemplate='日期: %{x}<br>连板高度: %{y:.0f}天<extra></extra>'
        ),
        row=2, col=1
    )
    
    # 添加龙头股识别线
    fig.add_hline(y=5, line_dash="dot", line_color="purple", row=2, col=1,
                  annotation_text="龙头股阈值", annotation_position="top right")
    fig.update_yaxes(title_text="连板天数", row=2, col=1)
    
    # 4. 亏钱效应折线图（右下）
    fig.add_trace(
        go.Scatter(
            x=df['Day'],
            y=df['df_num'],
            name='亏钱效应',
            mode='lines+markers',
            line=dict(color='#D50000', width=2),
            marker=dict(size=6, symbol='x'),
            hovertemplate='日期: %{x}<br>跌停数量: %{y:.0f}<extra></extra>'
        ),
        row=2, col=2
    )
    
    # 添加风险警戒线
    fig.add_hline(y=30, line_dash="dot", line_color="brown", row=2, col=2,
                  annotation_text="风险警戒线", annotation_position="top right")
    fig.update_yaxes(title_text="跌停数量", row=2, col=2)
    
    # 统一设置布局
    fig.update_layout(
        height=700,
        showlegend=False,  # 每个图表独立展示，无需图例
        template='plotly_white',
        margin=dict(t=50, b=50),
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=2)
    
    return fig

def generate_sentiment_advice(df):
    """生成市场情绪建议"""
    if df is None or df.empty:
        return
        
    latest = df.iloc[-1]
    sentiment_level, _, _ = analyze_sentiment_level(latest['strong'])
    
    st.markdown('<p class="sentiment-subtitle">💡 操作建议</p>', unsafe_allow_html=True)
    
    # 根据情绪水平给出建议
    if sentiment_level == "过热":
        st.markdown("""
        <div class="sentiment-warning">
            <h4>⚠️ 市场过热警告</h4>
            <p><strong>建议操作：</strong></p>
            <ul>
                <li>谨慎追高，注意风险控制</li>
                <li>可考虑适当减仓或获利了结</li>
                <li>关注市场调整信号</li>
                <li>避免盲目追涨停板</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    elif sentiment_level == "过冷":
        st.markdown("""
        <div class="sentiment-info">
            <h4>❄️ 市场过冷提示</h4>
            <p><strong>建议操作：</strong></p>
            <ul>
                <li>可关注优质标的逢低布局机会</li>
                <li>等待市场情绪回暖信号</li>
                <li>控制仓位，分批建仓</li>
                <li>重点关注基本面良好的个股</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.markdown("""
        <div class="sentiment-info">
            <h4>📊 市场情绪正常</h4>
            <p><strong>建议操作：</strong></p>
            <ul>
                <li>可正常进行投资操作</li>
                <li>关注个股基本面和技术面</li>
                <li>保持合理的仓位配置</li>
                <li>密切关注情绪变化趋势</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # 特殊情况提醒
    if latest['df_num'] > 30:
        st.warning("🚨 当前跌停数量较多，市场风险较高，建议谨慎操作")
    
    if latest['lbgd'] >= 7:
        st.info("🔥 连板高度较高，市场投机情绪浓厚，注意风险")

def display_market_sentiment_analysis():
    """显示市场情绪分析界面"""
    # 设置样式
    setup_sentiment_analysis_styles()
    
    # 主标题
    st.markdown('<p class="sentiment-title">📊 市场情绪分析</p>', unsafe_allow_html=True)
    
    # 功能说明
    with st.expander("📖 功能说明", expanded=False):
        st.markdown("""
        **市场情绪分析工具说明：**
        
        - **情绪温度**: 综合涨停数量、跌停数量和连板高度计算的市场情绪指标(0-100)
        - **涨停家数**: 当日涨停股票数量，反映市场活跃度
        - **连板高度**: 最高连续涨停天数，反映龙头股强度
        - **亏钱效应**: 跌停股票数量，反映市场风险水平
        
        **情绪温度计算公式：**
        ```
        情绪温度 = 涨停占比得分(0-60) + 市场活跃度(0-25) + 连板强度(0-15) + 风险惩罚(-10-0)
        
        - 涨停占比得分 = (涨停数量 / (涨停+跌停)) × 60
        - 市场活跃度 = min(涨停数量 / 50 × 25, 25)
        - 连板强度 = min(连板高度 / 8 × 15, 15)  
        - 风险惩罚 = max(-10, -跌停数量 / 30 × 10)
        ```
        
        **情绪等级划分：**
        - 🔥 过热(≥75): 市场情绪过度乐观，注意风险
        - 📈 偏热(60-75): 市场情绪较好，可适度参与
        - 😐 正常(40-60): 市场情绪平稳，正常操作
        - 📉 偏冷(25-40): 市场情绪低迷，谨慎操作
        - 🧊 过冷(<25): 市场情绪极度悲观，可关注机会
        
        **数据获取方式：**
        - 真实数据：通过问财接口分别查询每日涨停、跌停股票数量
        - 演示数据：使用模拟数据展示功能效果
        - 数据处理：自动过滤周末和无效数据
        """)
    
    # 参数设置
    st.markdown('<p class="sentiment-subtitle">⚙️ 分析设置</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        days = st.slider(
            "分析天数",
            min_value=7,
            max_value=60,
            value=30,
            help="选择要分析的历史天数"
        )
    
    with col2:
        use_mock_data = st.checkbox(
            "使用演示数据",
            value=False,
            help="勾选后使用模拟数据进行演示，不勾选则获取真实市场数据"
        )
    
    with col3:
        analyze_button = st.button("🚀 开始分析", type="primary", width="stretch")
    
    # 数据获取和分析
    if analyze_button:
        if use_mock_data:
            # 使用模拟数据
            with st.spinner("正在生成演示数据..."):
                df = create_mock_data(days)
                st.info("📊 当前使用演示数据，展示功能效果")
        else:
            # 获取真实数据
            st.warning("⏳ 获取真实市场数据需要较长时间，请耐心等待...")
            st.info(f"将获取最近 {days} 天的市场统计数据，包括每日涨停、跌停股票数量和连板高度")
            
            df = get_market_sentiment_data(days)
            if df is not None:
                df = calculate_sentiment_indicators(df)
            
            if df is None or df.empty:
                st.error("❌ 未能获取到有效数据")
                return
            
            # 数据质量检查
            if not use_mock_data:
                valid_days = len(df[(df['ztjs'] > 0) | (df['df_num'] > 0)])
                total_days = len(df)
                
                if valid_days < total_days * 0.7:
                    st.warning(f"⚠️ 数据质量提醒：{total_days}天中只有{valid_days}天有有效数据，可能包含节假日或数据获取问题")
                
                if df['ztjs'].max() == 0 and df['df_num'].max() == 0:
                    st.error("❌ 所有数据都为0，可能是数据获取失败，建议使用演示数据")
                    return
            
            # 显示情绪概览
            display_sentiment_summary(df)
            
            # 显示趋势图表
            st.markdown('<p class="sentiment-subtitle">📈 情绪趋势分析</p>', unsafe_allow_html=True)
            
            fig = create_sentiment_charts(df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # 生成操作建议
            generate_sentiment_advice(df)
            
            # 数据导出
            st.markdown('<p class="sentiment-subtitle">💾 数据导出</p>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV下载
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下载CSV数据",
                    data=csv,
                    file_name=f"市场情绪分析_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                    width="stretch"
                )
            
            with col2:
                # Excel下载
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='市场情绪分析')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📊 下载Excel数据",
                    data=excel_data,
                    file_name=f"市场情绪分析_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    width="stretch"
                )

if __name__ == "__main__":
    display_market_sentiment_analysis()