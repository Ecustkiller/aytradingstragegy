"""
统一配置管理模块
集中管理所有配置项，支持环境变量和默认值
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """配置管理类"""

    # ========== 项目路径 ==========
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    CACHE_DIR = PROJECT_ROOT / os.getenv("CACHE_DIR", "data_cache")
    LOG_DIR = PROJECT_ROOT / "logs"

    # ========== 数据源配置 ==========
    TUSHARE_TOKEN: Optional[str] = os.getenv("TUSHARE_TOKEN")
    AKSHARE_TIMEOUT: int = int(os.getenv("AKSHARE_TIMEOUT", "30"))

    # 股票数据目录
    STOCK_DATA_DIR: str = os.getenv("STOCK_DATA_DIR") or str(DATA_DIR / "stock_data")

    # ========== 通知配置 ==========
    WECOM_WEBHOOK_URL: Optional[str] = os.getenv("WECOM_WEBHOOK_URL")
    DINGTALK_WEBHOOK_URL: Optional[str] = os.getenv("DINGTALK_WEBHOOK_URL")

    # ========== 应用配置 ==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    CACHE_TTL_MINUTES: int = int(os.getenv("CACHE_TTL_MINUTES", "30"))
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "15"))

    # ========== 开发配置 ==========
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))

    # ========== 数据库配置（未来扩展） ==========
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    @classmethod
    def ensure_dirs(cls) -> None:
        """确保必要的目录存在"""
        for dir_path in [cls.DATA_DIR, cls.CACHE_DIR, cls.LOG_DIR, Path(cls.STOCK_DATA_DIR)]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> None:
        """验证必要的配置项"""
        errors = []

        if not cls.TUSHARE_TOKEN:
            errors.append("TUSHARE_TOKEN 未设置，Tushare数据源将不可用")

        if errors:
            print("⚠️  配置警告：")
            for error in errors:
                print(f"  - {error}")
            print("\n请参考 .env.example 文件配置环境变量")

    @classmethod
    def get_tushare_token(cls, raise_on_missing: bool = False) -> Optional[str]:
        """
        获取Tushare Token
        
        Args:
            raise_on_missing: 如果未配置是否抛出异常（默认False，返回None）
        
        Returns:
            Optional[str]: Tushare Token，如果未配置则返回None
        
        Raises:
            ValueError: 当raise_on_missing=True且Token未配置时
        """
        if not cls.TUSHARE_TOKEN:
            if raise_on_missing:
                raise ValueError(
                    "Tushare Token 未配置！\n"
                    "请在 .env 文件中设置 TUSHARE_TOKEN 环境变量\n"
                    "获取Token: https://tushare.pro/register"
                )
            return None
        return cls.TUSHARE_TOKEN

    @classmethod
    def get_webhook_url(cls) -> Optional[str]:
        """获取可用的Webhook URL"""
        return cls.WECOM_WEBHOOK_URL or cls.DINGTALK_WEBHOOK_URL

    @classmethod
    def print_config(cls) -> None:
        """打印当前配置（隐藏敏感信息）"""
        print("=" * 60)
        print("当前配置信息")
        print("=" * 60)
        print(f"项目根目录: {cls.PROJECT_ROOT}")
        print(f"数据目录: {cls.DATA_DIR}")
        print(f"缓存目录: {cls.CACHE_DIR}")
        print(f"日志目录: {cls.LOG_DIR}")
        print(f"股票数据目录: {cls.STOCK_DATA_DIR}")
        print(f"Tushare Token: {'已配置' if cls.TUSHARE_TOKEN else '未配置'}")
        print(f"Webhook URL: {'已配置' if cls.get_webhook_url() else '未配置'}")
        print(f"日志级别: {cls.LOG_LEVEL}")
        print(f"缓存TTL: {cls.CACHE_TTL_MINUTES}分钟")
        print(f"请求限流: {cls.MAX_REQUESTS_PER_MINUTE}次/分钟")
        print(f"调试模式: {cls.DEBUG}")
        print("=" * 60)


# 初始化配置
Config.ensure_dirs()
Config.validate()

# 导出配置实例
config = Config()

if __name__ == "__main__":
    Config.print_config()
