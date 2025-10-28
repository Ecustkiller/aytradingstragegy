#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyTT 麦语言-通达信-同花顺指标实现
来源：https://github.com/mpquant/MyTT

V2.1 2021-6-6 新增 BARSLAST函数
V2.2 2021-6-8 新增 SLOPE,FORCAST线性回归，和回归预测函数
V2.3 2025-8-2 改进 SAM函数,速度提升15倍
"""

import numpy as np
import pandas as pd


# ==================== 0级：核心工具函数 ====================

def RD(N, D=3):
    """四舍五入取3位小数"""
    return np.round(N, D)


def RET(S, N=1):
    """返回序列倒数第N个值,默认返回最后一个"""
    return np.array(S)[-N]


def ABS(S):
    """返回N的绝对值"""
    return np.abs(S)


def MAX(S1, S2):
    """序列max"""
    return np.maximum(S1, S2)


def MIN(S1, S2):
    """序列min"""
    return np.minimum(S1, S2)


def MA(S, N):
    """求序列的N日平均值，返回序列"""
    return pd.Series(S).rolling(N).mean().values


def REF(S, N=1):
    """对序列整体下移动N,返回序列(shift后会产生NAN)"""
    return pd.Series(S).shift(N).values


def DIFF(S, N=1):
    """前一个值减后一个值,前面会产生nan"""
    return pd.Series(S).diff(N)


def STD(S, N):
    """求序列的N日标准差，返回序列"""
    return pd.Series(S).rolling(N).std(ddof=0).values


def IF(S_BOOL, S_TRUE, S_FALSE):
    """序列布尔判断 res=S_TRUE if S_BOOL==True else S_FALSE"""
    return np.where(S_BOOL, S_TRUE, S_FALSE)


def SUM(S, N):
    """对序列求N天累计和，返回序列"""
    return pd.Series(S).rolling(N).sum().values


def HHV(S, N):
    """最近N天最高价 HHV(C, 5) # 最近5天收盘最高价"""
    return pd.Series(S).rolling(N).max().values


def LLV(S, N):
    """最近N天最低价 LLV(C, 5) # 最近5天收盘最低价"""
    return pd.Series(S).rolling(N).min().values


def EMA(S, N):
    """指数移动平均,为了精度 S>4*N EMA至少需要120周期"""
    return pd.Series(S).ewm(span=N, adjust=False).mean().values


def SMA(S, N, M=1):
    """中国式的SMA,至少需要120周期才精确 (雪球180周期) alpha=1/(1+com)"""
    return pd.Series(S).ewm(alpha=M / N, adjust=False).mean().values


def AVEDEV(S, N):
    """平均绝对偏差 (序列与其平均值的绝对差的平均值)"""
    avedev = pd.Series(S).rolling(N).apply(lambda x: (np.abs(x - x.mean())).mean())
    return avedev.values


def SLOPE(S, N, RS=False):
    """返S序列N周期回线性回归斜率 (默认只返回斜率,不返回整个直线序列)"""
    M = pd.Series(S[-N:])
    poly = np.polyfit(M.index, M.values, deg=1)
    Y = np.polyval(poly, M.index)
    if RS:
        return Y[1] - Y[0], Y
    return Y[1] - Y[0]


# ==================== 1级：应用层函数 ====================

def COUNT(S_BOOL, N):
    """COUNT(CLOSE>O, N): 最近N天满足S_BOO的天数 True的天数"""
    return SUM(S_BOOL, N)


def EVERY(S_BOOL, N):
    """EVERY(CLOSE>O, 5) 最近N天是否都是True"""
    R = SUM(S_BOOL, N)
    return IF(R == N, True, False)


def LAST(S_BOOL, A, B):
    """从前A日到前B日一直满足S_BOOL条件"""
    if A < B:
        A = B
    return S_BOOL[-A:-B].sum() == (A - B)


def EXIST(S_BOOL, N=5):
    """EXIST(CLOSE>3010, N=5) n日内是否存在一天大于3000点"""
    R = SUM(S_BOOL, N)
    return IF(R > 0, True, False)


def BARSLAST(S_BOOL):
    """上一次条件成立到当前的周期"""
    M = np.argwhere(S_BOOL)
    return len(S_BOOL) - int(M[-1]) - 1 if M.size > 0 else -1


