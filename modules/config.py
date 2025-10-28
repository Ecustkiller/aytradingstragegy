"""
配置模块 - 包含全局配置和常量
"""
import datetime
import pandas as pd

# 全局设置
CHINESE_FONT = {'family': 'SimHei', 'size': 14}

# 周期映射
PERIOD_MAP = {
    "日线": "daily", 
    "周线": "weekly", 
    "月线": "monthly",
    "5分钟": "5min",
    "15分钟": "15min",
    "30分钟": "30min",
    "60分钟": "60min"
}

# 股票分类数据
STOCK_CATEGORIES = {
    "热门股票": {
        "600519": "贵州茅台",
        "601318": "中国平安",
        "600036": "招商银行",
        "000858": "五粮液",
        "600276": "恒瑞医药",
        "601166": "兴业银行",
        "000333": "美的集团",
        "600887": "伊利股份",
        "601888": "中国中免",
        "600030": "中信证券"
    },
    "科技板块": {
        "000063": "中兴通讯",
        "002415": "海康威视",
        "600745": "闻泰科技",
        "002230": "科大讯飞",
        "002475": "立讯精密",
        "603986": "兆易创新",
        "688981": "中芯国际",
        "688012": "中微公司",
        "688111": "金山办公",
        "688036": "传音控股"
    },
    "半导体ETF": {
        "512760": "芯片ETF",
        "512480": "半导体ETF",
        "512930": "TMTETF",
        "159995": "芯片50ETF",
        "159601": "科创板50",
        "159825": "半导体50",
        "159611": "中证芯片",
        "159880": "央企科技ETF",
        "512770": "科技龙头ETF",
        "512980": "传媒ETF"
    },
    "医药ETF": {
        "512170": "医疗ETF",
        "159928": "消费ETF",
        "512120": "医药50ETF",
        "159938": "医药ETF",
        "512290": "生物医药ETF",
        "159992": "创新药ETF",
        "513120": "港股创新药",
        "513050": "中概互联",
        "513180": "恒生科技",
        "513330": "恒生医疗"
    },
    "新能源ETF": {
        "515790": "光伏ETF",
        "515030": "新能源车ETF",
        "516160": "新能源ETF",
        "159845": "光伏50ETF",
        "159857": "煤炭ETF",
        "159869": "新能车ETF",
        "159755": "光伏产业ETF",
        "516110": "汽车ETF",
        "159806": "新能源车",
        "159996": "电池ETF"
    },
    "互联网ETF": {
        "159939": "信息技术ETF",
        "513330": "恒生科技ETF",
        "513050": "中概互联ETF",
        "159994": "互联金融ETF",
        "513180": "恒生科技",
        "159859": "腾讯ETF",
        "513010": "恒生互联网ETF",
        "513290": "智能手机ETF",
        "159740": "游戏ETF",
        "159614": "云计算ETF"
    },
    "云计算ETF": {
        "159614": "云计算ETF",
        "516950": "云计算50ETF",
        "159711": "计算机ETF",
        "512720": "计算机ETF",
        "512330": "智能汽车ETF",
        "512670": "军工龙头ETF",
        "512660": "军工ETF",
        "512710": "军工ETF",
        "512680": "军工龙头ETF",
        "512560": "中证军工ETF"
    },
    "AI人工智能": {
        "516000": "科技ETF",
        "512580": "科技ETF",
        "512770": "科技龙头ETF",
        "512070": "证券保险ETF",
        "512880": "证券ETF",
        "512000": "券商ETF",
        "512800": "银行ETF",
        "512070": "证券保险ETF",
        "512690": "酒ETF",
        "512200": "房地产ETF"
    },
    "大盘指数": {
        "159901": "深红利ETF",
        "510300": "沪深300ETF",
        "510500": "中证500ETF",
        "510050": "上证50ETF",
        "510180": "上证180ETF",
        "510330": "沪深300ETF",
        "510880": "红利ETF",
        "512100": "中证1000ETF",
        "512090": "MSCI中国ETF",
        "512990": "MSCI中国A股ETF"
    },
    "行业龙头": {
        "600519": "贵州茅台",
        "601318": "中国平安",
        "600036": "招商银行",
        "601166": "兴业银行",
        "600276": "恒瑞医药",
        "600887": "伊利股份",
        "600309": "万华化学",
        "600031": "三一重工",
        "601012": "隆基绿能",
        "600745": "闻泰科技"
    },
    "特色板块": {
        "880491": "半导体",
        "881359": "云服务",
        "880819": "光伏设备",
        "880952": "锂电池",
        "880418": "新能源车",
        "880488": "军工",
        "880471": "证券",
        "880459": "银行",
        "880466": "医药",
        "880472": "白酒"
    }
}

# 初始化会话状态默认值
DEFAULT_SESSION_STATE = {
    'data_loaded': False,
    'df_data': pd.DataFrame(),
    'current_period': "日线",
    'current_symbol': "600519",
    'indicator_updated': False,
    'data_source': "AKShare"
}

# CSS样式
PAGE_STYLE = """
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
}
h1, h2, h3, h4, h5, h6 {
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}
.title-container {
    margin-top: 0.8rem;
    padding-top: 0.3rem;
    text-align: center;  /* 使标题居中 */
}
</style>
"""

SIDEBAR_STYLE = """
<style>
[data-testid="stSidebar"] .block-container {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
}
[data-testid="stSidebar"] h3 {
    font-size: 1.1rem !important;
    margin-top: 0.3rem !important;
    margin-bottom: 0.3rem !important;
}
[data-testid="stSidebar"] .stRadio > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 0.1rem !important;
}
[data-testid="stSidebar"] .stCheckbox > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    padding: 0.1rem !important;
}
[data-testid="stSidebar"] .stSelectbox > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
[data-testid="stSidebar"] .stDateInput > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
[data-testid="stSidebar"] .stTextInput > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    margin-top: 0.3rem !important;
    margin-bottom: 0.3rem !important;
}
</style>
"""