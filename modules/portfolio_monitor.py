"""
持仓监控模块
类似同花顺自选股功能，支持添加、删除、实时监控股票
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import time

try:
    import sys
    from pathlib import Path
    # 添加aitrader_core路径
    sys.path.insert(0, str(Path(__file__).parent.parent / 'aitrader_core' / 'datafeed'))
    from Ashare import get_realtime_quotes_sina, get_stock_name
    HAS_ASHARE = True
except ImportError as e:
    print(f"导入Ashare失败: {e}")
    HAS_ASHARE = False

# 导入分时图模块
try:
    from .intraday_chart import display_intraday_chart
    HAS_INTRADAY_CHART = True
except ImportError as e:
    print(f"导入分时图模块失败: {e}")
    HAS_INTRADAY_CHART = False
    # 尝试另一种导入方式
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from intraday_chart import display_intraday_chart
        HAS_INTRADAY_CHART = True
        print("使用备用导入方式成功")
    except Exception as e2:
        print(f"备用导入方式也失败: {e2}")
        HAS_INTRADAY_CHART = False

# 持仓文件路径
PORTFOLIO_FILE = "data/portfolio.json"

def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs("data", exist_ok=True)

def load_portfolio():
    """加载持仓数据"""
    ensure_data_dir()

    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"加载持仓数据失败: {e}")
            return {}
    return {}

def save_portfolio(portfolio):
    """保存持仓数据"""
    ensure_data_dir()

    try:
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"保存持仓数据失败: {e}")
        return False

def add_stock_to_portfolio(stock_code, stock_name, buy_price=None, quantity=None, buy_date=None):
    """添加股票到持仓"""
    portfolio = load_portfolio()

    # 如果股票已存在，更新信息
    if stock_code in portfolio:
        st.warning(f"股票 {stock_code} 已在持仓中")
        return False

    portfolio[stock_code] = {
        'name': stock_name,
        'buy_price': float(buy_price) if buy_price else None,
        'quantity': int(quantity) if quantity else None,
        'buy_date': buy_date.strftime('%Y-%m-%d') if buy_date else None,
        'add_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    if save_portfolio(portfolio):
        st.success(f"✅ 成功添加 {stock_name}({stock_code}) 到持仓")
        return True
    return False

def remove_stock_from_portfolio(stock_code):
    """从持仓中移除股票"""
    portfolio = load_portfolio()

    if stock_code in portfolio:
        stock_name = portfolio[stock_code]['name']
        del portfolio[stock_code]

        if save_portfolio(portfolio):
            st.success(f"✅ 已移除 {stock_name}({stock_code})")
            return True
    else:
        st.warning(f"股票 {stock_code} 不在持仓中")

    return False

def update_stock_info(stock_code, buy_price=None, quantity=None, buy_date=None):
    """更新股票信息"""
    portfolio = load_portfolio()

    if stock_code not in portfolio:
        st.error(f"股票 {stock_code} 不在持仓中")
        return False

    if buy_price is not None:
        portfolio[stock_code]['buy_price'] = float(buy_price)
    if quantity is not None:
        portfolio[stock_code]['quantity'] = int(quantity)
    if buy_date is not None:
        portfolio[stock_code]['buy_date'] = buy_date.strftime('%Y-%m-%d')

    if save_portfolio(portfolio):
        st.success(f"✅ 更新成功")
        return True
    return False

def get_realtime_quotes(stock_codes):
    """获取实时行情数据"""
    if not HAS_ASHARE:
        st.error("❌ Ashare库未安装，无法获取实时数据")
        return None

    try:
        # 使用新的实时行情接口批量获取
        quotes_dict = get_realtime_quotes_sina(stock_codes)
        
        if not quotes_dict:
            st.warning("未获取到任何行情数据")
            return pd.DataFrame()
        
        # 转换为DataFrame格式
        quotes_data = []
        for code in stock_codes:
            # 格式化代码以匹配返回的key
            xcode = code.replace('.XSHG', '').replace('.XSHE', '')
            if not (xcode.startswith('sh') or xcode.startswith('sz')):
                if xcode.startswith('6'):
                    xcode = 'sh' + xcode
                elif xcode.startswith('0') or xcode.startswith('3'):
                    xcode = 'sz' + xcode
            
            if xcode in quotes_dict:
                data = quotes_dict[xcode]
                quotes_data.append({
                    'code': code,
                    'current_price': data['current_price'],
                    'change': data['change'],
                    'change_pct': data['change_pct'],
                    'open': data['open'],
                    'high': data['high'],
                    'low': data['low'],
                    'volume': data['volume'],
                    'amount': data['amount'],
                    'time': data['time']
                })
            else:
                # 如果获取失败，添加空数据
                quotes_data.append({
                    'code': code,
                    'current_price': 0,
                    'change': 0,
                    'change_pct': 0,
                    'open': 0,
                    'high': 0,
                    'low': 0,
                    'volume': 0,
                    'amount': 0,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

        return pd.DataFrame(quotes_data)

    except Exception as e:
        st.error(f"获取实时行情失败: {e}")
        import traceback
        st.error(traceback.format_exc())
        return None

def calculate_portfolio_stats(portfolio_df, quotes_df):
    """计算持仓统计"""
    if portfolio_df.empty or quotes_df.empty:
        return None

    # 合并数据
    merged = portfolio_df.merge(quotes_df, left_on='股票代码', right_on='code', how='left')

    stats = {
        'total_stocks': len(merged),
        'total_value': 0,
        'total_cost': 0,
        'total_profit': 0,
        'total_profit_pct': 0,
        'rising_count': 0,
        'falling_count': 0,
        'flat_count': 0
    }

    for _, row in merged.iterrows():
        if pd.notna(row['持仓数量']) and pd.notna(row['成本价']) and row['current_price'] > 0:
            quantity = row['持仓数量']
            buy_price = row['成本价']
            current_price = row['current_price']

            cost = quantity * buy_price
            value = quantity * current_price
            profit = value - cost

            stats['total_cost'] += cost
            stats['total_value'] += value
            stats['total_profit'] += profit

        # 统计涨跌数量
        if row['change_pct'] > 0:
            stats['rising_count'] += 1
        elif row['change_pct'] < 0:
            stats['falling_count'] += 1
        else:
            stats['flat_count'] += 1

    if stats['total_cost'] > 0:
        stats['total_profit_pct'] = (stats['total_profit'] / stats['total_cost']) * 100

    return stats

def display_portfolio_monitor():
    """显示持仓监控界面"""
    st.title("📊 持仓监控")

    # 检查Ashare
    if not HAS_ASHARE:
        st.error("❌ Ashare库未安装，无法使用持仓监控功能")
        st.info("请安装Ashare库: pip install Ashare")
        return
    
    # 调试信息：显示分时图功能状态
    if HAS_INTRADAY_CHART:
        print("✅ 分时图功能已启用")
    else:
        print("❌ 分时图功能未启用")

    # 加载持仓
    portfolio = load_portfolio()

    # 侧边栏：添加股票
    with st.sidebar:
        st.markdown("### ➕ 添加股票")

        with st.form("add_stock_form"):
            new_code = st.text_input("股票代码", placeholder="例如: 000001 或 600519")
            new_name = st.text_input("股票名称（可选）", placeholder="留空自动获取", help="如果不填写，系统会自动获取股票名称")

            col1, col2 = st.columns(2)
            with col1:
                new_price = st.number_input("成本价（可选）", min_value=0.0, value=0.0, step=0.01, help="可以稍后再填写")
                new_quantity = st.number_input("持仓数量（可选）", min_value=0, value=0, step=100, help="可以稍后再填写")
            with col2:
                new_date = st.date_input("买入日期", value=datetime.now())

            submit = st.form_submit_button("添加到持仓", use_container_width=True)

            if submit and new_code:
                # 如果没有输入名称，自动获取
                stock_name = new_name
                if not stock_name:
                    with st.spinner(f"正在获取 {new_code} 的股票名称..."):
                        stock_name = get_stock_name(new_code)
                        if stock_name:
                            st.success(f"✅ 自动识别: {stock_name}")
                        else:
                            st.error(f"❌ 无法获取股票 {new_code} 的名称，请手动输入")
                            stock_name = None
                
                if stock_name:
                    add_stock_to_portfolio(
                        new_code,
                        stock_name,
                        new_price if new_price > 0 else None,
                        new_quantity if new_quantity > 0 else None,
                        new_date
                    )
                    st.rerun()

        # 添加使用说明
        with st.expander("💡 使用说明"):
            st.markdown("""
            ### 快速上手
            
            **添加股票：**
            - 只需输入股票代码即可
            - 名称会自动获取
            - 成本价和数量可以稍后填写
            
            **编辑信息：**
            - 点击表格中的"✏️"按钮快速编辑
            - 支持修改成本价、数量、日期
            
            **查看盈亏：**
            - 填写成本价和数量后自动计算
            - 红色表示盈利，绿色表示亏损
            
            **排序筛选：**
            - 使用排序功能查看涨跌幅
            - 使用筛选功能查看盈亏情况
            """)

    # 主界面
    if not portfolio:
        st.info("📝 持仓为空，请在侧边栏添加股票")
        return

    # 转换为DataFrame
    portfolio_df = pd.DataFrame([
        {
            '股票代码': code,
            '股票名称': info['name'],
            '成本价': info.get('buy_price'),
            '持仓数量': info.get('quantity'),
            '买入日期': info.get('buy_date'),
            '添加时间': info.get('add_time')
        }
        for code, info in portfolio.items()
    ])

    # 操作按钮
    col1, col2, col3 = st.columns([2, 2, 8])

    with col1:
        if st.button("🔄 刷新行情", type="primary", use_container_width=True):
            st.session_state.refresh_time = datetime.now()

    with col2:
        auto_refresh = st.checkbox("自动刷新", value=False)

    with col3:
        if st.button("🗑️ 清空持仓", use_container_width=True):
            if st.session_state.get('confirm_clear', False):
                portfolio = {}
                save_portfolio(portfolio)
                st.success("已清空持仓")
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ 再次点击确认清空")

    # 获取实时行情
    with st.spinner("正在获取实时行情..."):
        quotes_df = get_realtime_quotes(list(portfolio.keys()))

    if quotes_df is None or quotes_df.empty:
        st.error("❌ 获取行情数据失败")
        return

    # 计算统计数据
    stats = calculate_portfolio_stats(portfolio_df, quotes_df)

    # 显示统计卡片
    st.markdown("---")
    st.markdown("### 📈 持仓概览")

    if stats and stats['total_cost'] > 0:
        # 有成本数据，显示完整统计
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("持仓股票", f"{stats['total_stocks']}只")

        with col2:
            profit_color = "normal" if stats['total_profit'] >= 0 else "inverse"
            st.metric(
                "总盈亏",
                f"¥{stats['total_profit']:,.2f}",
                f"{stats['total_profit_pct']:.2f}%",
                delta_color=profit_color
            )

        with col3:
            st.metric("总市值", f"¥{stats['total_value']:,.2f}")

        with col4:
            st.metric("总成本", f"¥{stats['total_cost']:,.2f}")

        with col5:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <p style="font-size: 0.8rem; margin: 0;">涨跌统计</p>
                <p style="margin: 5px 0;">
                    <span style="color: red;">↑{stats['rising_count']}</span> /
                    <span style="color: green;">↓{stats['falling_count']}</span> /
                    <span style="color: gray;">—{stats['flat_count']}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        # 没有成本数据，显示简化统计
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("持仓股票", f"{stats['total_stocks']}只")
        
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px;">
                <p style="font-size: 0.8rem; margin: 0;">涨跌统计</p>
                <p style="margin: 5px 0;">
                    <span style="color: red;">↑{stats['rising_count']}</span> /
                    <span style="color: green;">↓{stats['falling_count']}</span> /
                    <span style="color: gray;">—{stats['flat_count']}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.info("💡 填写成本价和数量后可查看盈亏统计")

    st.markdown("---")

    # 合并数据
    merged_df = portfolio_df.merge(quotes_df, left_on='股票代码', right_on='code', how='left')

    # 计算盈亏
    merged_df['当前价'] = merged_df['current_price']
    merged_df['涨跌额'] = merged_df['change']
    merged_df['涨跌幅'] = merged_df['change_pct']

    # 计算持仓盈亏
    merged_df['持仓盈亏'] = None
    merged_df['盈亏比例'] = None

    for idx, row in merged_df.iterrows():
        if pd.notna(row['持仓数量']) and pd.notna(row['成本价']) and row['当前价'] > 0:
            quantity = row['持仓数量']
            buy_price = row['成本价']
            current_price = row['当前价']

            profit = (current_price - buy_price) * quantity
            profit_pct = ((current_price - buy_price) / buy_price) * 100

            merged_df.at[idx, '持仓盈亏'] = profit
            merged_df.at[idx, '盈亏比例'] = profit_pct

    # 筛选和排序选项
    col1, col2, col3 = st.columns([3, 3, 6])
    
    with col1:
        filter_option = st.selectbox(
            "筛选",
            ["全部", "盈利", "亏损", "未设置成本"],
            key="filter_option"
        )
    
    with col2:
        sort_option = st.selectbox(
            "排序",
            ["默认", "涨跌幅↓", "涨跌幅↑", "盈亏比例↓", "盈亏比例↑"],
            key="sort_option"
        )

    # 应用筛选
    filtered_df = merged_df.copy()
    if filter_option == "盈利":
        filtered_df = filtered_df[filtered_df['盈亏比例'] > 0]
    elif filter_option == "亏损":
        filtered_df = filtered_df[filtered_df['盈亏比例'] < 0]
    elif filter_option == "未设置成本":
        filtered_df = filtered_df[filtered_df['成本价'].isna() | (filtered_df['成本价'] == 0)]

    # 应用排序
    if sort_option == "涨跌幅↓":
        filtered_df = filtered_df.sort_values('涨跌幅', ascending=False)
    elif sort_option == "涨跌幅↑":
        filtered_df = filtered_df.sort_values('涨跌幅', ascending=True)
    elif sort_option == "盈亏比例↓":
        filtered_df = filtered_df.sort_values('盈亏比例', ascending=False, na_position='last')
    elif sort_option == "盈亏比例↑":
        filtered_df = filtered_df.sort_values('盈亏比例', ascending=True, na_position='last')

    # 显示持仓列表
    st.markdown("### 📋 持仓明细")

    # 使用data_editor显示可编辑表格
    display_df = filtered_df[[
        '股票代码', '股票名称', '当前价', '涨跌额', '涨跌幅',
        '成本价', '持仓数量', '持仓盈亏', '盈亏比例', '买入日期'
    ]].copy()

    # 为每行添加操作按钮
    for idx, row in display_df.iterrows():
        stock_code = row['股票代码']
        stock_name = row['股票名称']
        
        # 创建展开区域用于编辑
        with st.expander(f"📊 {stock_name} ({stock_code}) - 当前价: {row['当前价']:.2f} | 涨跌幅: {row['涨跌幅']:+.2f}%"):
            col1, col2, col3 = st.columns([3, 3, 2])
            
            with col1:
                st.markdown("**实时行情**")
                st.write(f"当前价: **{row['当前价']:.2f}**")
                st.write(f"涨跌额: {row['涨跌额']:+.2f}")
                st.write(f"涨跌幅: {row['涨跌幅']:+.2f}%")
            
            with col2:
                st.markdown("**持仓信息**")
                if pd.notna(row['成本价']) and row['成本价'] > 0:
                    st.write(f"成本价: {row['成本价']:.2f}")
                else:
                    st.write("成本价: 未设置")
                
                if pd.notna(row['持仓数量']) and row['持仓数量'] > 0:
                    st.write(f"持仓数量: {int(row['持仓数量'])}")
                else:
                    st.write("持仓数量: 未设置")
                
                if pd.notna(row['盈亏比例']):
                    profit_color = "🔴" if row['盈亏比例'] > 0 else "🟢"
                    st.write(f"盈亏: {profit_color} {row['盈亏比例']:+.2f}%")
            
            with col3:
                st.markdown("**操作**")
                
                # 查看分时图按钮
                if HAS_INTRADAY_CHART:
                    if st.button("📈 分时图", key=f"chart_{stock_code}_{idx}", use_container_width=True):
                        st.session_state[f'show_chart_{stock_code}'] = not st.session_state.get(f'show_chart_{stock_code}', False)
                
                # 快速编辑按钮
                if st.button("✏️ 编辑", key=f"edit_{stock_code}_{idx}", use_container_width=True):
                    st.session_state[f'editing_{stock_code}'] = True
                
                # 删除按钮
                if st.button("🗑️ 删除", key=f"del_{stock_code}_{idx}", use_container_width=True):
                    remove_stock_from_portfolio(stock_code)
                    st.rerun()
            
            # 显示分时图
            if HAS_INTRADAY_CHART and st.session_state.get(f'show_chart_{stock_code}', False):
                st.markdown("---")
                st.markdown("**📈 实时分时图**")
                display_intraday_chart(stock_code, stock_name)
            
            # 编辑表单
            if st.session_state.get(f'editing_{stock_code}', False):
                st.markdown("---")
                st.markdown("**编辑持仓信息**")
                
                with st.form(f"edit_form_{stock_code}_{idx}"):
                    stock_info = portfolio[stock_code]
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        edit_price = st.number_input(
                            "成本价",
                            value=float(stock_info.get('buy_price', 0)),
                            min_value=0.0,
                            step=0.01,
                            key=f"price_{stock_code}_{idx}"
                        )
                    
                    with col_b:
                        edit_quantity = st.number_input(
                            "持仓数量",
                            value=int(stock_info.get('quantity', 0)),
                            min_value=0,
                            step=100,
                            key=f"qty_{stock_code}_{idx}"
                        )
                    
                    with col_c:
                        edit_date = st.date_input(
                            "买入日期",
                            value=datetime.strptime(stock_info['buy_date'], '%Y-%m-%d').date()
                                  if stock_info.get('buy_date') else datetime.now(),
                            key=f"date_{stock_code}_{idx}"
                        )
                    
                    col_save, col_cancel = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 保存", use_container_width=True):
                            update_stock_info(
                                stock_code,
                                edit_price if edit_price > 0 else None,
                                edit_quantity if edit_quantity > 0 else None,
                                edit_date
                            )
                            st.session_state[f'editing_{stock_code}'] = False
                            st.rerun()
                    
                    with col_cancel:
                        if st.form_submit_button("❌ 取消", use_container_width=True):
                            st.session_state[f'editing_{stock_code}'] = False
                            st.rerun()

    # 自动刷新
    if auto_refresh:
        st.info("⏰ 自动刷新已开启，每30秒更新一次")
        time.sleep(30)
        st.rerun()

    # 显示更新时间
    st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    display_portfolio_monitor()