def FORCAST(S, N):
    """返S序列N周期回线性回归后的预测值"""
    K, Y = SLOPE(S, N, RS=True)
    return Y[-1] + K


def CROSS(S1, S2):
    """判断穿越 CROSS(MA(C,5),MA(C,10))"""
    CROSS_BOOL = IF(S1 > S2, True, False)
    return COUNT(CROSS_BOOL > 0, 2) == 1


# ==================== 2级：技术指标函数 ====================

def MACD(CLOSE, SHORT=12, LONG=26, M=9):
    """MACD指标"""
    DIF = EMA(CLOSE, SHORT) - EMA(CLOSE, LONG)
    DEA = EMA(DIF, M)
    MACD = (DIF - DEA) * 2
    return RD(DIF), RD(DEA), RD(MACD)


def KDJ(CLOSE, HIGH, LOW, N=9, M1=3, M2=3):
    """KDJ指标"""
    RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
    K = EMA(RSV, (M1 * 2 - 1))
    D = EMA(K, (M2 * 2 - 1))
    J = K * 3 - D * 2
    return K, D, J


def RSI(CLOSE, N=24):
    """RSI相对强弱指标"""
    DIF = CLOSE - REF(CLOSE, 1)
    return RD(SMA(MAX(DIF, 0), N) / SMA(ABS(DIF), N) * 100)


def WR(CLOSE, HIGH, LOW, N=10, N1=6):
    """W&R 威廉指标"""
    WR = (HHV(HIGH, N) - CLOSE) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
    WR1 = (HHV(HIGH, N1) - CLOSE) / (HHV(HIGH, N1) - LLV(LOW, N1)) * 100
    return RD(WR), RD(WR1)


def BIAS(CLOSE, L1=6, L2=12, L3=24):
    """BIAS乖离率"""
    BIAS1 = (CLOSE - MA(CLOSE, L1)) / MA(CLOSE, L1) * 100
    BIAS2 = (CLOSE - MA(CLOSE, L2)) / MA(CLOSE, L2) * 100
    BIAS3 = (CLOSE - MA(CLOSE, L3)) / MA(CLOSE, L3) * 100
    return RD(BIAS1), RD(BIAS2), RD(BIAS3)


def BOLL(CLOSE, N=20, P=2):
    """BOLL指标，布林带"""
    MID = MA(CLOSE, N)
    UPPER = MID + STD(CLOSE, N) * P
    LOWER = MID - STD(CLOSE, N) * P
    return RD(UPPER), RD(MID), RD(LOWER)


def PSY(CLOSE, N=12, M=6):
    """PSY心理线指标"""
    PSY = COUNT(CLOSE > REF(CLOSE, 1), N) / N * 100
    PSYMA = MA(PSY, M)
    return RD(PSY), RD(PSYMA)


def CCI(CLOSE, HIGH, LOW, N=14):
    """CCI顺势指标"""
    TP = (HIGH + LOW + CLOSE) / 3
    return (TP - MA(TP, N)) / (0.015 * AVEDEV(TP, N))


def ATR(CLOSE, HIGH, LOW, N=20):
    """真实波动N日平均值"""
    TR = MAX(MAX((HIGH - LOW), ABS(REF(CLOSE, 1) - HIGH)), ABS(REF(CLOSE, 1) - LOW))
    return MA(TR, N)


def BBI(CLOSE, M1=3, M2=6, M3=12, M4=20):
    """BBI多空指标"""
    return (MA(CLOSE, M1) + MA(CLOSE, M2) + MA(CLOSE, M3) + MA(CLOSE, M4)) / 4


def DMI(CLOSE, HIGH, LOW, M1=14, M2=6):
    """动向指标：结果和同花顺，通达信完全一致"""
    TR = SUM(MAX(MAX(HIGH - LOW, ABS(HIGH - REF(CLOSE, 1))), ABS(LOW - REF(CLOSE, 1))), M1)
    HD = HIGH - REF(HIGH, 1)
    LD = REF(LOW, 1) - LOW
    DMP = SUM(IF((HD > 0) & (HD > LD), HD, 0), M1)
    DMM = SUM(IF((LD > 0) & (LD > HD), LD, 0), M1)
    PDI = DMP * 100 / TR
    MDI = DMM * 100 / TR
    ADX = MA(ABS(MDI - PDI) / (PDI + MDI) * 100, M2)
    ADXR = (ADX + REF(ADX, M2)) / 2
    return PDI, MDI, ADX, ADXR


