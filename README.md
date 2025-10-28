---
title: AY Trading Strategy
emoji: 📈
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.28.0"
app_file: streamlit_app.py
pinned: false
license: apache-2.0
---

# AY Trading Strategy - AI量化交易策略平台

一个基于Streamlit的A股量化交易策略分析平台，集成多种数据源和分析工具。

## ✨ 主要功能

- 📊 **单股分析**：技术指标分析、K线图展示
- 🚀 **增强选股**：基于多因子的智能选股
- 📈 **涨停概念分析**：A股涨停概念统计与分析
- 📊 **指数RPS分析**：基于相对强度排名的指数分析
- 🌡️ **市场情绪分析**：多维度市场情绪监控
- 📊 **ETF动量分析**：基于三大核心因子的ETF评分
- 🏭 **板块分析**：行业板块排行与成分股查询
- 🎯 **竞价分析**：集合竞价异动分析
- 💰 **A股估值**：巴菲特指标宏观择时
- 📈 **涨停连板**：涨停连板分析与晋级率统计
- 📅 **每日宜忌**：农历黄历查询
- 🎯 **AI策略回测**：ETF/个股策略回测
- 💾 **AI数据管理**：A股全量数据更新
- 📊 **问财数据采集**：自然语言查询股票数据

## 🚀 快速开始

### 在线访问

- Hugging Face: https://huggingface.co/spaces/pyecuster/trading
- Streamlit Cloud: (待部署)

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/ecustkiller/aytradingstrategy_streamlit.git
cd aytradingstrategy_streamlit

# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run streamlit_app.py
```

## 📦 数据源

- **AKShare**: 开源金融数据接口
- **Ashare**: 自定义A股数据源
- **Tushare**: 专业金融数据平台
- **本地CSV**: 支持本地数据导入
- **问财**: 自然语言数据查询

## 🛠️ 技术栈

- **前端框架**: Streamlit
- **数据处理**: Pandas, NumPy
- **数据可视化**: Plotly, Matplotlib
- **回测引擎**: bt, ffn
- **技术指标**: ta, scipy

## 📄 许可证

Apache License 2.0

## 👨‍💻 作者

ecustkiller

## 🙏 致谢

感谢所有开源项目的贡献者！
