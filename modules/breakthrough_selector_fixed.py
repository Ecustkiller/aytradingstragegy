"""
突破选股模块 - 正确的前高点逻辑
选股条件:
- 股价在55日均线上方
- 55日均线拐头向上  
- 突破前高点（左三右三K线确认的前高点）
- 沪深主板股票
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class BreakthroughSelector:
    def __init__(self):
        self.today = datetime.now().strftime('%Y%m%d')
        
    def get_stock_data(self, code, days=60):
        """获取股票历史数据"""
        try:
            # 计算开始日期
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            # 获取股票历史数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                  start_date=start_date, end_date=end_date, adjust="")
            
            if df.empty:
                return None
            
            # 标准列名映射
            column_mapping = {}
            columns = df.columns.tolist()
            
            # 根据akshare的实际列名进行映射
            if '日期' in columns:
                column_mapping['日期'] = 'date'
            if '开盘' in columns:
                column_mapping['开盘'] = 'open'
            if '收盘' in columns:
                column_mapping['收盘'] = 'close'
            if '最高' in columns:
                column_mapping['最高'] = 'high'
            if '最低' in columns:
                column_mapping['最低'] = 'low'
            if '成交量' in columns:
                column_mapping['成交量'] = 'volume'
            if '涨跌幅' in columns:
                column_mapping['涨跌幅'] = 'change_pct'
            
            # 重命名列
            df = df.rename(columns=column_mapping)
            
            # 确保必要的列存在
            required_columns = ['date', 'open', 'close', 'high', 'low', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"缺少列: {missing_columns}")
                return None
            
            # 选择需要的列
            df = df[required_columns + (['change_pct'] if 'change_pct' in df.columns else [])].copy()
            
            # 转换数据类型
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 如果没有涨跌幅列，计算它
            if 'change_pct' not in df.columns:
                df['change_pct'] = df['close'].pct_change() * 100
            else:
                df['change_pct'] = pd.to_numeric(df['change_pct'], errors='coerce')
            
            df['change_pct'] = df['change_pct'].fillna(0)
            
            # 去除无效数据
            df = df.dropna(subset=['open', 'close', 'high', 'low'])
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            return df.tail(days) if len(df) > days else df
                
        except Exception as e:
            print(f"获取股票 {code} 数据失败: {e}")
            return None

    def find_previous_high(self, df, lookback_days=60):
        """
        寻找前高点 - 左三右三K线确认的前高点
        :param df: 股票数据DataFrame
        :param lookback_days: 回看天数
        :return: 前高点信息字典或None
        """
        if len(df) < 10:  # 至少需要10天数据
            return None
        
        # 只在最近lookback_days天内寻找前高点，但排除最近3天
        recent_df = df.tail(lookback_days) if len(df) > lookback_days else df
        search_end = len(recent_df) - 3  # 排除最近3天
        
        # 从最近的开始往前找，找到第一个符合条件的前高点
        for i in range(search_end - 1, 2, -1):  # 从后往前找，确保左右都有3根K线
            current_high = recent_df.iloc[i]['high']
            current_date = recent_df.iloc[i]['date']
            
            # 检查左边3根K线
            left_highs = recent_df.iloc[i-3:i]['high'].values
            left_condition = all(current_high > h for h in left_highs)
            
            # 检查右边3根K线
            right_highs = recent_df.iloc[i+1:i+4]['high'].values
            right_condition = all(current_high > h for h in right_highs)
            
            # 如果满足左三右三条件，这就是一个前高点
            if left_condition and right_condition:
                # 确认日期是右边第3根K线的日期
                confirm_date = recent_df.iloc[i+3]['date']
                
                return {
                    'price': current_high,
                    'date': current_date,
                    'confirm_date': confirm_date,
                    'index': i
                }
        
        return None

    def select_breakthrough_stocks(self, min_price=5, max_price=100):
        """
        选择突破股票 - 正确的前高点逻辑
        选股条件:
        - 股价在55日均线上方
        - 55日均线拐头向上  
        - 突破前高点（左三右三K线确认的前高点）
        - 沪深主板股票
        """
        try:
            print("🔍 开始获取沪深主板股票列表...")
            
            # 获取A股股票列表
            stock_list = ak.stock_zh_a_spot_em()
            if stock_list.empty:
                return []
            
            # 筛选沪深主板股票（排除创业板、科创板、北交所）
            main_board_stocks = stock_list[
                (stock_list['代码'].str.startswith('000')) |  # 深圳主板
                (stock_list['代码'].str.startswith('001')) |  # 深圳主板
                (stock_list['代码'].str.startswith('002')) |  # 深圳主板（部分）
                (stock_list['代码'].str.startswith('600')) |  # 上海主板
                (stock_list['代码'].str.startswith('601')) |  # 上海主板
                (stock_list['代码'].str.startswith('603')) |  # 上海主板
                (stock_list['代码'].str.startswith('605'))    # 上海主板
            ].copy()
            
            # 排除创业板、科创板
            main_board_stocks = main_board_stocks[
                ~main_board_stocks['代码'].str.startswith('300') &  # 排除创业板
                ~main_board_stocks['代码'].str.startswith('688') &  # 排除科创板
                ~main_board_stocks['代码'].str.startswith('8')      # 排除北交所
            ]
            
            print(f"📊 筛选出 {len(main_board_stocks)} 只沪深主板股票")
            
            # 价格筛选
            filtered_stocks = main_board_stocks[
                (main_board_stocks['最新价'] >= min_price) & 
                (main_board_stocks['最新价'] <= max_price)
            ].copy()
            
            print(f"📈 价格筛选后剩余 {len(filtered_stocks)} 只股票")
            
            breakthrough_stocks = []
            
            # 分析前100只股票
            for i, (_, stock) in enumerate(filtered_stocks.head(100).iterrows()):
                try:
                    code = stock['代码']
                    name = stock['名称']
                    current_price = stock['最新价']
                    
                    print(f"🔍 分析 {code} {name} ({i+1}/100)")
                    
                    # 获取足够的历史数据（至少80天用于计算55日均线和寻找前高点）
                    df = self.get_stock_data(code, days=80)
                    if df is None or len(df) < 60:
                        continue
                    
                    # 计算55日均线
                    df['ma55'] = df['close'].rolling(55).mean()
                    
                    # 确保有足够数据
                    if df['ma55'].isna().sum() > 0:
                        df = df.dropna(subset=['ma55'])
                    
                    if len(df) < 10:  # 至少需要10天数据
                        continue
                    
                    # 获取最新数据
                    latest = df.iloc[-1]
                    prev_5 = df.iloc[-6:-1] if len(df) >= 6 else df.iloc[:-1]
                    
                    # 条件1: 股价在55日均线上方
                    price_above_ma55 = latest['close'] > latest['ma55']
                    
                    # 条件2: 55日均线拐头向上（最近5天均线呈上升趋势）
                    if len(prev_5) >= 3:
                        ma55_trend_up = (latest['ma55'] > prev_5.iloc[-1]['ma55'] and 
                                        prev_5.iloc[-1]['ma55'] > prev_5.iloc[-3]['ma55'])
                    else:
                        ma55_trend_up = False
                    
                    # 条件3: 突破前高点（左三右三K线确认的前高点）
                    previous_high_info = self.find_previous_high(df)
                    if previous_high_info is None:
                        continue
                    
                    prev_high = previous_high_info['price']
                    prev_high_date = previous_high_info['date']
                    prev_high_confirm_date = previous_high_info['confirm_date']
                    
                    # 检查是否是第一天突破
                    today_break = latest['high'] > prev_high  # 今天突破前高
                    yesterday = df.iloc[-2] if len(df) >= 2 else None
                    yesterday_not_break = yesterday['high'] <= prev_high if yesterday is not None else False
                    
                    # 必须是今天第一天突破（昨天还没突破）
                    breakthrough_high = today_break and yesterday_not_break
                    
                    # 综合判断
                    if price_above_ma55 and ma55_trend_up and breakthrough_high:
                        breakthrough_amount = latest['high'] - prev_high
                        breakthrough_pct = (breakthrough_amount / prev_high) * 100
                        
                        breakthrough_stocks.append({
                            'code': code,
                            'name': name,
                            'current_price': current_price,
                            'current_high': latest['high'],
                            'ma55': latest['ma55'],
                            'previous_high': prev_high,
                            'previous_high_date': prev_high_date.strftime('%Y-%m-%d'),
                            'previous_high_confirm_date': prev_high_confirm_date.strftime('%Y-%m-%d'),
                            'breakthrough_amount': breakthrough_amount,
                            'breakthrough_pct': breakthrough_pct,
                            'volume': latest['volume'],
                            'change_pct': latest['change_pct']
                        })
                        print(f"✅ 发现突破股票: {code} {name} - 价格:{current_price:.2f} 突破幅度:{breakthrough_pct:.2f}%")
                    
                except Exception as e:
                    print(f"❌ 分析股票 {code} 失败: {e}")
                    continue
            
            # 按突破幅度排序
            breakthrough_stocks.sort(key=lambda x: x['breakthrough_pct'], reverse=True)
            
            print(f"🎯 共发现 {len(breakthrough_stocks)} 只符合条件的突破股票")
            return breakthrough_stocks
            
        except Exception as e:
            print(f"❌ 突破选股失败: {e}")
            return []

    def save_results(self, results, filename):
        """保存选股结果到CSV文件"""
        if not results:
            print("无结果需要保存")
            return
        
        try:
            df = pd.DataFrame(results)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✅ 结果已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

# 测试功能
if __name__ == "__main__":
    selector = BreakthroughSelector()
    
    print("测试突破选股功能:")
    stocks = selector.select_breakthrough_stocks()
    if stocks:
        print("发现的突破股票:")
        for stock in stocks[:10]:  # 显示前10只
            print(f"{stock['code']} {stock['name']}: {stock['current_price']:.2f} "
                  f"突破幅度:{stock['breakthrough_pct']:.2f}% "
                  f"前高:{stock['previous_high']:.2f} ({stock['previous_high_date']})")
        
        # 保存结果
        filename = f"breakthrough_test_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        selector.save_results(stocks, filename)
    else:
        print("未发现符合条件的突破股票")