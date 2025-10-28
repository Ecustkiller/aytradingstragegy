from datetime import datetime

import pandas as pd
from loguru import logger

from config import DATA_DIR


class CsvDataLoader:
    def __init__(self):
        pass

    def _read_csv(self, symbol, path='quotes'):
        import os
        import glob
        
        # 处理路径：如果是绝对路径，直接使用；否则用DATA_DIR
        if os.path.isabs(path):
            base_path = path
        else:
            base_path = DATA_DIR.joinpath(path)
        
        # 尝试标准格式：symbol.csv
        csv = os.path.join(base_path, f'{symbol}.csv')
        if os.path.exists(csv):
            df = pd.read_csv(csv, index_col=None)
        else:
            # 尝试stock_data格式：股票代码_股票名.csv
            stock_code = symbol.split('.')[0]  # 提取股票代码（去掉.SH/.SZ）
            pattern = os.path.join(base_path, f'{stock_code}_*.csv')
            matches = glob.glob(pattern)
            
            if not matches:
                logger.warning(f'{csv}不存在，也未找到{stock_code}_*.csv格式文件')
                return None
            
            csv = matches[0]  # 使用第一个匹配的文件
            df = pd.read_csv(csv, index_col=None)
        
        df['date'] = df['date'].apply(lambda x: str(x))
        df['date'] = pd.to_datetime(df['date'])
        df['symbol'] = symbol
        df.dropna(inplace=True)
        return df

    def read_dfs(self, symbols: list[str],path='quotes',start_date='20100101', end_date=datetime.now().strftime('%Y%m%d')):
        dfs = {}
        for s in symbols:
            df = self._read_csv(s, path=path)
            if df is None:
                continue  # 跳过找不到的股票
            df.sort_values(by='date', ascending=True, inplace=True)
            df = df[df['date'] >= start_date]
            df = df[df['date'] <= end_date]
            dfs[s] = df
        return dfs

    def read_df(self, symbols: list[str],start_date='20100101', end_date=datetime.now().strftime('%Y%m%d'),
               path='quotes'):
        dfs = []
        for s in symbols:
            df = self._read_csv(s, path=path)
            if df is not None:
                dfs.append(df)

        df = pd.concat(dfs, axis=0)
        df.sort_values(by='date', ascending=True, inplace=True)
        df = df[df['date'] >= start_date]
        df = df[df['date'] <= end_date]

        return df

if __name__ == '__main__':
    df = CsvDataLoader().read_df(symbols=['510300.SH','159915.SZ'])
    print(df)