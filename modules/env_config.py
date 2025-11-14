"""
环境变量统一管理模块
集中管理所有环境变量配置，提供类型安全的访问接口
"""
import os
from typing import Optional, List
from pathlib import Path
from .logger_config import get_logger

logger = get_logger(__name__)


class EnvConfig:
    """环境变量配置管理器"""
    
    # ========== Tushare配置 ==========
    @staticmethod
    def get_tushare_token() -> Optional[str]:
        """获取Tushare Token"""
        return os.getenv("TUSHARE_TOKEN") or os.getenv("TS_TOKEN")
    
    @staticmethod
    def has_tushare_token() -> bool:
        """检查是否配置了Tushare Token"""
        return bool(EnvConfig.get_tushare_token())
    
    # ========== 代理配置 ==========
    @staticmethod
    def get_proxy_url() -> Optional[str]:
        """获取代理URL"""
        return os.getenv("PROXY_URL") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
    
    @staticmethod
    def get_proxy_enabled() -> bool:
        """检查是否启用代理"""
        return os.getenv("USE_PROXY", "false").lower() == "true"
    
    # ========== Webhook配置 ==========
    @staticmethod
    def get_webhook_url() -> Optional[str]:
        """获取Webhook URL"""
        return os.getenv("WEBHOOK_URL") or os.getenv("DINGTALK_WEBHOOK")
    
    @staticmethod
    def get_webhook_secret() -> Optional[str]:
        """获取Webhook密钥"""
        return os.getenv("WEBHOOK_SECRET")
    
    # ========== 日志配置 ==========
    @staticmethod
    def get_log_level() -> str:
        """获取日志级别"""
        return os.getenv("LOG_LEVEL", "INFO").upper()
    
    @staticmethod
    def get_debug_mode() -> bool:
        """检查是否启用调试模式"""
        return os.getenv("DEBUG", "false").lower() == "true"
    
    # ========== 数据目录配置 ==========
    @staticmethod
    def get_data_dir() -> Path:
        """获取数据目录"""
        data_dir = os.getenv("DATA_DIR")
        if data_dir:
            return Path(data_dir)
        return Path.home() / "stock_data"
    
    @staticmethod
    def get_cache_dir() -> Path:
        """获取缓存目录"""
        cache_dir = os.getenv("CACHE_DIR")
        if cache_dir:
            return Path(cache_dir)
        return Path.home() / ".cache" / "aytrading"
    
    # ========== 数据库配置 ==========
    @staticmethod
    def get_database_path() -> Optional[Path]:
        """获取数据库路径"""
        db_path = os.getenv("DATABASE_PATH")
        if db_path:
            return Path(db_path)
        return None
    
    @staticmethod
    def get_database_url() -> Optional[str]:
        """获取数据库连接URL"""
        return os.getenv("DATABASE_URL")
    
    # ========== API配置 ==========
    @staticmethod
    def get_api_timeout() -> float:
        """获取API超时时间（秒）"""
        return float(os.getenv("API_TIMEOUT", "30.0"))
    
    @staticmethod
    def get_api_retry_count() -> int:
        """获取API重试次数"""
        return int(os.getenv("API_RETRY_COUNT", "3"))
    
    # ========== 异步配置 ==========
    @staticmethod
    def get_async_max_workers() -> int:
        """获取异步最大并发数"""
        return int(os.getenv("ASYNC_MAX_WORKERS", "10"))
    
    @staticmethod
    def get_async_enabled() -> bool:
        """检查是否启用异步模式"""
        return os.getenv("ASYNC_ENABLED", "true").lower() == "true"
    
    # ========== 缓存配置 ==========
    @staticmethod
    def get_cache_enabled() -> bool:
        """检查是否启用缓存"""
        return os.getenv("CACHE_ENABLED", "true").lower() == "true"
    
    @staticmethod
    def get_cache_ttl() -> int:
        """获取缓存TTL（秒）"""
        return int(os.getenv("CACHE_TTL", "3600"))
    
    # ========== 功能开关 ==========
    @staticmethod
    def get_feature_enabled(feature_name: str) -> bool:
        """检查功能是否启用"""
        env_var = f"FEATURE_{feature_name.upper()}_ENABLED"
        return os.getenv(env_var, "true").lower() == "true"
    
    # ========== 验证配置 ==========
    @staticmethod
    def validate() -> List[str]:
        """
        验证配置完整性
        
        Returns:
            List[str]: 警告信息列表
        """
        warnings = []
        
        # 检查Tushare Token
        if not EnvConfig.has_tushare_token():
            warnings.append("⚠️ TUSHARE_TOKEN 未设置，Tushare数据源将不可用")
        
        # 检查数据目录
        data_dir = EnvConfig.get_data_dir()
        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                warnings.append(f"⚠️ 无法创建数据目录 {data_dir}: {str(e)}")
        
        return warnings
    
    # ========== 打印配置摘要 ==========
    @staticmethod
    def print_summary():
        """打印配置摘要（隐藏敏感信息）"""
        logger.info("=" * 50)
        logger.info("环境配置摘要")
        logger.info("=" * 50)
        logger.info(f"Tushare Token: {'已配置' if EnvConfig.has_tushare_token() else '未配置'}")
        logger.info(f"代理: {'启用' if EnvConfig.get_proxy_enabled() else '禁用'}")
        logger.info(f"调试模式: {'启用' if EnvConfig.get_debug_mode() else '禁用'}")
        logger.info(f"日志级别: {EnvConfig.get_log_level()}")
        logger.info(f"数据目录: {EnvConfig.get_data_dir()}")
        logger.info(f"缓存目录: {EnvConfig.get_cache_dir()}")
        logger.info(f"异步模式: {'启用' if EnvConfig.get_async_enabled() else '禁用'}")
        logger.info(f"异步并发数: {EnvConfig.get_async_max_workers()}")
        logger.info("=" * 50)


# 全局配置实例
env_config = EnvConfig()

