"""
常量定义模块
集中管理所有魔法数字和配置常量
"""
from typing import Final

# ========== 缓存配置 ==========
CACHE_TTL_ONLINE_DATA: Final[int] = 3600  # 在线数据缓存时间（秒）- 1小时
CACHE_TTL_LOCAL_DATA: Final[int] = 7200  # 本地数据缓存时间（秒）- 2小时

# ========== API限流配置 ==========
TUSHARE_RATE_LIMIT_CALLS: Final[int] = 1500  # Tushare API调用限制（次/分钟）
TUSHARE_RATE_LIMIT_PERIOD: Final[int] = 60  # 限流周期（秒）
TUSHARE_SLEEP_INTERVAL: Final[float] = 0.04  # API调用间隔（秒）- 约1500次/分钟

# ========== 异步并发配置 ==========
ASYNC_MAX_WORKERS_DEFAULT: Final[int] = 10  # 默认最大并发数
ASYNC_MAX_WORKERS_MIN: Final[int] = 5  # 最小并发数
ASYNC_MAX_WORKERS_MAX: Final[int] = 20  # 最大并发数
ASYNC_BATCH_FETCH_WORKERS: Final[int] = 5  # 批量获取默认并发数

# ========== 数据获取配置 ==========
MAX_DATA_COUNT_DAILY: Final[int] = 1000  # 日线数据最大获取数量
MAX_DATA_COUNT_WEEKLY: Final[int] = 200  # 周线数据最大获取数量
MAX_DATA_COUNT_MONTHLY: Final[int] = 100  # 月线数据最大获取数量
MIN_DATA_COUNT_DAILY: Final[int] = 100  # 日线数据最小获取数量
MIN_DATA_COUNT_WEEKLY: Final[int] = 52  # 周线数据最小获取数量
MIN_DATA_COUNT_MONTHLY: Final[int] = 24  # 月线数据最小获取数量
DATA_BUFFER_DAYS: Final[int] = 50  # 数据缓冲天数（多获取一些确保覆盖）

# ========== 数据返回限制 ==========
MAX_RETURN_ROWS: Final[int] = 500  # 最大返回行数（用于数据截断）

# ========== 重试配置 ==========
RETRY_MAX_ATTEMPTS: Final[int] = 3  # 最大重试次数
RETRY_WAIT_MIN: Final[int] = 2  # 最小等待时间（秒）
RETRY_WAIT_MAX: Final[int] = 10  # 最大等待时间（秒）

# ========== 日志配置 ==========
LOG_BATCH_SIZE: Final[int] = 50  # 批量操作日志间隔
LOG_SKIP_INTERVAL: Final[int] = 100  # 跳过操作日志间隔
LOG_ERROR_DISPLAY_LIMIT: Final[int] = 5  # 错误显示限制（超过后只记录日志）

# ========== 进度更新配置 ==========
PROGRESS_UPDATE_INTERVAL: Final[int] = 50  # 进度更新间隔（每N个操作更新一次）
