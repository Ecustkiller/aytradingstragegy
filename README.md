# 🎯 AY Trading Strategy - Streamlit版

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io/)

**A股量化交易分析系统 + AI策略回测平台 - Streamlit Web应用**

本项目是一个**完整的Streamlit量化交易系统**,集成了aytrading的所有分析功能(单股分析、选股、板块分析等)以及10种AI量化策略回测、4种数据源支持、实时信号生成等功能。

---

## ✨ 核心特性

### 📊 原生aytrading功能
- **单股技术分析** - 多维度技术指标分析(MA/MACD/KDJ/RSI/BOLL等)
- **增强选股** - 基于聚宽小市值策略的优化版本
- **涨停概念分析** - A股涨停板统计与概念追踪
- **指数RPS分析** - 基于相对强度排名的指数分析
- **市场情绪分析** - 多维度指标的市场情绪监控
- **ETF动量分析** - 基于三大核心因子的ETF动量评分系统
- **板块分析** - 行业板块排行榜与成分股查询
- **突破选股** - 技术突破策略选股

### 🎯 10种量化策略
1. **V13动量轮动策略** - 4只ETF | 20日动量评分 | 双阈值超买识别
2. **聚宽年化收益评分轮动** - 4只ETF | 25日动量×R² | 周度调仓
3. **全天候风险平价策略** - 多资产配置 | 风险平价加权 | 月度再平衡
4. **创业板择时策略** - ROC择时 | 日线交易
5. **创业板布林带策略** - 布林带突破 | 上轨买入下轨卖出
6. **上证50双均线策略** - MA20>MA120择时
7. **沪深300RSRS择时** - 阻力支撑相对强度
8. **大小盘轮动策略** - 创业板vs沪深300 | ROC动量
9. **优质资产动量轮动** - 7资产轮动 | 医药黄金纳指
10. **个股动量轮动策略** - 随机20只A股 | 持仓前5 | 周度调仓

### 📡 4种数据源
- **💾 本地CSV (Baostock)** - 5600+只A股历史数据 | 快速稳定
- **🌐 Ashare (实时)** - 腾讯/新浪数据 | 实时更新 | 免费
- **📊 Tushare (专业版)** - 高质量金融数据 | Token已配置
- **🔧 AKShare (在线)** - 开源多源数据 | 完全免费

### 🛠️ 强大功能
- ✅ **策略下拉选择** - 10种策略快速切换
- ✅ **日期范围回测** - 自定义回测起止日期
- ✅ **交易记录导出** - CSV格式完整交易明细
- ✅ **多策略对比** - 自动生成对比分析表格和曲线
- ✅ **实时信号获取** - V13策略实时交易信号
- ✅ **数据源切换** - 一键切换不同数据源
- ✅ **可视化回测** - 累计收益曲线 + 回撤曲线
- ✅ **详细统计** - 总收益/年化收益/最大回撤/夏普比率
- ✅ **A股数据管理** - 全量数据更新与管理

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone git@github.com:Ecustkiller/aytradingstragegy.git
cd aytradingstrategy_streamlit

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据初始化 (可选)

如果您需要使用**本地CSV数据源**,需要先更新数据:

```bash
# 方式1: Web界面更新 (推荐)
python3 -m streamlit run streamlit_app.py
# 访问 http://localhost:8501 → 💾 AI数据管理 → 开始更新

# 方式2: 命令行更新
cd aitrader_core
python3 update_daily_stock_data.py
```

**注意**: 初次数据更新需要1-2小时(5600+只股票),建议使用**Ashare实时数据源**快速体验。

### 3. 启动应用

```bash
# 启动Streamlit应用
python3 -m streamlit run streamlit_app.py

# 浏览器自动打开 http://localhost:8501
```

---

## 📖 使用指南

### 策略回测流程

#### 步骤1: 访问AI策略回测
```
主界面 → 🎯 AI策略回测
```

#### 步骤2: 选择数据源
点击顶部4个数据源按钮之一:
- **💾 本地CSV** - 用于长时间历史回测(需先更新数据)
- **🌐 Ashare** - 推荐!实时数据,无需预先更新
- **📊 Tushare** - 专业数据源(Token已配置)
- **🔧 AKShare** - 免费在线数据

#### 步骤3: 选择策略
从下拉框选择10种策略之一,系统会显示策略描述。

#### 步骤4: 设置回测参数
- **开始日期**: 默认 2015-01-01
- **结束日期**: 默认今天

#### 步骤5: 开始回测
点击 **🚀 开始回测** 按钮,等待10-30秒。

#### 步骤6: 查看结果
- **关键指标卡片**: 总收益、年化收益、最大回撤、夏普比率
- **累计收益曲线**: 策略表现可视化
- **回撤曲线**: 风险控制分析
- **交易记录表格**: 完整交易明细

#### 步骤7: 导出数据
点击 **📥 下载完整交易记录** 按钮,下载CSV文件。

### 多策略对比

回测2个或更多策略后,界面会自动显示:
- **策略对比表格** - 并排对比关键指标
- **收益曲线叠加图** - 直观比较策略表现

### 实时信号获取

在 **🎯 AI策略回测** 界面,点击 **📡 获取V13实时信号** 按钮,查看V13策略的最新持仓建议。

### ETF数据更新

