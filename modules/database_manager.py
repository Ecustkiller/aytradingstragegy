"""
数据库管理模块
使用SQLite替代CSV文件存储，提升查询性能和数据一致性
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import logging
from .logger_config import get_logger
from .config_manager import Config

logger = get_logger(__name__)


class StockDatabase:
    """股票数据库管理器"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径（默认使用配置目录）
        """
        if db_path is None:
            db_path = Config.DATA_DIR / "stock_data.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建股票数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 创建索引以提升查询性能
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_date 
            ON stock_data(symbol, date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date 
            ON stock_data(date)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 数据库初始化完成: {self.db_path}")
    
    def save_stock_data(
        self,
        symbol: str,
        df: pd.DataFrame,
        replace: bool = False
    ) -> int:
        """
        保存股票数据到数据库
        
        Args:
            symbol: 股票代码
            df: 包含OHLCV数据的DataFrame，索引为日期
            replace: 是否替换已存在的数据
        
        Returns:
            int: 保存的记录数
        """
        if df.empty:
            return 0
        
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            # 准备数据
            df = df.copy()
            df.reset_index(inplace=True)
            df['symbol'] = symbol
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 选择需要的列
            columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            if 'amount' in df.columns:
                columns.append('amount')
            
            df = df[columns]
            
            # 保存到数据库
            if replace:
                # 删除旧数据
                cursor = conn.cursor()
                cursor.execute("DELETE FROM stock_data WHERE symbol = ?", (symbol,))
                conn.commit()
            
            df.to_sql('stock_data', conn, if_exists='append', index=False)
            count = len(df)
            logger.info(f"✅ 保存 {symbol} 数据: {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"❌ 保存数据失败: {symbol} - {str(e)}", exc_info=True)
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def get_stock_data(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        从数据库获取股票数据
        
        Args:
            symbol: 股票代码
            start: 开始日期（YYYY-MM-DD）
            end: 结束日期（YYYY-MM-DD）
        
        Returns:
            pd.DataFrame: 包含OHLCV数据的DataFrame，索引为日期
        """
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            query = "SELECT * FROM stock_data WHERE symbol = ?"
            params = [symbol]
            
            if start:
                query += " AND date >= ?"
                params.append(start)
            
            if end:
                query += " AND date <= ?"
                params.append(end)
            
            query += " ORDER BY date"
            
            df = pd.read_sql_query(query, conn, params=params)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 获取数据失败: {symbol} - {str(e)}", exc_info=True)
            return pd.DataFrame()
        finally:
            conn.close()
    
    def get_latest_date(self, symbol: str) -> Optional[str]:
        """
        获取股票的最新数据日期
        
        Args:
            symbol: 股票代码
        
        Returns:
            str: 最新日期（YYYY-MM-DD）或None
        """
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(date) FROM stock_data WHERE symbol = ?",
                (symbol,)
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"❌ 获取最新日期失败: {symbol} - {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_all_symbols(self) -> List[str]:
        """
        获取数据库中所有股票代码
        
        Returns:
            List[str]: 股票代码列表
        """
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol")
            symbols = [row[0] for row in cursor.fetchall()]
            return symbols
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {str(e)}", exc_info=True)
            return []
        finally:
            conn.close()
    
    def get_data_count(self, symbol: Optional[str] = None) -> int:
        """
        获取数据记录数
        
        Args:
            symbol: 股票代码（None表示所有股票）
        
        Returns:
            int: 记录数
        """
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            cursor = conn.cursor()
            if symbol:
                cursor.execute("SELECT COUNT(*) FROM stock_data WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("SELECT COUNT(*) FROM stock_data")
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ 获取数据统计失败: {str(e)}")
            return 0
        finally:
            conn.close()
    
    def optimize_database(self):
        """优化数据库（VACUUM和ANALYZE）"""
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.commit()
            logger.info("✅ 数据库优化完成")
        except Exception as e:
            logger.error(f"❌ 数据库优化失败: {str(e)}", exc_info=True)
        finally:
            conn.close()


# 全局数据库实例
_db_instance: Optional[StockDatabase] = None


def get_database() -> StockDatabase:
    """获取全局数据库实例（单例模式）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = StockDatabase()
    return _db_instance