def TAQ(HIGH, LOW, N):
    """唐安奇通道交易指标，大道至简，能穿越牛熊"""
    UP = HHV(HIGH, N)
    DOWN = LLV(LOW, N)
    MID = (UP + DOWN) / 2
    return UP, MID, DOWN


def TRIX(CLOSE, M1=12, M2=20):
    """三重指数平滑平均线"""
    TR = EMA(EMA(EMA(CLOSE, M1), M1), M1)
    TRIX = (TR - REF(TR, 1)) / REF(TR, 1) * 100
    TRMA = MA(TRIX, M2)
    return TRIX, TRMA


def VR(CLOSE, VOL, M1=26):
    """VR容量比率"""
    LC = REF(CLOSE, 1)
    return SUM(IF(CLOSE > LC, VOL, 0), M1) / SUM(IF(CLOSE <= LC, VOL, 0), M1) * 100


def EMV(HIGH, LOW, VOL, N=14, M=9):
    """简易波动指标"""
    VOLUME = MA(VOL, N) / VOL
    MID = 100 * (HIGH + LOW - REF(HIGH + LOW, 1)) / (HIGH + LOW)
    EMV = MA(MID * VOLUME * (HIGH - LOW) / MA(HIGH - LOW, N), N)
    MAEMV = MA(EMV, M)
    return EMV, MAEMV


def DPO(CLOSE, M1=20, M2=10, M3=6):
    """区间震荡线"""
    DPO = CLOSE - REF(MA(CLOSE, M1), M2)
    MADPO = MA(DPO, M3)
    return DPO, MADPO


def BRAR(OPEN, CLOSE, HIGH, LOW, M1=26):
    """BRAR-ARBR 情绪指标"""
    AR = SUM(HIGH - OPEN, M1) / SUM(OPEN - LOW, M1) * 100
    BR = SUM(MAX(0, HIGH - REF(CLOSE, 1)), M1) / SUM(MAX(0, REF(CLOSE, 1) - LOW), M1) * 100
    return AR, BR


def DMA(CLOSE, N1=10, N2=50, M=10):
    """平行线差指标"""
    DIF = MA(CLOSE, N1) - MA(CLOSE, N2)
    DIFMA = MA(DIF, M)
    return DIF, DIFMA


def MTM(CLOSE, N=12, M=6):
    """动量指标"""
    MTM = CLOSE - REF(CLOSE, N)
    MTMMA = MA(MTM, M)
    return MTM, MTMMA


def ROC(CLOSE, N=12, M=6):
    """变动率指标"""
    ROC = 100 * (CLOSE - REF(CLOSE, N)) / REF(CLOSE, N)
    MAROC = MA(ROC, M)
    return ROC, MAROC


# ==================== 测试代码 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("MyTT 技术指标库测试")
    print("=" * 60)
    
    # 生成测试数据
    np.random.seed(42)
    close = np.cumsum(np.random.randn(100)) + 100
    high = close + np.random.rand(100) * 2
    low = close - np.random.rand(100) * 2
    open_price = close + np.random.randn(100) * 0.5
    volume = np.random.randint(1000, 10000, 100)
    
    print("\n【测试1】MA均线")
    ma5 = MA(close, 5)
    print(f"MA5最新值: {ma5[-1]:.2f}")
    
    print("\n【测试2】MACD指标")
    dif, dea, macd = MACD(close)
    print(f"DIF: {dif[-1]:.2f}, DEA: {dea[-1]:.2f}, MACD: {macd[-1]:.2f}")
    
    print("\n【测试3】BOLL布林带")
    upper, mid, lower = BOLL(close)
    print(f"UPPER: {upper[-1]:.2f}, MID: {mid[-1]:.2f}, LOWER: {lower[-1]:.2f}")
    
    print("\n【测试4】RSI相对强弱")
    rsi = RSI(close, 14)
    print(f"RSI(14): {rsi[-1]:.2f}")
    
    print("\n【测试5】KDJ指标")
    k, d, j = KDJ(close, high, low)
    print(f"K: {k[-1]:.2f}, D: {d[-1]:.2f}, J: {j[-1]:.2f}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
