"""
工具模块 - 包含辅助函数和工具
"""
import datetime
import streamlit as st
import pytz

# 中国时区
CHINA_TZ = pytz.timezone('Asia/Shanghai')

def get_china_now():
    """获取中国当前时间"""
    return datetime.datetime.now(CHINA_TZ)

def to_china_time(dt):
    """将datetime对象转换为中国时区"""
    if dt.tzinfo is None:
        # 如果是naive datetime，假设为UTC并转换
        dt = pytz.utc.localize(dt)
    return dt.astimezone(CHINA_TZ)

def format_stock_code(stock_code):
    """
    智能格式化股票代码，支持更多类型的股票代码
    
    参数:
        stock_code: 股票代码字符串
    
    返回:
        格式化后的股票代码 (带sh/sz前缀)
    """
    # 移除可能的空格和特殊字符
    stock_code = str(stock_code).strip().upper()
    
    # 如果已经包含交易所前缀，直接返回小写格式
    if stock_code.startswith(('SH', 'SZ')):
        return stock_code.lower()
    
    # 移除可能的点号分隔符 (如 600519.SH)
    if '.' in stock_code:
        code_part = stock_code.split('.')[0]
        if 'SH' in stock_code or 'XSHG' in stock_code:
            return f'sh{code_part}'
        elif 'SZ' in stock_code or 'XSHE' in stock_code:
            return f'sz{code_part}'
    else:
        code_part = stock_code
    
    # 根据股票代码规则智能判断交易所
    if code_part.startswith('6'):
        # 上海A股: 600xxx, 601xxx, 603xxx, 605xxx等
        return f'sh{code_part}'
    elif code_part.startswith('0'):
        # 深圳A股: 000xxx, 001xxx, 002xxx等
        return f'sz{code_part}'
    elif code_part.startswith('3'):
        # 创业板: 300xxx, 301xxx等
        return f'sz{code_part}'
    elif code_part.startswith('68'):
        # 科创板: 688xxx
        return f'sh{code_part}'
    elif code_part.startswith('5'):
        # 上海基金/ETF: 50xxxx, 51xxxx, 52xxxx等
        return f'sh{code_part}'
    elif code_part.startswith('1'):
        # 深圳基金/ETF: 15xxxx, 16xxxx等
        return f'sz{code_part}'
    elif code_part.startswith('4'):
        # 深圳基金: 4xxxxx
        return f'sz{code_part}'
    elif code_part.startswith('8'):
        # 北交所: 8xxxxx (新三板精选层)
        return f'bj{code_part}'  # 北交所使用bj前缀
    elif code_part.startswith('43') or code_part.startswith('83'):
        # 新三板: 430xxx, 831xxx等
        return f'nq{code_part}'  # 新三板使用nq前缀
    else:
        # 默认深圳 (兼容其他情况)
        return f'sz{code_part}'

def validate_period(period, symbol):
    """验证所选周期是否可获取，并给出相应提示"""
    if period in ["5分钟", "15分钟", "30分钟", "60分钟"]:
        today = datetime.datetime.now()
        if today.weekday() >= 5:  # 周末
            st.warning(f"⚠️ 当前为非交易日，可能无法获取最新的分钟级K线数据。")
        
        # 特定股票的提示
        if symbol.startswith(('300', '688')):  # 创业板和科创板
            st.info("⚠️ 创业板和科创板股票的分钟级数据可能受到更多限制，如无法获取请尝试其他股票。")
            
        # 提醒用户分钟级别数据的限制
        with st.expander("ℹ️ 关于分钟级别数据的说明"):
            st.write("""
            - 分钟级别数据通常**只能获取最近几个交易日**的数据，而非您选择的完整时间范围
            - 数据来源API有流量限制，可能偶尔出现无法获取的情况
            - 如果获取不到数据，请尝试：
                1. 选择其他股票代码
                2. 改用日线、周线或月线周期
                3. 稍后再试
            """)
        return True
    return True

