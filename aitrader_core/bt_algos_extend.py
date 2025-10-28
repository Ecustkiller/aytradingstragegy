from dataclasses import dataclass, asdict
from typing import List, Dict

import bt
import numpy as np
import pandas as pd
from bt import Algo




class SelectTopK(bt.AlgoStack):
    def __init__(self, signal, K=1, dropN=0, sort_descending=True, all_or_none=False, filter_selected=True):
        super(SelectTopK, self).__init__(bt.algos.SetStat(signal),
                                         bt.algos.SelectN(int(K) + int(dropN), sort_descending, all_or_none,
                                                          filter_selected))
        self.dropN = dropN

    def __call__(self, target):
        #print('selectTopK运行.....')
        super(SelectTopK, self).__call__(target)

        if self.dropN > 0:
            sel = target.temp["selected"]
            if self.dropN >= len(sel):
                target.temp['selected'] = []
            else:
                target.temp["selected"] = target.temp["selected"][self.dropN:]

            #print(target.now, target.temp['selected'])
            return True
        return True


class ClosePositionsNotSelected(bt.Algo):
    """
    清仓不在selected中的持仓
    
    这个算法确保只持有selected中的资产，
    将不在selected中的持仓全部清空。
    """
    
    def __init__(self):
        super(ClosePositionsNotSelected, self).__init__()
    
    def __call__(self, target):
        selected = target.temp.get('selected', [])
        
        # 初始化weights字典（如果不存在）
        if 'weights' not in target.temp:
            target.temp['weights'] = {}
        
        # 获取当前所有持仓
        positions = list(target.positions.keys())
        
        # 找出需要清仓的资产（不在selected中）
        to_close = [p for p in positions if p not in selected]
        
        # 清仓
        for security in to_close:
            target.temp['weights'][security] = 0.0
        
        return True

from matplotlib import rcParams
from dataclasses import dataclass, field

# 使用系统可用的中文字体
rcParams['font.sans-serif'] = ['STHeiti', 'Arial Unicode MS', 'Songti SC', 'SimHei']
rcParams['axes.unicode_minus'] = False


@dataclass
class MultiStrategies:
    name: str = '多策略组合'
    id_or_symbols: List[str] = field(default_factory=list)  # 策略组合的id
    start_date: str = '20100101'
    end_date: str = None
    benchmark: str = '510300.SH'
    weight: str = 'WeighEqually'
    select: str = 'SelectAll'
    weight_fixed: Dict[str, int] = field(default_factory=dict)
    period: str = 'RunMonthly'


@dataclass
class Task:
    name: str = '策略'
    symbols: List[str] = field(default_factory=list)

    start_date: str = '20100101'
    end_date: str = None

    benchmark: str = '510300.SH'
    select: str = 'SelectAll'

    select_buy: List[str] = field(default_factory=list)
    buy_at_least_count: int = 0
    select_sell: List[str] = field(default_factory=list)
    sell_at_least_count: int = 1

    order_by_signal: str = ''
    order_by_topK: int = 1
    order_by_dropN: int = 0
    order_by_DESC: bool = True  # 默认从大至小排序

    weight: str = 'WeighEqually'
    weight_fixed: Dict[str, int] = field(default_factory=dict)
    period: str = 'RunDaily'
    period_days: int = None


@dataclass
class StrategyConfig:
    name: str = '策略'
    desc: str = '策略描述'
    config_json: Dict[str, int] = field(default_factory=dict)
    author: str = ''


import importlib


