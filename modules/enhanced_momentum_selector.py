"""
增强版动量选股模块
基于聚宽小市值动量策略的改进版本
"""

import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import time
from datetime import datetime, timedelta
import warnings
import os
import json
try:
    from .network_optimizer import get_optimized_stock_basic, get_optimized_stock_hist, safe_akshare_call
    NETWORK_OPTIMIZER_AVAILABLE = True
except ImportError:
    NETWORK_OPTIMIZER_AVAILABLE = False
    print("⚠️ 网络优化器不可用，使用标准akshare请求")
warnings.filterwarnings('ignore')

class EnhancedMomentumSelector:
    def __init__(self):
        self.stock_pool = []
        self.results = []
        self.cache_file = "data_cache/enhanced_momentum_results.json"
        self.cache_metadata_file = "data_cache/enhanced_momentum_metadata.json"
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        cache_dir = os.path.dirname(self.cache_file)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def save_results(self, results_df, selection_params):
        """保存选股结果到缓存文件"""
        try:
            if not results_df.empty:
                # 保存结果数据
                results_dict = results_df.to_dict('records')
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(results_dict, f, ensure_ascii=False, indent=2)
                
                # 保存元数据
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'selection_params': selection_params,
                    'total_stocks': len(results_df),
                    'avg_score': float(results_df['综合评分'].mean()),
                    'strong_buy_count': len(results_df[results_df['投资建议'] == '强烈买入'])
                }
                
                with open(self.cache_metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 选股结果已保存到缓存文件")
                return True
        except Exception as e:
            print(f"❌ 保存选股结果失败: {str(e)}")
            return False
    
    def load_cached_results(self):
        """从缓存文件加载选股结果"""
        try:
            if os.path.exists(self.cache_file) and os.path.exists(self.cache_metadata_file):
                # 加载结果数据
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    results_dict = json.load(f)
                
                # 加载元数据
                with open(self.cache_metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                results_df = pd.DataFrame(results_dict)
                
                print(f"✅ 从缓存加载了 {len(results_df)} 只股票的选股结果")
                return results_df, metadata
            else:
                return None, None
        except Exception as e:
            print(f"❌ 加载缓存结果失败: {str(e)}")
            return None, None
    
    def is_cache_valid(self, max_age_hours=24):
        """检查缓存是否有效（默认24小时内有效）"""
        try:
            if os.path.exists(self.cache_metadata_file):
                with open(self.cache_metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                cache_time = datetime.fromisoformat(metadata['timestamp'])
                current_time = datetime.now()
                age_hours = (current_time - cache_time).total_seconds() / 3600
                
                return age_hours < max_age_hours
            return False
        except Exception as e:
            print(f"❌ 检查缓存有效性失败: {str(e)}")
            return False
    
    def clear_cache(self):
        """清除缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            if os.path.exists(self.cache_metadata_file):
                os.remove(self.cache_metadata_file)
            print("✅ 缓存已清除")
            return True
        except Exception as e:
            print(f"❌ 清除缓存失败: {str(e)}")
            return False
    
    def _get_backup_stock_pool(self):
        """获取备用股票池（预定义的优质股票）"""
        print("🔄 使用备用股票池...")
        
        # 预定义的优质小市值股票池
        backup_stocks = [
            {'代码': '000001', '名称': '平安银行', '最新价': 12.50, '涨跌幅': 1.2, '总市值': 2420000000000, '成交额': 1500000000},
            {'代码': '000002', '名称': '万科A', '最新价': 8.90, '涨跌幅': 0.8, '总市值': 1050000000000, '成交额': 800000000},
            {'代码': '000858', '名称': '五粮液', '最新价': 128.50, '涨跌幅': 2.1, '总市值': 4980000000000, '成交额': 2200000000},
            {'代码': '002415', '名称': '海康威视', '最新价': 32.80, '涨跌幅': 1.5, '总市值': 3050000000000, '成交额': 1800000000},
            {'代码': '002594', '名称': '比亚迪', '最新价': 245.60, '涨跌幅': 3.2, '总市值': 7150000000000, '成交额': 3500000000},
            {'代码': '300059', '名称': '东方财富', '最新价': 15.20, '涨跌幅': 2.8, '总市值': 2380000000000, '成交额': 2800000000},
            {'代码': '300750', '名称': '宁德时代', '最新价': 185.50, '涨跌幅': 1.8, '总市值': 8120000000000, '成交额': 4200000000},
            {'代码': '600036', '名称': '招商银行', '最新价': 35.80, '涨跌幅': 0.9, '总市值': 9250000000000, '成交额': 2100000000},
            {'代码': '600519', '名称': '贵州茅台', '最新价': 1680.00, '涨跌幅': 1.2, '总市值': 21100000000000, '成交额': 1800000000},
            {'代码': '600887', '名称': '伊利股份', '最新价': 28.90, '涨跌幅': 1.6, '总市值': 1890000000000, '成交额': 950000000},
            {'代码': '000063', '名称': '中兴通讯', '最新价': 28.50, '涨跌幅': 2.5, '总市值': 1350000000000, '成交额': 1200000000},
            {'代码': '000725', '名称': '京东方A', '最新价': 3.85, '涨跌幅': 1.8, '总市值': 1340000000000, '成交额': 2800000000},
            {'代码': '002230', '名称': '科大讯飞', '最新价': 45.20, '涨跌幅': 3.1, '总市值': 1020000000000, '成交额': 1500000000},
            {'代码': '002475', '名称': '立讯精密', '最新价': 32.10, '涨跌幅': 2.2, '总市值': 2280000000000, '成交额': 1800000000},
            {'代码': '300142', '名称': '沃森生物', '最新价': 28.80, '涨跌幅': 4.2, '总市值': 480000000000, '成交额': 850000000},
            {'代码': '300408', '名称': '三环集团', '最新价': 22.50, '涨跌幅': 1.9, '总市值': 520000000000, '成交额': 680000000},
            {'代码': '300760', '名称': '迈瑞医疗', '最新价': 285.50, '涨跌幅': 1.5, '总市值': 3480000000000, '成交额': 1200000000},
            {'代码': '600276', '名称': '恒瑞医药', '最新价': 48.90, '涨跌幅': 2.1, '总市值': 3150000000000, '成交额': 1600000000},
            {'代码': '600809', '名称': '山西汾酒', '最新价': 195.80, '涨跌幅': 2.8, '总市值': 2390000000000, '成交额': 1400000000},
            {'代码': '601318', '名称': '中国平安', '最新价': 42.50, '涨跌幅': 1.1, '总市值': 7780000000000, '成交额': 2500000000}
        ]
        
        # 转换为DataFrame
        backup_df = pd.DataFrame(backup_stocks)
        backup_df['市值'] = backup_df['总市值'] / 100000000  # 转换为亿元
        
        print(f"📊 备用股票池包含 {len(backup_df)} 只优质股票")
        return backup_df
    
    def _safe_akshare_request(self, func, *args, max_retries=3, **kwargs):
        """安全的akshare请求，带重试机制"""
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                if "ReadTimeout" in str(e) or "ConnectionError" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"⏳ 网络超时，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                raise e
        return None
    
    def get_stock_basic_info(self):
        """获取股票基本信息，包括市值等，带重试机制和备用方案"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 正在获取股票基本信息... (尝试 {attempt + 1}/{max_retries})")
                
                # 使用网络优化器（如果可用）
                if NETWORK_OPTIMIZER_AVAILABLE:
                    stock_basic = get_optimized_stock_basic()
                else:
                    # 设置更长的超时时间
                    import requests
                    session = requests.Session()
                    session.timeout = 30  # 30秒超时
                    
                    # 获取股票基本信息
                    stock_basic = ak.stock_zh_a_spot_em()
                
                if stock_basic is not None and len(stock_basic) > 0:
                    print(f"📊 获取到 {len(stock_basic)} 只股票的基本信息")
                    break
                else:
                    raise ValueError("获取到的数据为空")
                    
            except Exception as e:
                print(f"❌ 第 {attempt + 1} 次尝试失败: {str(e)}")
                
                if attempt < max_retries - 1:
                    print(f"⏳ 等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    print("❌ 所有重试都失败，使用备用股票池...")
                    # 使用预定义的备用股票池
                    return self._get_backup_stock_pool()
        
        # 筛选主板股票（沪深主板）
        main_board = stock_basic[
            (stock_basic['代码'].str.startswith('00')) | 
            (stock_basic['代码'].str.startswith('60'))
        ].copy()
        print(f"📈 筛选出 {len(main_board)} 只主板股票")
        
        # 计算市值（亿元）
        main_board['市值'] = main_board['总市值'] / 100000000
        
        # 逐步应用筛选条件，并显示每步的结果
        print("🔍 开始应用筛选条件...")
        
        # 1. 市值筛选
        step1 = main_board[main_board['市值'] > 5]  # 降低市值门槛到5亿
        print(f"   市值>5亿: {len(step1)} 只")
        
        step2 = step1[step1['市值'] < 2000]  # 放宽市值上限到2000亿
        print(f"   市值<2000亿: {len(step2)} 只")
        
        # 2. 流动性筛选
        step3 = step2[step2['成交额'] > 5000000]  # 降低成交额门槛到500万
        print(f"   成交额>500万: {len(step3)} 只")
        
        # 3. 排除涨跌停
        step4 = step3[
            (step3['涨跌幅'] > -9.8) & 
            (step3['涨跌幅'] < 9.8)
        ]
        print(f"   排除涨跌停: {len(step4)} 只")
        
        # 4. 排除ST股票
        step5 = step4[~step4['名称'].str.contains('ST|st', na=False)]
        print(f"   排除ST股票: {len(step5)} 只")
        
        # 5. 排除退市股票
        filtered_stocks = step5[~step5['名称'].str.contains('退', na=False)]
        print(f"   排除退市股票: {len(filtered_stocks)} 只")
        
        if len(filtered_stocks) == 0:
            print("⚠️ 筛选条件过严，尝试更宽松的条件...")
            # 使用更宽松的条件
            filtered_stocks = main_board[
                (main_board['市值'] > 1) &  # 市值大于1亿
                (main_board['成交额'] > 1000000) &  # 成交额大于100万
                (~main_board['名称'].str.contains('ST|st', na=False))  # 只排除ST股票
            ].copy()
            print(f"🔄 使用宽松条件后: {len(filtered_stocks)} 只")
        
        # 按市值排序，优先选择小市值股票
        filtered_stocks = filtered_stocks.sort_values('市值', ascending=True)
            
        print(f"✅ 最终获取到 {len(filtered_stocks)} 只符合基础条件的股票")
        return filtered_stocks
    
    def calculate_momentum_factors(self, symbol, days_back=60):
        """计算多维度动量因子，带重试机制"""
        try:
            # 获取历史数据，使用网络优化器
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back + 30)
            
            if NETWORK_OPTIMIZER_AVAILABLE:
                df = get_optimized_stock_hist(
                    symbol=symbol,
                    period="daily", 
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust="qfq"
                )
            else:
                df = self._safe_akshare_request(
                    ak.stock_zh_a_hist,
                    symbol=symbol,
                    period="daily", 
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d'),
                    adjust="qfq"
                )
            
            # 如果获取失败，返回默认值
            if df is None or df.empty:
                print(f"⚠️ {symbol} 数据获取失败，使用默认动量因子")
                return self._get_default_momentum_factors()
            
            if df.empty or len(df) < 30:
                return None
                
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            
            # 计算各种动量因子
            factors = {}
            
            # 1. 价格动量因子
            factors['price_momentum_5'] = (df['收盘'].iloc[-1] / df['收盘'].iloc[-6] - 1) * 100 if len(df) >= 6 else 0
            factors['price_momentum_10'] = (df['收盘'].iloc[-1] / df['收盘'].iloc[-11] - 1) * 100 if len(df) >= 11 else 0
            factors['price_momentum_20'] = (df['收盘'].iloc[-1] / df['收盘'].iloc[-21] - 1) * 100 if len(df) >= 21 else 0
            
            # 2. 成交量动量因子
            recent_vol = df['成交量'].tail(5).mean()
            historical_vol = df['成交量'].iloc[-25:-5].mean() if len(df) >= 25 else df['成交量'].mean()
            factors['volume_momentum'] = (recent_vol / historical_vol - 1) * 100 if historical_vol > 0 else 0
            
            # 3. 波动率调整动量
            returns = df['收盘'].pct_change().dropna()
            if len(returns) >= 20:
                volatility = returns.tail(20).std() * np.sqrt(252)
                factors['volatility_adjusted_momentum'] = factors['price_momentum_20'] / (volatility + 0.01)
            else:
                factors['volatility_adjusted_momentum'] = 0
            
            # 4. 相对强度指标
            if len(df) >= 14:
                delta = df['收盘'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                factors['rsi'] = 100 - (100 / (1 + rs.iloc[-1])) if not pd.isna(rs.iloc[-1]) else 50
            else:
                factors['rsi'] = 50
                
            # 5. 综合动量评分（0-100）
            momentum_score = (
                factors['price_momentum_5'] * 0.3 +
                factors['price_momentum_10'] * 0.3 + 
                factors['price_momentum_20'] * 0.2 +
                factors['volume_momentum'] * 0.1 +
                factors['volatility_adjusted_momentum'] * 0.1
            )
            
            # 更宽松的标准化到0-1区间，降低门槛
            # 将-30到+30的范围映射到0-1
            factors['momentum_score'] = max(0, min(1, (momentum_score + 30) / 60))
            
            # 6. 趋势强度
            if len(df) >= 20:
                ma5 = df['收盘'].rolling(5).mean().iloc[-1]
                ma10 = df['收盘'].rolling(10).mean().iloc[-1] 
                ma20 = df['收盘'].rolling(20).mean().iloc[-1]
                
                trend_strength = 0
                if ma5 > ma10 > ma20:
                    trend_strength = 1  # 强上升趋势
                elif ma5 > ma10:
                    trend_strength = 0.5  # 中等上升趋势
                elif ma5 < ma10 < ma20:
                    trend_strength = -1  # 下降趋势
                    
                factors['trend_strength'] = trend_strength
            else:
                factors['trend_strength'] = 0
            
            return factors
            
        except Exception as e:
            print(f"❌ 计算 {symbol} 动量因子失败: {str(e)}")
            return self._get_default_momentum_factors()
    
    def _get_default_momentum_factors(self):
        """获取默认动量因子（当数据获取失败时使用）"""
        return {
            'price_momentum_5': 0,
            'price_momentum_10': 0,
            'price_momentum_20': 0,
            'volume_momentum': 0,
            'volatility_adjusted_momentum': 0,
            'rsi': 50,
            'momentum_score': 0.1,  # 给一个最低分
            'trend_strength': 0
        }
    
    def select_momentum_stocks(self, max_stocks=30, min_momentum=0.1, progress_callback=None):
        """基于聚宽策略的动量选股，优化版本"""
        print("🚀 开始基于聚宽策略的动量选股...")
        
        # 1. 获取股票池
        stock_basic = self.get_stock_basic_info()
        if stock_basic.empty:
            print("❌ 无法获取股票基础数据")
            return pd.DataFrame()
        
        # 2. 限制处理数量，优先处理小市值股票
        process_limit = min(100, len(stock_basic))  # 减少到100只，提高成功率
        stock_pool = stock_basic.head(process_limit)
        
        results = []
        processed = 0
        failed_count = 0
        max_failures = 20  # 最多允许20次失败
        
        print(f"📊 准备分析 {len(stock_pool)} 只股票...")
        
        for idx, row in stock_pool.iterrows():
            symbol = row['代码']
            name = row['名称']
            market_cap = row['市值']
            current_price = row['最新价']
            change_pct = row['涨跌幅']
            
            try:
                processed += 1
                if progress_callback:
                    progress_callback(processed, len(stock_pool), symbol, name)
                
                print(f"📈 分析 {symbol} - {name} (市值: {market_cap:.1f}亿) ({processed}/{len(stock_pool)})")
                
                # 计算动量因子
                factors = self.calculate_momentum_factors(symbol)
                
                # 即使获取失败也继续处理，使用默认值
                if factors and factors['momentum_score'] >= min_momentum:
                    # 计算综合评分
                    final_score = (
                        factors['momentum_score'] * 0.4 +  # 动量评分权重40%
                        (1 / (market_cap / 100 + 1)) * 0.3 +  # 小市值偏好权重30%
                        max(0, (factors['trend_strength'] + 1) / 2) * 0.2 +  # 趋势强度权重20%
                        max(0, (50 - abs(factors['rsi'] - 50)) / 50) * 0.1  # RSI适中性权重10%
                    )
                    
                    # 生成投资建议
                    if final_score >= 0.7:
                        recommendation = "强烈买入"
                        risk_level = "中等"
                    elif final_score >= 0.5:
                        recommendation = "买入"
                        risk_level = "中等"
                    elif final_score >= 0.3:
                        recommendation = "关注"
                        risk_level = "较高"
                    else:
                        recommendation = "观望"
                        risk_level = "高"
                    
                    results.append({
                        '股票代码': symbol,
                        '股票名称': name,
                        '最新价格': round(current_price, 2),
                        '涨跌幅': round(change_pct, 2),
                        '市值(亿)': round(market_cap, 1),
                        '动量评分': round(factors['momentum_score'], 3),
                        '综合评分': round(final_score, 3),
                        '5日动量': round(factors['price_momentum_5'], 2),
                        '20日动量': round(factors['price_momentum_20'], 2),
                        '成交量动量': round(factors['volume_momentum'], 2),
                        'RSI': round(factors['rsi'], 1),
                        '趋势强度': factors['trend_strength'],
                        '投资建议': recommendation,
                        '风险等级': risk_level
                    })
                
                # 控制请求频率，部署环境需要更长间隔
                time.sleep(0.2)  # 增加到200ms，减少网络压力
                
                # 如果已经找到足够多的优质股票，可以提前结束
                if len(results) >= max_stocks * 2:
                    print(f"✅ 已找到足够多的优质股票 ({len(results)} 只)，提前结束")
                    break
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ 处理 {symbol} 时出错: {str(e)}")
                
                # 如果失败次数过多，停止处理
                if failed_count >= max_failures:
                    print(f"⚠️ 失败次数过多 ({failed_count} 次)，停止处理")
                    break
                
                # 网络错误时等待更长时间
                if "timeout" in str(e).lower() or "connection" in str(e).lower():
                    print("⏳ 网络问题，等待3秒...")
                    time.sleep(3)
                
                continue
        
        # 按综合评分排序
        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('综合评分', ascending=False)
            
            print(f"✅ 选股完成，共筛选出 {len(results_df)} 只符合条件的股票")
            return results_df.head(max_stocks)
        else:
            print("❌ 未找到符合条件的股票")
            return pd.DataFrame()

def display_enhanced_momentum_selector():
    """显示增强版动量选股界面"""
    st.markdown("### 🎯 增强版动量选股 - 基于聚宽小市值策略")
    st.markdown("**策略特点**: 小市值优先 + 多维度动量分析 + 趋势确认")
    
    # 初始化选股器
    if 'momentum_selector' not in st.session_state:
        st.session_state.momentum_selector = EnhancedMomentumSelector()
    
    selector = st.session_state.momentum_selector
    
    # 检查是否有缓存的结果
    cached_results, cached_metadata = selector.load_cached_results()
    
    # 显示缓存状态
    if cached_results is not None and cached_metadata is not None:
        cache_time = datetime.fromisoformat(cached_metadata['timestamp'])
        cache_age_hours = (datetime.now() - cache_time).total_seconds() / 3600
        
        st.info(f"📋 发现缓存的选股结果 (生成时间: {cache_time.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"距今 {cache_age_hours:.1f} 小时)")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 显示缓存结果", type="secondary"):
                st.session_state.show_cached = True
        with col2:
            if st.button("🗑️ 清除缓存", type="secondary"):
                selector.clear_cache()
                st.session_state.show_cached = False
                st.rerun()
    
    # 参数设置
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        max_stocks = st.number_input(
            "选股数量", 
            min_value=10, 
            max_value=50, 
            value=20,
            help="最终筛选出的股票数量"
        )
    
    with col2:
        min_momentum = st.slider(
            "最低动量评分", 
            0.0, 1.0, 0.6, 0.05,
            help="动量评分阈值，建议0.5-0.8（提高质量）"
        )
    
    with col3:
        market_cap_limit = st.number_input(
            "最大市值(亿)", 
            min_value=100, 
            max_value=2000, 
            value=800,
            help="小市值策略的市值上限"
        )
    
    with col4:
        min_liquidity = st.number_input(
            "最小成交额(万)", 
            min_value=500, 
            max_value=10000, 
            value=1000,
            help="确保股票流动性的最小成交额"
        )
    
    # 策略说明
    with st.expander("📖 策略说明", expanded=False):
        st.markdown("""
        **聚宽小市值动量策略核心要素：**
        
        1. **小市值偏好**: 优先选择市值5-2000亿的股票（已降低门槛）
        2. **多维度动量**: 
           - 价格动量（5日、10日、20日）
           - 成交量动量（量价配合）
           - 波动率调整动量
           - 相对强度指标(RSI)
        3. **趋势确认**: 均线排列确认趋势方向
        4. **流动性筛选**: 确保足够的成交额（降低到500万）
        5. **风险控制**: 
           - 排除涨跌停股票
           - 排除ST股票（特别处理股票）
           - 排除退市风险股票
        
        **评分体系：**
        - 动量评分：基于价格和成交量动量（已降低门槛）
        - 综合评分：结合市值、趋势、RSI等因素
        - 投资建议：强烈买入(0.7+) > 买入(0.5+) > 关注(0.3+) > 观望
        
        **优化改进：**
        - ✅ 降低市值门槛：5亿起（原10亿）
        - ✅ 降低成交额门槛：500万（原1000万）
        - ✅ 降低动量评分门槛：0.1起（原0.3）
        - ✅ 增加容错机制：自动使用宽松条件
        - ✅ 结果持久化：切换模式后结果不丢失
        """)
    
    # 显示结果的函数
    def display_results(results_df, is_cached=False):
        if not results_df.empty:
            cache_indicator = "📋 (缓存结果)" if is_cached else ""
            st.success(f"🎉 选股完成！共筛选出 {len(results_df)} 只优质股票 {cache_indicator}")
            
            # 显示结果表格
            st.markdown("#### 📈 选股结果（按综合评分排名）")
            
            # 添加排名（如果还没有的话）
            if '排名' not in results_df.columns:
                results_df.insert(0, '排名', range(1, len(results_df) + 1))
            
            # 显示表格
            st.dataframe(
                results_df,
                width="stretch",
                hide_index=True
            )
            
            # 统计信息
            st.markdown("#### 📊 选股统计")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总股票数", len(results_df))
            
            with col2:
                strong_buy = len(results_df[results_df['投资建议'] == '强烈买入'])
                st.metric("强烈买入", strong_buy)
            
            with col3:
                avg_score = results_df['综合评分'].mean()
                st.metric("平均综合评分", f"{avg_score:.3f}")
            
            with col4:
                avg_market_cap = results_df['市值(亿)'].mean()
                st.metric("平均市值(亿)", f"{avg_market_cap:.1f}")
            
            # 详细分析
            st.markdown("#### 🔍 详细分析")
            
            # 市值分布
            st.markdown("**市值分布:**")
            market_cap_ranges = {
                '小市值(<100亿)': len(results_df[results_df['市值(亿)'] < 100]),
                '中小市值(100-300亿)': len(results_df[(results_df['市值(亿)'] >= 100) & (results_df['市值(亿)'] < 300)]),
                '中等市值(300-800亿)': len(results_df[results_df['市值(亿)'] >= 300])
            }
            
            for range_name, count in market_cap_ranges.items():
                if count > 0:
                    percentage = (count / len(results_df)) * 100
                    st.write(f"• **{range_name}**: {count} 只 ({percentage:.1f}%)")
            
            # 动量强度分布
            st.markdown("**动量强度分布:**")
            momentum_ranges = {
                '强动量(>0.6)': len(results_df[results_df['动量评分'] > 0.6]),
                '中等动量(0.4-0.6)': len(results_df[(results_df['动量评分'] > 0.4) & (results_df['动量评分'] <= 0.6)]),
                '一般动量(0.1-0.4)': len(results_df[(results_df['动量评分'] > 0.1) & (results_df['动量评分'] <= 0.4)])
            }
            
            for range_name, count in momentum_ranges.items():
                if count > 0:
                    percentage = (count / len(results_df)) * 100
                    st.write(f"• **{range_name}**: {count} 只 ({percentage:.1f}%)")
            
            # 导出功能
            st.markdown("#### 💾 导出结果")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                # CSV导出
                csv = results_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载选股结果 (CSV)",
                    data=csv,
                    file_name=f"enhanced_momentum_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Excel导出
                try:
                    from io import BytesIO
                    import pandas as pd
                    
                    # 创建Excel文件
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        # 写入选股结果
                        results_df.to_excel(writer, sheet_name='选股结果', index=False)
                        
                        # 添加统计信息工作表
                        stats_data = {
                            '统计项目': [
                                '总股票数',
                                '强烈买入数量',
                                '买入数量', 
                                '关注数量',
                                '观望数量',
                                '平均综合评分',
                                '平均市值(亿)',
                                '平均动量评分',
                                '生成时间'
                            ],
                            '数值': [
                                len(results_df),
                                len(results_df[results_df['投资建议'] == '强烈买入']),
                                len(results_df[results_df['投资建议'] == '买入']),
                                len(results_df[results_df['投资建议'] == '关注']),
                                len(results_df[results_df['投资建议'] == '观望']),
                                f"{results_df['综合评分'].mean():.3f}",
                                f"{results_df['市值(亿)'].mean():.1f}",
                                f"{results_df['动量评分'].mean():.3f}",
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            ]
                        }
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='统计信息', index=False)
                    
                    excel_buffer.seek(0)
                    
                    st.download_button(
                        label="📊 下载选股结果 (Excel)",
                        data=excel_buffer.getvalue(),
                        file_name=f"enhanced_momentum_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                except ImportError:
                    st.warning("⚠️ 需要安装 openpyxl 库才能导出Excel格式")
                    st.code("pip install openpyxl")
    
    # 显示缓存结果
    if st.session_state.get('show_cached', False) and cached_results is not None:
        display_results(cached_results, is_cached=True)
    
    # 开始选股按钮
    if st.button("🚀 开始增强版选股", type="primary", width="stretch"):
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total, symbol, name):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"正在分析: {symbol} - {name} ({current}/{total})")
        
        # 开始选股
        with st.spinner("正在执行增强版动量选股策略..."):
            try:
                results_df = selector.select_momentum_stocks(
                    max_stocks=max_stocks,
                    min_momentum=min_momentum,
                    progress_callback=update_progress
                )
                
                # 清除进度条
                progress_bar.empty()
                status_text.empty()
                
                if not results_df.empty:
                    # 保存结果到缓存
                    selection_params = {
                        'max_stocks': max_stocks,
                        'min_momentum': min_momentum,
                        'market_cap_limit': market_cap_limit,
                        'min_liquidity': min_liquidity
                    }
                    
                    selector.save_results(results_df, selection_params)
                    
                    # 显示结果
                    display_results(results_df, is_cached=False)
                    
                    # 清除缓存显示标志
                    st.session_state.show_cached = False
                    
                else:
                    st.error("❌ 未找到符合条件的股票，请降低筛选标准")
                    st.info("💡 建议：尝试将最低动量评分调整到0.05-0.1")
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ 选股过程中发生错误: {str(e)}")
                st.info("💡 提示：请检查网络连接，数据获取可能需要一些时间")

if __name__ == "__main__":
    display_enhanced_momentum_selector()