在 **🎯 AI策略回测** 界面,点击 **🔄 更新ETF数据** 按钮,使用Ashare更新ETF最新数据到本地。

---

## 📁 项目结构

```
aytradingstrategy_streamlit/
├── streamlit_app.py                # Streamlit主入口
├── modules/
│   ├── aitrader_integration.py    # AI策略集成核心模块
│   ├── app.py                      # 主应用逻辑
│   ├── frontend.py                 # 前端界面配置
│   └── __init__.py
├── aitrader_core/                  # AI Trader核心引擎
│   ├── bt_engine.py                # 回测引擎(基于bt库)
│   ├── bt_algos_extend.py          # 自定义算法扩展
│   ├── config.py                   # 配置文件
│   ├── matplotlib_config.py        # 图表配置
│   ├── update_daily_stock_data.py  # 数据更新脚本
│   └── datafeed/                   # 数据加载模块
│       ├── Ashare.py               # Ashare数据源
│       ├── tushare_loader.py       # Tushare数据源
│       ├── akshare_loader.py       # AKShare数据源
│       ├── csv_dataloader.py       # 本地CSV数据加载
│       ├── factor_expr.py          # 因子表达式引擎
│       ├── factor_extends.py       # 扩展因子库
│       └── mytt.py                 # 技术指标库
├── AI功能集成总结.md               # 功能集成说明
├── 数据源使用说明.md               # 数据源详细文档
├── README.md                       # 本文件
└── requirements.txt                # Python依赖
```

---

## 🎯 策略示例

### V13动量轮动策略

**核心逻辑:**
```python
# 4只ETF池
symbols = [
    '518880.SH',  # 黄金ETF
    '513100.SH',  # 纳指ETF
    '159915.SZ',  # 创业板ETF
    '512100.SH'   # 中证1000
]

# 20日动量评分
score = annualized_returns × R²

# 双阈值超买识别
if 7日涨幅 > 35%: score × 0.4
elif 7日涨幅 > 25%: score × 0.6

# 持仓前1只(最高评分)
```

**历史表现 (2015-2024):**
- 年化收益: ~32%
- 最大回撤: ~26%
- 夏普比率: ~1.2

### 全天候风险平价

**核心逻辑:**
```python
# 4种资产类别
资产 = {
    '股票': '159915.SZ',  # 创业板ETF
    '商品': '518880.SH',  # 黄金ETF
    '债券': '511010.SH',  # 国债ETF
    '海外': '513100.SH'   # 纳指ETF
}

# 风险平价加权(等风险贡献)
权重 = WeighERC(资产)

# 月度再平衡
调仓周期 = RunMonthly
```

---

## 📊 数据源对比

| 数据源 | 成本 | 速度 | 质量 | 历史数据 | 推荐场景 |
|--------|------|------|------|---------|---------|
| **本地CSV** | 免费 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 10年+ | 长期回测 |
| **Ashare** | 免费 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 3-5年 | 实时监控 |
| **Tushare** | 积分制 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 10年+ | 专业研究 |
| **AKShare** | 免费 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 5-10年 | 快速验证 |

---

## 🔧 高级配置

### Tushare Token配置

已预配置Token:
```python
TUSHARE_TOKEN = "ad56243b601d82fd5c4aaf04b72d4d9d567401898d46c20f4d905d59"
```

如需更换,修改:
```bash
aitrader_core/datafeed/tushare_loader.py
```

### 添加自定义策略

编辑 `modules/aitrader_integration.py`,在 `STRATEGY_CONFIGS` 字典中添加:

```python
STRATEGY_CONFIGS = {
    # ... 现有策略 ...
    
    "我的策略": {
        "desc": "策略描述",
        "symbols": ['股票代码1', '股票代码2'],
        "order_by_signal": '因子表达式',  # 例如: 'roc(close,20)'
        "order_by_topK": 1,               # 持仓数量
        "weight": 'WeighEqually',         # 加权方式
        "period": 'RunDaily',             # 调仓周期
        "benchmark": '510300.SH',         # 基准代码
        "data_type": "etf"                # 数据类型: etf/stock
    }
}
```

重启应用即可使用。

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

**开发流程:**
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

---

## 📝 更新日志

### v1.0.0 (2025-10-28)

**新增功能:**
- ✅ 创建独立Streamlit项目
- ✅ 集成10种量化策略
- ✅ 支持4种数据源 (本地CSV/Ashare/Tushare/AKShare)
- ✅ 数据源按钮选择界面
- ✅ 交易记录导出 (CSV格式)
- ✅ 多策略对比分析
- ✅ Tushare专业数据源 (Token已配置)
- ✅ 内置AI Trader核心引擎
- ✅ 完整的数据管理功能

---

## 📚 相关文档

- [AI功能集成总结](./AI功能集成总结.md)
- [数据源使用说明](./数据源使用说明.md)

---

## ⚖️ 许可证

MIT License

---

## 📧 联系方式

- **GitHub**: [@Ecustkiller](https://github.com/Ecustkiller)
- **仓库**: [aytradingstragegy](https://github.com/Ecustkiller/aytradingstragegy)

---

## ⭐ Star History

如果这个项目对您有帮助,请给个⭐️支持一下!

---

**免责声明**: 本项目仅供学习交流使用,不构成任何投资建议。量化交易存在风险,请谨慎决策。

