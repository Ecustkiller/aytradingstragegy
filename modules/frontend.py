"""
前端模块 - 负责Streamlit界面
"""
import streamlit as st
import datetime
import pandas as pd
from .config import PERIOD_MAP, STOCK_CATEGORIES, SIDEBAR_STYLE, PAGE_STYLE, DEFAULT_SESSION_STATE
from .utils import validate_period
from .indicators import analyze_market_status
from .visualization import create_plotly_chart, create_market_status_panel
from .trade_advisor import get_comprehensive_advice


def setup_page_config():
    """设置页面配置"""
    st.set_page_config(
        page_title="股票技术指标分析系统",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 应用自定义CSS样式
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='title-container'><h1>股票技术指标分析系统</h1></div>", unsafe_allow_html=True)

def setup_sidebar():
    """设置侧边栏控件"""
    with st.sidebar:
        st.markdown("### 🔍 功能选择", unsafe_allow_html=True)
        
        # 应用侧边栏样式
        st.markdown(SIDEBAR_STYLE, unsafe_allow_html=True)
        
        # 全局代理设置（放在最前面）
        st.markdown("### 🌐 全局代理设置", unsafe_allow_html=True)
        
        from .global_proxy import enable_global_proxy, disable_global_proxy, is_proxy_enabled, get_current_proxy
        
        # 简化为单个开关
        enable_proxy = st.checkbox(
            "启用全局代理（自动检测）",
            value=st.session_state.get('global_proxy_enabled', False),
            help="自动检测并使用本地代理工具（Hiddify、Clash、V2Ray等）\n支持端口：12334/12335/7890/7891/10808/10809"
        )
        
        # 状态变化时触发
        if enable_proxy != st.session_state.get('global_proxy_enabled', False):
            if enable_proxy:
                with st.spinner("🔍 正在自动检测本地代理..."):
                    success = enable_global_proxy()
                
                if success:
                    st.session_state.global_proxy_enabled = True
                    st.success(f"✅ 全局代理已启用: {get_current_proxy()}")
                    st.rerun()
                else:
                    st.session_state.global_proxy_enabled = False
                    st.error("❌ 未检测到可用代理")
                    st.info("""
                    **请确保以下之一正在运行**：
                    - Hiddify (端口 12334/12335)
                    - Clash (端口 7890/7891)
                    - V2Ray (端口 10808/10809)
                    
                    **或者手动配置代理工具**，确保HTTP代理端口已开启。
                    """)
                    # 取消勾选
                    st.rerun()
            else:
                disable_global_proxy()
                st.session_state.global_proxy_enabled = False
                st.info("🔴 全局代理已禁用")
                st.rerun()
        
        # 显示当前代理状态
        if is_proxy_enabled():
            from .global_proxy import switch_to_next_proxy, get_available_proxies
            
            current_proxy = get_current_proxy()
            available_proxies = get_available_proxies()
            
            # 显示当前代理和可用代理数量
            proxy_count = len(available_proxies) if available_proxies else 1
            st.success(f"🟢 **代理已启用**\n\n📍 当前代理：`{current_proxy}`\n\n🔢 可用代理数：{proxy_count}")
            
            # 如果有多个代理或需要重新扫描，显示切换按钮
            if st.button("🔄 切换到下一个代理", help="如果当前代理被封，可切换到其他可用代理"):
                with st.spinner("正在切换代理..."):
                    success = switch_to_next_proxy()
                
                if success:
                    st.success(f"✅ 已切换到新代理: {get_current_proxy()}")
                    st.rerun()
                else:
                    st.error("❌ 切换失败，没有其他可用代理")
                    st.info("建议：\n1. 检查代理工具是否正常运行\n2. 尝试重启代理工具\n3. 或者暂时禁用代理使用直连")
        else:
            st.info("🔴 代理未启用（使用直连）")
        
        st.markdown("---")
        
        # 功能选择
        function_mode = st.radio(
            "选择功能模式",
            ["📊 单股分析", "💼 持仓监控", "🚀 增强选股", "📈 涨停概念分析", "📊 指数RPS分析", "🌡️ 市场情绪分析", "📈 大盘涨跌统计", "📊 ETF动量分析", "🏭 板块分析", "🎯 突破选股", "🎯 竞价分析", "💰 A股估值", "📈 涨停连板", "📅 每日宜忌", "🎯 AI策略回测", "📝 自定义策略", "💾 AI数据管理", "📊 问财数据采集", "🎯 Z哥战法选股"],
            horizontal=True,
            help="单股分析：分析指定股票的技术指标\n持仓监控：类似同花顺自选股功能，实时监控持仓股票\n增强选股：基于聚宽小市值策略的优化版本\n涨停概念分析：A股涨停概念统计与分析\n指数RPS分析：基于相对强度排名的指数分析\n市场情绪分析：基于多维度指标的市场情绪监控\n大盘涨跌统计：统计指定日期和时分的大盘涨跌幅情况\nETF动量分析：基于三大核心因子的ETF动量评分系统\n板块分析：行业板块排行榜与成分股查询\n竞价分析：集合竞价异动分析，盘前选股神器\nA股估值：巴菲特指标，宏观择时利器\n涨停连板：涨停连板分析，晋级率统计\n每日宜忌：农历黄历查询（娱乐功能）\nAI策略回测：ETF/个股策略回测（V13动量轮动等）\n自定义策略：类聚宽平台的策略编辑器，支持自由编写策略代码\nAI数据管理：A股全量数据更新与管理（Z哥战法批量选股需要）\n问财数据采集：使用问财接口批量采集历史股票数据\nZ哥战法选股：少妇/SuperB1/补票/填坑/上穿60放量等经典战法"
        )
        
        st.markdown("### 🔍 分析参数设置", unsafe_allow_html=True)
        
        # 导入 has_ashare 变量从 data_loader 模块
        from .data_loader import has_ashare
        from .cache_dashboard import integrate_cache_management
        from .performance_dashboard import show_performance_panel
        # 已移除 optimized_data_loader，使用 data_loader 的统一接口
        # from .optimized_data_loader import get_optimized_stock_data, preload_hot_stocks
        
        # 添加数据源选择
        st.markdown("#### 📊 数据源选择")
        
        # 导入数据源检测
        from .data_loader import has_ashare, has_tushare, has_csv
        
        # 构建可用数据源列表
        available_sources = ["AKShare"]  # AKShare 作为基础数据源
        source_help = "AKShare: 免费开源数据源（在线）"
        
        if has_ashare:
            available_sources.insert(0, "Ashare")  # Ashare放在第一位
            source_help = "Ashare: 高速实时数据源\n" + source_help
        
        if has_tushare:
            available_sources.append("Tushare")
            source_help += "\nTushare: 专业金融数据（需Token）"
        
        if has_csv:
            available_sources.append("本地CSV")
            source_help += "\n本地CSV: 离线数据（需先下载）"
        
        # 根据可用数据源显示选择器
        if len(available_sources) > 1:
            data_source = st.radio(
                "选择数据源", 
                available_sources, 
                horizontal=True,
                help=source_help
            )
        else:
            data_source = "AKShare"
            st.info("💡 当前使用 AKShare 数据源")
        
        # 集成缓存管理功能
        integrate_cache_management()
        
        # 智能股票搜索输入框
        st.markdown("#### 🔍 股票搜索")
        
        # 创建两列布局
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 股票搜索输入框
            search_query = st.text_input(
                "股票代码或名称", 
                value="600519", 
                help="支持多种输入方式：\n• 股票代码：600519\n• 股票名称：贵州茅台\n• 简称拼音：GZMT\n• ETF名称：芯片ETF",
                placeholder="输入股票代码、名称或简称..."
            )
        
        with col2:
            # 搜索按钮
            search_clicked = st.button("🔍 搜索", help="搜索匹配的股票")
        
        # 处理搜索逻辑和股票代码智能识别
        symbol = search_query  # 默认使用输入的查询
        
        # 自动尝试识别和转换股票代码（不需要点击搜索按钮）
        try:
            from .stock_search import search_stock_by_name, extract_stock_code
            
            # 先尝试提取股票代码
            extracted_code = extract_stock_code(search_query)
            if extracted_code and extracted_code != search_query:
                symbol = extracted_code
                st.info(f"🎯 自动识别股票代码: {symbol}")
            elif search_query and not search_query.isdigit() and len(search_query.strip()) > 0:
                # 如果输入的不是纯数字代码，尝试搜索匹配
                search_results = search_stock_by_name(search_query, limit=1)
                if search_results:
                    auto_symbol = search_results[0]['code']
                    if auto_symbol != search_query:
                        symbol = auto_symbol
                        st.info(f"🎯 自动匹配: {search_query} → {symbol} {search_results[0]['name']}")
        except Exception as e:
            # 如果自动识别失败，使用原始输入
            print(f"自动搜索失败: {e}")
            pass
        
        # 手动搜索功能（可选）
        if search_clicked and search_query:
            try:
                from .stock_search import search_stock_by_name, extract_stock_code
                
                with st.spinner("正在搜索股票..."):
                    search_results = search_stock_by_name(search_query, limit=5)
                
                if search_results:
                    st.markdown("**🎯 搜索结果:**")
                    
                    # 显示搜索结果供用户选择
                    result_options = []
                    for result in search_results:
                        price_str = f"{result['price']:.2f}" if result['price'] > 0 else "N/A"
                        change_str = f"{result['change_pct']:+.2f}%" if result['change_pct'] != 0 else ""
                        option_text = f"{result['code']} {result['name']} ({result['type']}) - ¥{price_str} {change_str}"
                        result_options.append((result['code'], option_text))
                    
                    # 让用户选择
                    if len(result_options) == 1:
                        # 只有一个结果，自动选择
                        symbol = result_options[0][0]
                        st.success(f"✅ 自动选择: {result_options[0][1]}")
                    else:
                        # 多个结果，让用户选择
                        selected_option = st.selectbox(
                            "请选择股票:",
                            options=[code for code, _ in result_options],
                            format_func=lambda x: next(text for code, text in result_options if code == x),
                            key="stock_selection"
                        )
                        if selected_option:
                            symbol = selected_option
                            selected_text = next(text for code, text in result_options if code == selected_option)
                            st.success(f"✅ 已选择: {selected_text}")
                else:
                    st.warning(f"❌ 未找到匹配的股票: '{search_query}'")
                    st.info("💡 建议:\n• 检查输入是否正确\n• 尝试使用股票代码\n• 尝试使用完整的股票名称")
                    
            except ImportError:
                st.warning("⚠️ 股票搜索功能需要网络连接，当前使用输入的原始查询")
            except Exception as e:
                st.error(f"❌ 搜索过程中出现错误: {str(e)}")
        
        # 显示当前将要分析的股票
        if symbol and symbol != search_query:
            st.markdown(f"**📊 将要分析:** `{symbol}`")
        
        # 日期选择使用两列布局节省空间
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始", datetime.datetime.now() - datetime.timedelta(days=90))
        with col2:
            end_date = st.date_input("结束", datetime.datetime.now())
        
        # 更新为支持多周期，使用水平布局
        period = st.radio("分析周期", ["日线", "周线", "月线", "60分钟", "30分钟", "15分钟", "5分钟"], horizontal=True)
        
        # 如果用户修改了周期或股票代码，则需要重新加载数据
        if st.session_state.get('current_period') != period or st.session_state.get('current_symbol') != symbol:
            st.session_state.data_loaded = False
            st.session_state.current_period = period
            st.session_state.current_symbol = symbol
        
        # 验证并提示周期选择相关信息
        validate_period(period, symbol)
        
        # 所有技术指标选项都在开始分析按钮前设置，并默认关闭
        st.markdown("#### 📊 技术指标", unsafe_allow_html=True)
        
        # 使用3列布局显示技术指标选项
        col1, col2, col3 = st.columns(3)
        with col1:
            show_ma = st.checkbox("均线", value=False)
        with col2:
            show_boll = st.checkbox("布林带", value=False)
        with col3:
            show_vol = st.checkbox("成交量", value=False)
            
        col1, col2, col3 = st.columns(3)
        with col1:
            show_macd = st.checkbox("MACD", value=False)
        with col2:
            show_kdj = st.checkbox("KDJ", value=False)
        with col3:
            show_rsi = st.checkbox("RSI", value=False)
        
        # 开始分析按钮放在技术指标选项后
        analyze_clicked = st.button("开始分析", type="primary", help="点击后开始获取数据并分析", width="stretch")
        
        # 返回所有用户选择的参数
        return {
            "function_mode": function_mode,
            "data_source": data_source,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "period": period,
            "show_ma": show_ma,
            "show_boll": show_boll,
            "show_vol": show_vol,
            "show_macd": show_macd,
            "show_kdj": show_kdj,
            "show_rsi": show_rsi,
            "analyze_clicked": analyze_clicked
        }

def display_market_status(df):
    """显示市场状态面板"""
    if df is None or df.empty:
        return
    
    try:
        st.markdown("<h3 style='margin-top:0.1rem;margin-bottom:0.1rem;'>📋 技术状态面板</h3>", unsafe_allow_html=True)
        
        # 分析市场状态
        market_status = analyze_market_status(df)
        
        if not market_status:
            st.warning("无法计算技术指标状态，请确保数据包含足够的历史记录")
            return
            
        # 使用列布局显示技术状态
        cols = st.columns([1, 1, 1, 1, 1, 1])
        
        # MA状态
        with cols[0]:
            ma = market_status.get("ma", {})
            ma_status = ma.get("status", "未知")
            ma_color = "green" if ma_status == "看涨" else "red" if ma_status == "看跌" else "gray"
            st.metric(
                label="均线状态", 
                value=ma_status,
                delta=f"MA5: {ma.get('ma5', 0):.2f}",
                delta_color="off"
            )
            st.markdown(f"<p style='color:{ma_color};text-align:center;line-height:1;margin:0;font-size:0.7rem;'>MA10: {ma.get('ma10', 0):.2f}<br>MA20: {ma.get('ma20', 0):.2f}</p>", unsafe_allow_html=True)
        
        # MACD状态
        with cols[1]:
            macd = market_status.get("macd", {})
            macd_status = macd.get("status", "未知")
            macd_color = "green" if macd.get("hist", 0) > 0 else "red"
            
            # 确保MACD状态显示完整，避免截断
            if macd_status == "看涨趋势":
                display_status = "看涨"
            elif macd_status == "看跌趋势":
                display_status = "看跌"
            else:
                display_status = macd_status
            
            st.metric(
                label="MACD状态",
                value=display_status,
                delta=f"DIF: {macd.get('dif', 0):.3f}",
                delta_color="off"
            )
            st.markdown(f"<p style='color:{macd_color};text-align:center;line-height:1;margin:0;font-size:0.7rem;'>DEA: {macd.get('dea', 0):.3f}<br>HIST: {macd.get('hist', 0):.3f}</p>", unsafe_allow_html=True)
        
        # RSI状态
        with cols[2]:
            rsi = market_status.get("rsi", {})
            rsi_status = rsi.get("status", "未知")
            rsi_color = "red" if rsi.get("value", 0) > 70 else "green" if rsi.get("value", 0) < 30 else "gray"
            st.metric(
                label="RSI状态", 
                value=rsi_status,
                delta=f"{rsi.get('change', 0):.2f}",
                delta_color="normal" if rsi.get('change', 0) > 0 else "inverse"
            )
            st.markdown(f"<p style='color:{rsi_color};text-align:center;line-height:1;margin:0;font-size:0.7rem;'>RSI(14): {rsi.get('value', 0):.2f}</p>", unsafe_allow_html=True)
        
        # KDJ状态
        with cols[3]:
            kdj = market_status.get("kdj", {})
            kdj_status = kdj.get("status", "未知")
            kdj_color = "red" if kdj_status == "超买" or kdj_status == "死叉" else "green" if kdj_status == "超卖" or kdj_status == "金叉" else "gray"
            st.metric(
                label="KDJ状态", 
                value=kdj_status,
                delta=f"K: {kdj.get('k', 0):.2f}",
                delta_color="off"
            )
            st.markdown(f"<p style='color:{kdj_color};text-align:center;line-height:1;margin:0;font-size:0.7rem;'>D: {kdj.get('d', 0):.2f}<br>J: {kdj.get('j', 0):.2f}</p>", unsafe_allow_html=True)
        
        # 成交量状态
        with cols[4]:
            volume = market_status.get("volume", {})
            vol_status = volume.get("status", "未知")
            vol_color = "red" if vol_status == "放量" else "green" if vol_status == "缩量" else "gray"
            vol_change = volume.get("change", 0)
            st.metric(
                label="成交量状态", 
                value=vol_status,
                delta=f"{vol_change:.2f}%" if vol_change != 0 else None,
                delta_color="normal" if vol_change > 0 else "inverse"
            )
            # 将成交量转换为更易读的格式（以万为单位）
            vol_value = volume.get("value", 0)
            vol_display = f"{vol_value/10000:.2f}万" if vol_value < 1000000 else f"{vol_value/10000000:.2f}千万"
            st.markdown(f"<p style='color:{vol_color};text-align:center;line-height:1;margin:0;font-size:0.7rem;'>{vol_display}</p>", unsafe_allow_html=True)
        
        # 价格位置
        with cols[5]:
            price = market_status.get("price", {})
            position_status = price.get("status", "未知")
            position_color = "red" if position_status == "高位" else "green" if position_status == "低位" else "gray"
            price_change = price.get("change", 0)
            st.metric(
                label="价格位置", 
                value=position_status,
                delta=f"{price_change:.2f}%",
                delta_color="normal" if price_change > 0 else "inverse"
            )
            st.markdown(f"<p style='color:{position_color};text-align:center;line-height:1;margin:0;font-size:0.7rem;'>位置: {price.get('position', 0):.2f}%<br>价格: {price.get('value', 0):.2f}</p>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"显示技术状态面板时出错: {str(e)}")

def display_trade_advice(df, symbol):
    """显示交易建议（含峰级线分析）"""
    if df is None or df.empty:
        return

    try:
        # 获取交易建议
        advice = get_comprehensive_advice(df)

        if not advice:
            st.warning("无法生成交易建议，请确保数据包含足够的历史记录")
            return

        # 设置标题
        st.markdown("<h3 style='margin-top:1rem;margin-bottom:0.5rem;'>💡 智能交易建议（峰级线趋势）</h3>", unsafe_allow_html=True)

        # 获取建议内容
        action = advice.get("action", "观望")
        position = advice.get("position", 0)
        reason = advice.get("reason", "无具体理由")
        peak_valley_info = advice.get("peak_valley_info", {})

        # 设置颜色
        action_color = "green" if action == "买入" else "red" if action == "卖出" else "#FFA500"  # 橙色用于观望

        # 创建两列布局
        col1, col2 = st.columns([1, 3])

        # 左侧显示建议和仓位
        with col1:
            # 创建一个带有颜色的卡片样式
            card_style = f"""
            <div style="
                background-color: {action_color}22;
                border-left: 5px solid {action_color};
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 10px;
                text-align: center;
            ">
                <h2 style="color: {action_color}; margin:0;">{action}</h2>
                <h3 style="margin:5px 0;">仓位: {position}%</h3>
                <p style="font-size: 0.8rem; color: gray; margin:0;">股票代码: {symbol}</p>
            </div>
            """
            st.markdown(card_style, unsafe_allow_html=True)

            # 显示关键价位信息
            support_levels = peak_valley_info.get('support_levels', [])
            resistance_levels = peak_valley_info.get('resistance_levels', [])

            if support_levels or resistance_levels:
                current_price = df['Close'].iloc[-1]

                price_info = f"""
                <div style="
                    background-color: #f0f8ff;
                    border: 1px solid #4682b4;
                    padding: 10px;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-size: 0.85rem;
                ">
                    <h4 style="margin:5px 0;color:#4682b4;">📍 关键价位</h4>
                    <p style="margin:5px 0;"><strong>当前价:</strong> {current_price:.2f}</p>
                """

                if resistance_levels:
                    price_info += f"<p style='margin:5px 0;color:red;'><strong>压力位:</strong> {', '.join([f'{r:.2f}' for r in resistance_levels[:3]])}</p>"

                if support_levels:
                    price_info += f"<p style='margin:5px 0;color:green;'><strong>支撑位:</strong> {', '.join([f'{s:.2f}' for s in support_levels[:3]])}</p>"

                # 添加止损止盈信息
                if 'stop_loss' in advice and advice['stop_loss']:
                    price_info += f"<p style='margin:5px 0;color:#ff4444;'><strong>建议止损:</strong> {advice['stop_loss']:.2f}</p>"

                if 'take_profit' in advice and advice['take_profit']:
                    price_info += f"<p style='margin:5px 0;color:#44ff44;'><strong>建议止盈:</strong> {advice['take_profit']:.2f}</p>"

                price_info += "</div>"
                st.markdown(price_info, unsafe_allow_html=True)

        # 右侧显示建议理由
        with col2:
            # 创建一个理由卡片
            reason_style = f"""
            <div style="
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
            ">
                <h4 style="margin-top:0;">分析理由:</h4>
                <p style="line-height: 1.8;">{reason}</p>
            </div>
            """
            st.markdown(reason_style, unsafe_allow_html=True)

            # 显示交易形态信息
            patterns = peak_valley_info.get('patterns', [])
            if patterns:
                st.markdown("##### 📊 识别到的交易形态")

                # 按置信度排序
                patterns_sorted = sorted(patterns, key=lambda x: x.get('confidence', 0), reverse=True)

                for i, pattern in enumerate(patterns_sorted[:3]):  # 只显示前3个
                    pattern_name = pattern.get('pattern', '未知形态')
                    pattern_type = pattern.get('type', 'neutral')
                    pattern_confidence = pattern.get('confidence', 0) * 100
                    pattern_desc = pattern.get('description', '')

                    # 根据类型设置颜色
                    badge_color = "#28a745" if pattern_type == 'bullish' else "#dc3545" if pattern_type == 'bearish' else "#6c757d"
                    type_text = "看涨" if pattern_type == 'bullish' else "看跌" if pattern_type == 'bearish' else "中性"

                    pattern_html = f"""
                    <div style="
                        background-color: {badge_color}15;
                        border-left: 3px solid {badge_color};
                        padding: 8px 12px;
                        margin: 8px 0;
                        border-radius: 4px;
                    ">
                        <strong style="color:{badge_color};">🎯 {pattern_name}</strong>
                        <span style="
                            background-color: {badge_color};
                            color: white;
                            padding: 2px 8px;
                            border-radius: 10px;
                            font-size: 0.75rem;
                            margin-left: 8px;
                        ">{type_text}</span>
                        <span style="
                            color: gray;
                            font-size: 0.75rem;
                            margin-left: 8px;
                        ">置信度: {pattern_confidence:.0f}%</span>
                        <p style="margin: 5px 0 0 0; font-size: 0.85rem; color: #555;">{pattern_desc}</p>
                    </div>
                    """
                    st.markdown(pattern_html, unsafe_allow_html=True)

        # 添加免责声明
        st.markdown("""
        <div style="font-size: 0.7rem; color: gray; margin-top: 10px; text-align: center;">
            免责声明: 以上建议基于峰级线趋势和技术指标分析，不构成投资建议。投资决策请结合基本面分析和个人风险承受能力。
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"显示交易建议时出错: {str(e)}")
        import traceback
        st.text(traceback.format_exc())

def display_chart(df, params):
    """显示K线图和技术指标"""
    if df is None or df.empty:
        return
    
    try:
        # 创建Plotly图表
        chart = create_plotly_chart(
            df=df, 
            period=params["period"], 
            show_ma=params["show_ma"], 
            show_boll=params["show_boll"], 
            show_vol=params["show_vol"], 
            show_macd=params["show_macd"], 
            show_kdj=params["show_kdj"], 
            show_rsi=params["show_rsi"],
            data_source=params["data_source"]
        )
        
        if chart is not None:
            # 显示图表
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.error("无法创建图表，请检查数据格式是否正确")
    except Exception as e:
        st.error(f"显示图表时出错: {str(e)}")

def display_data_info(df, symbol, period):
    """显示数据基本信息"""
    if df is None or df.empty:
        return
    
    # 创建一个可折叠的部分来显示数据信息
    with st.expander("数据信息", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("股票代码", symbol)
            
        with col2:
            st.metric("周期", period)
            
        with col3:
            st.metric("数据点数", len(df))
            
        # 显示最新的几个数据点
        st.markdown("### 最新数据")
        st.dataframe(df.tail(5))

def initialize_session_state():
    """初始化会话状态"""
    # 使用DEFAULT_SESSION_STATE中的默认值初始化会话状态
    for key, value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value
