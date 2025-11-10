"""
主应用模块 - 主程序入口
"""
import streamlit as st
import matplotlib
import os
import sys

# 设置时区为中国标准时间
os.environ['TZ'] = 'Asia/Shanghai'
try:
    import time
    time.tzset()
except AttributeError:
    # Windows系统不支持tzset
    pass

# 设置页面配置（必须是第一个Streamlit命令）
st.set_page_config(
    page_title="AY Trading System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置非交互式后端，适合Streamlit
matplotlib.use('Agg')

# 导入自定义模块
from .config import DEFAULT_SESSION_STATE, PERIOD_MAP, STOCK_CATEGORIES, PAGE_STYLE
from .frontend import setup_sidebar, display_market_status, display_chart, display_data_info, initialize_session_state, display_trade_advice
from .data_loader import get_stock_data
from .indicators import calculate_technical_indicators
from .utils import validate_period

def main():
    """主函数，应用程序入口点"""
    # 应用自定义CSS样式
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='title-container'><h1>AY Trading System 📈</h1></div>", unsafe_allow_html=True)
    
    # 初始化会话状态
    initialize_session_state()
    
    # 设置侧边栏并获取用户参数
    params = setup_sidebar()
    
    # 打印调试信息
    print(f"当前参数: {params}")
    
    # 根据功能模式显示不同界面
    if params["function_mode"] == "💼 持仓监控":
        # 显示持仓监控界面
        try:
            from .portfolio_monitor import display_portfolio_monitor
            display_portfolio_monitor()
        except ImportError as e:
            pass
        except Exception as e:
            st.error(f"❌ 持仓监控功能出现错误: {str(e)}")
            import traceback
            st.text(traceback.format_exc())
        return
    elif params["function_mode"] == "🚀 增强选股":
        # 显示增强版选股界面
        try:
            from .enhanced_momentum_selector import display_enhanced_momentum_selector
            display_enhanced_momentum_selector()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        return
    elif params["function_mode"] == "📈 涨停概念分析":
        # 显示涨停概念分析界面
        try:
            from .concept_analysis import display_concept_analysis
            display_concept_analysis()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 涨停概念分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "📊 指数RPS分析":
        # 显示指数RPS强度排名分析界面
        try:
            from .index_rps_analysis import display_index_rps_analysis
            display_index_rps_analysis()
        except Exception as e:
            # 静默处理错误，不显示误导性提示
            pass
        return
    elif params["function_mode"] == "🌡️ 市场情绪分析":
        # 显示市场情绪分析界面
        try:
            from .market_sentiment_analysis import display_market_sentiment_analysis
            display_market_sentiment_analysis()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 市场情绪分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "📊 ETF动量分析":
        # 显示ETF动量分析界面
        try:
            from .etf_momentum_analysis import display_etf_momentum_analysis
            display_etf_momentum_analysis()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ ETF动量分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "🏭 板块分析":
        # 显示板块与个股联动分析界面
        try:
            from .industry_analysis import display_industry_analysis
            display_industry_analysis()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 板块分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "🎯 AI策略回测":
        # 显示AI Trader策略回测界面
        try:
            from .aitrader_integration import display_aitrader_backtest
            display_aitrader_backtest()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ AI策略回测功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "📝 自定义策略":
        # 显示自定义策略编辑器界面
        try:
            from .custom_strategy_editor import display_custom_strategy_editor
            display_custom_strategy_editor()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 自定义策略编辑器功能出现错误: {str(e)}")
            import traceback
            st.text(traceback.format_exc())
        return
    elif params["function_mode"] == "💾 AI数据管理":
        # 显示AI Trader数据管理界面
        try:
            from .aitrader_integration import display_aitrader_data_management
            display_aitrader_data_management()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ AI数据管理功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "📊 问财数据采集":
        # 显示问财数据采集界面
        try:
            from .wencai_data_collector import display_wencai_collector
            display_wencai_collector()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 问财数据采集功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "🎯 竞价分析":
        # 显示竞价分析界面
        try:
            from .auction_analysis import display_auction_analysis
            display_auction_analysis()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 竞价分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "💰 A股估值":
        # 显示A股估值分析界面
        try:
            from .buffett_indicator import display_buffett_indicator
            display_buffett_indicator()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ A股估值分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "📈 涨停连板":
        # 显示涨停连板分析界面
        try:
            from .limit_up_analysis import display_limit_up_analysis
            display_limit_up_analysis()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 涨停连板分析功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "📅 每日宜忌":
        # 显示每日宜忌界面
        try:
            from .daily_calendar import display_daily_calendar
            display_daily_calendar()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 每日宜忌功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "🎯 Z哥战法选股":
        # 显示Z哥战法选股界面
        try:
            from .zgzf_strategy_bot import display_zgzf_strategy
            display_zgzf_strategy()
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ Z哥战法选股功能出现错误: {str(e)}")
        return
    elif params["function_mode"] == "🎯 突破选股":
        # 显示突破选股界面
        try:
            from .breakthrough_selector_fixed import BreakthroughSelector
            import pandas as pd
            from datetime import datetime
            
            st.header("🎯 突破选股分析")
            st.write("基于技术指标识别具有突破潜力的股票")
            
            # 创建选股器实例
            selector = BreakthroughSelector()
            
            # 添加选股参数设置
            col1, col2 = st.columns(2)
            with col1:
                min_volume = st.number_input("最小成交量(万手)", min_value=1, value=100, step=10)
                min_price = st.number_input("最低股价(元)", min_value=1.0, value=5.0, step=0.5)
            with col2:
                max_price = st.number_input("最高股价(元)", min_value=1.0, value=100.0, step=5.0)
                min_change = st.number_input("最小涨幅(%)", min_value=0.0, value=2.0, step=0.5)
            
            # 添加选股按钮
            if st.button("🚀 开始突破选股", type="primary"):
                with st.spinner("正在分析股票突破信号..."):
                    try:
                        # 执行选股
                        results = selector.select_breakthrough_stocks()
                        
                        if results and len(results) > 0:
                            st.success(f"✅ 发现 {len(results)} 只突破股票")
                            
                            # 显示结果
                            df = pd.DataFrame(results)
                            st.dataframe(df, width="stretch")
                            
                            # 提供下载功能
                            csv = df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 下载选股结果",
                                data=csv,
                                file_name=f"breakthrough_stocks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("⚠️ 暂未发现符合条件的突破股票")
                            
                    except Exception as e:
                        st.error(f"❌ 选股过程中出现错误: {str(e)}")
                        st.error(f"详细错误信息: {repr(e)}")
                        
        except ImportError as e:
            # 模块导入错误已在模块内部处理
            pass
        except Exception as e:
            st.error(f"❌ 突破选股功能出现错误: {str(e)}")
        return
    
    # 单股分析模式
    # 如果用户点击了分析按钮或者数据已经加载
    if params["analyze_clicked"]:
        # 如果用户点击了"开始分析"按钮，从选择的数据源加载数据
        with st.spinner(f"正在获取 {params['symbol']} 的{params['period']}数据..."):
            try:
                # 根据周期选择获取相应的数据
                period_key = PERIOD_MAP.get(params["period"], "daily")
                
                # 获取股票数据
                df = get_stock_data(
                    params["symbol"], 
                    params["start_date"], 
                    params["end_date"], 
                    period_key, 
                    params["data_source"]
                )
                
                if df.empty:
                    st.error(f"未能获取到 {params['symbol']} 的数据。")
                    return
                
                # 标记数据已加载
                st.session_state.data_loaded = True
                
                # 计算技术指标
                df = calculate_technical_indicators(df)
                
                # 🔧 添加调试信息，确保数据正确传递
                print(f"📊 传递给可视化的数据信息:")
                print(f"   数据形状: {df.shape}")
                print(f"   时间范围: {df.index[0]} 到 {df.index[-1]}")
                print(f"   最新收盘价: {df['Close'].iloc[-1]:.2f}")
                
                # 保存数据到会话状态
                st.session_state.df_data = df
                st.session_state.data_source = params["data_source"]
                
                # 显示市场状态面板
                display_market_status(df)
                
                # 显示交易建议
                display_trade_advice(df, params["symbol"])
                
                # 🔧 需求1：K线图放在前面
                # 显示图表
                display_chart(df, params)
                
                # 显示数据信息
                display_data_info(df, params["symbol"], params["period"])
                
            except Exception as e:
                st.error(f"获取数据时出错: {str(e)}")
                return
    elif st.session_state.data_loaded:
        # 如果数据已加载但用户没有点击"开始分析"按钮，仍然显示上一次的结果
        df = st.session_state.df_data
        
        # 显示市场状态面板
        display_market_status(df)
        
        # 显示交易建议
        display_trade_advice(df, params["symbol"])
        
        # 🔧 需求1：K线图放在前面
        # 显示图表
        display_chart(df, {
            "period": params["period"],
            "show_ma": params["show_ma"],
            "show_boll": params["show_boll"],
            "show_vol": params["show_vol"],
            "show_macd": params["show_macd"],
            "show_kdj": params["show_kdj"],
            "show_rsi": params["show_rsi"],
            "data_source": st.session_state.data_source
        })
        
        # 显示数据信息
        display_data_info(df, params["symbol"], params["period"])
        
    else:
        # 显示初始提示信息
        st.info("请在侧边栏输入股票代码并点击'开始分析'按钮获取数据。")

if __name__ == "__main__":
    main()