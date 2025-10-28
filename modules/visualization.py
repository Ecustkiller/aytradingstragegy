"""
可视化模块 - 负责创建图表和可视化
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_plotly_chart(df, period, show_ma=False, show_boll=False, show_vol=False, 
                        show_macd=False, show_kdj=False, show_rsi=False, data_source="AKShare"):
    """
    创建Plotly交互式K线图和技术指标图表
    
    参数:
        df: 包含股票数据和技术指标的DataFrame
        period: 周期类型 (日线、周线、月线、分钟线等)
        show_ma: 是否显示均线
        show_boll: 是否显示布林带
        show_vol: 是否显示成交量
        show_macd: 是否显示MACD
        show_kdj: 是否显示KDJ
        show_rsi: 是否显示RSI
        data_source: 数据源 ("AKShare" 或 "Ashare")
    
    返回:
        plotly图表对象
    """
    # 检查数据是否为空
    if df is None or df.empty or len(df) < 2:
        print("警告: 传入的数据为空或数据点不足")
        return None
        
    # 确保所有必要的列都存在
    required_cols = ['Open', 'Close', 'High', 'Low', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            print(f"警告: 数据中缺少 {col} 列")
            return None
    
    # 清理数据：移除包含NaN的行
    df = df.copy()
    df = df.dropna(subset=required_cols)
    
    if df.empty or len(df) < 2:
        print("警告: 清理NaN后数据不足")
        return None
    
    # 确保数据类型正确
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 再次清理可能产生的NaN
    df = df.dropna(subset=required_cols)
    
    if df.empty or len(df) < 2:
        print("警告: 数据类型转换后数据不足")
        return None
    
    print(f"✅ 数据验证通过，共 {len(df)} 条数据")
    print(f"   列: {df.columns.tolist()}")
    print(f"   Open范围: {df['Open'].min():.2f} - {df['Open'].max():.2f}")
    print(f"   Close范围: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
    
    # 确定子图行数和高度
    num_rows = 1  # 蜡烛图
    if show_vol:
        num_rows += 1
    if show_macd:
        num_rows += 1
    if show_kdj or show_rsi:
        num_rows += 1
    
    # 根据显示的指标数量调整高度比例 - 增加K线图区域比例
    row_heights = []
    if num_rows == 1:
        row_heights = [1]
    elif num_rows == 2:
        row_heights = [0.8, 0.2]
    elif num_rows == 3:
        row_heights = [0.7, 0.15, 0.15]
    elif num_rows == 4:
        row_heights = [0.65, 0.12, 0.12, 0.11]
    
    # 创建子图
    fig = make_subplots(
        rows=num_rows, 
        cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.01,  # 减少垂直间距
        row_heights=row_heights
    )

    # 准备悬停文本信息
    hover_texts = []
    for i in range(len(df)):
        date_str = df.index[i].strftime('%Y-%m-%d')
        open_val = df['Open'].iloc[i]
        high_val = df['High'].iloc[i]
        low_val = df['Low'].iloc[i]
        close_val = df['Close'].iloc[i]
        volume_val = df['Volume'].iloc[i]
        
        # 根据数据源格式化成交量
        if data_source == "AKShare":
            volume_str = f"{volume_val/10000:.2f}万" if volume_val < 1000000 else f"{volume_val/10000000:.2f}千万"
        else:  # Ashare
            volume_str = f"{volume_val}"
            
        hover_text = f"日期: {date_str}<br>开盘: {open_val:.2f}<br>最高: {high_val:.2f}<br>最低: {low_val:.2f}<br>收盘: {close_val:.2f}<br>成交量: {volume_str}"
        hover_texts.append(hover_text)
    
    # 创建连续索引以消除非交易日空白
    df_continuous = df.copy()
    df_continuous['date_str'] = df.index.strftime('%Y-%m-%d')
    df_continuous['continuous_index'] = range(len(df))
    
    # 添加K线图 - 使用连续索引
    candlestick = go.Candlestick(
        x=df_continuous['continuous_index'],
        open=df_continuous['Open'],
        high=df_continuous['High'],
        low=df_continuous['Low'],
        close=df_continuous['Close'],
        increasing_line_color='red',  # 阳线颜色
        decreasing_line_color='green',  # 阴线颜色
        name='K线',
        hoverinfo='text',
        text=hover_texts
    )
    fig.add_trace(candlestick, row=1, col=1)
    
    # 均线系统 - 只在选择显示均线时添加
    if show_ma:
        ma_colors = ['#FF9900', '#0066CC', '#4B0082', '#66CC99', '#FF00FF', '#FF3333']
        mas = [('MA5', 5), ('MA10', 10), ('MA20', 20), ('MA30', 30), ('MA60', 60)]
        
        for i, (ma_name, _) in enumerate(mas):
            if ma_name in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_continuous['continuous_index'],
                        y=df[ma_name],
                        line=dict(color=ma_colors[i], width=1),
                        name=ma_name
                    ),
                    row=1, col=1
                )
    
    # 布林带 - 只在选择显示布林带时添加
    if show_boll:
        if 'UPPER' in df.columns and 'LOWER' in df.columns and 'MA20' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['UPPER'],
                    line=dict(color='rgba(0, 0, 255, 0.3)', width=1),
                    name='上轨'
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['LOWER'],
                    line=dict(color='rgba(0, 0, 255, 0.3)', width=1),
                    fill='tonexty',
                    fillcolor='rgba(0, 0, 255, 0.1)',
                    name='下轨'
                ),
                row=1, col=1
                )
    
    # 当前行
    current_row = 2
    
    # 成交量图
    if show_vol:
        volume_colors = []
        for i in range(len(df)):
            if i > 0:
                if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                    volume_colors.append('red')
                else:
                    volume_colors.append('green')
            else:
                volume_colors.append('red')
        
        fig.add_trace(
            go.Bar(
                x=df_continuous['continuous_index'],
                y=df['Volume'],
                marker_color=volume_colors,
                name='成交量'
            ),
            row=current_row, col=1
        )
        
        # 添加成交量均线
        if 'VOL_MA5' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['VOL_MA5'],
                    line=dict(color='orange', width=1),
                    name='成交量MA5'
                ),
                row=current_row, col=1
            )
        
        if 'VOL_MA10' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['VOL_MA10'],
                    line=dict(color='blue', width=1),
                    name='成交量MA10'
                ),
                row=current_row, col=1
            )
            
        current_row += 1
    
    # MACD图
    if show_macd and 'MACD' in df.columns and 'MACD_signal' in df.columns and 'MACD_hist' in df.columns:
        # DIF线
        fig.add_trace(
            go.Scatter(
                x=df_continuous['continuous_index'],
                y=df['MACD'],
                line=dict(color='blue', width=1),
                name='DIF'
            ),
            row=current_row, col=1
        )
        
        # DEA线
        fig.add_trace(
            go.Scatter(
                x=df_continuous['continuous_index'],
                y=df['MACD_signal'],
                line=dict(color='orange', width=1),
                name='DEA'
            ),
            row=current_row, col=1
        )
        
        # MACD柱状图
        macd_colors = []
        for macd_hist in df['MACD_hist']:
            if macd_hist > 0:
                macd_colors.append('red')
            else:
                macd_colors.append('green')
                
        fig.add_trace(
            go.Bar(
                x=df_continuous['continuous_index'],
                y=df['MACD_hist'],
                marker_color=macd_colors,
                name='MACD柱'
            ),
            row=current_row, col=1
        )
        
        current_row += 1
    
    # KDJ/RSI图
    if (show_kdj and 'K' in df.columns and 'D' in df.columns and 'J' in df.columns) or (show_rsi and 'RSI' in df.columns):
        # KDJ
        if show_kdj and 'K' in df.columns and 'D' in df.columns and 'J' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['K'],
                    line=dict(color='blue', width=1),
                    name='K值'
                ),
                row=current_row, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['D'],
                    line=dict(color='orange', width=1),
                    name='D值'
                ),
                row=current_row, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['J'],
                    line=dict(color='purple', width=1),
                    name='J值'
                ),
                row=current_row, col=1
            )
            
            # 添加超买超卖水平线
            fig.add_hline(y=80, line_width=1, line_dash="dash", line_color="red", row=current_row)
            fig.add_hline(y=20, line_width=1, line_dash="dash", line_color="green", row=current_row)
            
        # RSI
        if show_rsi and 'RSI' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_continuous['continuous_index'],
                    y=df['RSI'],
                    line=dict(color='purple', width=1.5),
                    name='RSI'
                ),
                row=current_row, col=1
            )
            
            # 添加超买超卖水平线
            fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="red", row=current_row)
            fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="green", row=current_row)
    
    # 设置x轴范围断点，避免非交易时段
    range_breaks = []
    
    # 根据周期设置不同的日期格式和悬停格式
    date_format = '%Y-%m-%d'
    hover_format = '%Y-%m-%d'
    
    if period in ['5分钟', '15分钟', '30分钟', '60分钟']:
        date_format = '%m-%d %H:%M'
        hover_format = '%Y-%m-%d %H:%M'
        
        # 分钟级别数据需要跳过非交易时段
        range_breaks = [
            dict(bounds=["16:00", "09:00"], pattern="hour"),  # 跳过夜间时段
            dict(values=["Saturday", "Sunday"])  # 跳过周末
        ]
    else:
        # 日线级别数据跳过周末和节假日
        try:
            from modules.trading_calendar import is_trading_day
            from datetime import datetime, timedelta
            
            # 获取数据日期范围
            start_date = df.index.min()
            end_date = df.index.max()
            
            # 生成日期范围内的所有非交易日
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            non_trading_days = []
            
            for date in date_range:
                if not is_trading_day(date):
                    non_trading_days.append(date.strftime('%Y-%m-%d'))
            
            # 配置rangebreaks跳过所有非交易日
            if non_trading_days:
                # 使用bounds格式跳过连续的非交易时间段
                range_breaks = []
                
                # 找到连续的非交易日并转换为bounds格式
                
                # 将日期字符串转换为日期对象并排序
                non_trading_dates = sorted([pd.to_datetime(d) for d in non_trading_days])
                
                # 找到连续的日期段
                if non_trading_dates:
                    current_start = non_trading_dates[0]
                    current_end = non_trading_dates[0]
                    
                    for i in range(1, len(non_trading_dates)):
                        if (non_trading_dates[i] - current_end).days == 1:
                            # 连续日期，扩展当前段
                            current_end = non_trading_dates[i]
                        else:
                            # 非连续，添加当前段并开始新段
                            if current_start == current_end:
                                # 单日
                                range_breaks.append(dict(values=[current_start.strftime('%Y-%m-%d')]))
                            else:
                                # 连续多日，使用bounds
                                range_breaks.append(dict(
                                    bounds=[current_start.strftime('%Y-%m-%d'), 
                                           (current_end + timedelta(days=1)).strftime('%Y-%m-%d')]
                                ))
                            current_start = non_trading_dates[i]
                            current_end = non_trading_dates[i]
                    
                    # 添加最后一段
                    if current_start == current_end:
                        range_breaks.append(dict(values=[current_start.strftime('%Y-%m-%d')]))
                    else:
                        range_breaks.append(dict(
                            bounds=[current_start.strftime('%Y-%m-%d'), 
                                   (current_end + timedelta(days=1)).strftime('%Y-%m-%d')]
                        ))
                
                print(f"   📊 跳过的非交易日: {len(non_trading_days)} 个")
                print(f"   📊 生成的rangebreaks段数: {len(range_breaks)} 个")
                june_non_trading = [d for d in non_trading_days if '2024-06' in d]
                if june_non_trading:
                    print(f"   📅 6月份跳过: {june_non_trading}")
            else:
                range_breaks = [dict(values=["Saturday", "Sunday"])]
        except Exception as e:
            print(f"警告: 无法加载交易日历，使用默认周末跳过: {e}")
            range_breaks = [dict(values=["Saturday", "Sunday"])]
    
    # 显示逻辑优化 - 确保显示最新数据
    title_prefix = "AKShare" if data_source == "AKShare" else "Ashare"
    title_suffix = f" (共{len(df)}根K线)"
    
    # 🔧 修复：不再限制显示范围，让用户看到完整的数据
    # 特别是对于60分钟等重要周期，用户需要看到最新的数据
    print(f"📊 图表显示信息:")
    print(f"   数据源: {data_source}")
    print(f"   周期: {period}")
    print(f"   数据条数: {len(df)}")
    print(f"   显示范围: {df.index[0]} 到 {df.index[-1]}")
    
    # 只对过于密集的短周期数据进行适当限制
    if period == '5分钟' and len(df) > 100:
        start_idx = max(0, len(df) - 100)
        title_suffix = f" (显示最近100根K线，共{len(df)}根)"
        range_start = df.index[start_idx]
        fig.update_xaxes(range=[range_start, df.index[-1]])
        print(f"   ⚠️  5分钟数据过多，只显示最近100根")
    else:
        # 其他情况都显示全部数据，确保用户能看到最新的K线
        print(f"   ✅ 显示全部数据，包含最新K线")
    
    # 更新布局设置 - 确保显示实际的数据日期范围
    actual_start_date = df.index[0]
    actual_end_date = df.index[-1]
    
    # 格式化日期显示
    if period in ['5分钟', '15分钟', '30分钟', '60分钟']:
        start_str = actual_start_date.strftime('%Y-%m-%d %H:%M')
        end_str = actual_end_date.strftime('%Y-%m-%d %H:%M')
        title_text = f"{period}K线图 - {start_str} 至 {end_str}"
        title_text += f" (共{len(df)}根K线)"
    else:
        start_str = actual_start_date.strftime('%Y-%m-%d')
        end_str = actual_end_date.strftime('%Y-%m-%d')
        title_text = f"{period}K线图 - {start_str} 至 {end_str}"
        title_text += f" (共{len(df)}根K线)"
    
    # 添加数据源信息
    title_text += f" [{data_source}数据源]"
    
    fig.update_layout(
        title={
            'text': title_text,
            'y':0.99,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 14}  # 减小标题字体
        },
        margin=dict(l=30, r=30, t=50, b=20),  # 进一步减小边距
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=9)  # 减小图例字体
        ),
        height=750,  # 增加图表总高度
        hovermode='x unified',  # 统一X轴上的悬停效果
        hoverlabel=dict(
            bgcolor="white",
            font_size=11,
            font_family="Arial"
        ),
        # 创建签名
        annotations=[
            dict(
                text="created by ayuan",
                xref="paper", yref="paper",
                x=0.99, y=0.01,
                showarrow=False,
                font=dict(color="rgba(150,150,150,0.3)", size=10)  # 减小签名字体和透明度
            )
        ],
        dragmode='zoom',        # 设置默认拖动模式为缩放
        xaxis=dict(
            showticklabels=True,   # 显示X轴标签，方便用户查看日期
            rangeslider=dict(visible=False),  # 禁用范围滑块
            autorange=True,  # 自动调整范围以显示所有数据
            # 自定义X轴标签显示日期
            tickmode='array',
            tickvals=list(range(0, len(df_continuous), max(1, len(df_continuous)//10))),
            ticktext=[df_continuous.iloc[i]['date_str'] for i in range(0, len(df_continuous), max(1, len(df_continuous)//10))],
            tickangle=45
        )
    )
    
    # 为每个子图添加网格和十字准星
    for i in range(1, num_rows+1):
        fig.update_xaxes(
            showgrid=True,
            gridwidth=0.5,  # 减小网格线宽度
            gridcolor='rgba(211,211,211,0.3)',  # 使网格线更透明
            zeroline=False,
            row=i, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,  # 减小网格线宽度
            gridcolor='rgba(211,211,211,0.3)',  # 使网格线更透明
            zeroline=False,
            row=i, col=1
        )
    
    # 添加十字准星和rangebreaks配置
    xaxis_config = dict(
        showspikes=True,
        spikemode='across',
        spikesnap='cursor',
        spikecolor='rgba(0,0,0,0.5)',  # 使十字线半透明
        spikethickness=0.5,
        spikedash='solid'
    )
    
    # 应用rangebreaks配置以跳过非交易时间
    if range_breaks:
        xaxis_config['rangebreaks'] = range_breaks
        print(f"   ✅ 应用rangebreaks配置，跳过 {len(range_breaks)} 个时间段")
    else:
        print(f"   ❌ 未应用rangebreaks配置，可能仍有周末空白")
    
    fig.update_layout(
        xaxis=xaxis_config,
        yaxis=dict(
            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikecolor='rgba(0,0,0,0.5)',  # 使十字线半透明
            spikethickness=0.5,
            spikedash='solid'
        )
    )
    
    return fig

def create_market_status_panel(market_status):
    """
    创建市场状态面板的HTML内容
    
    参数:
        market_status: 包含市场状态信息的字典
    
    返回:
        HTML格式的市场状态面板内容
    """
    if not market_status:
        return ""
    
    # 提取状态信息
    ma = market_status.get("ma", {})
    macd = market_status.get("macd", {})
    rsi = market_status.get("rsi", {})
    kdj = market_status.get("kdj", {})
    volume = market_status.get("volume", {})
    price = market_status.get("price", {})
    
    # 设置颜色
    ma_color = "green" if ma.get("status") == "看涨" else "red" if ma.get("status") == "看跌" else "gray"
    macd_color = "green" if macd.get("hist", 0) > 0 else "red"
    rsi_color = "red" if rsi.get("value", 0) > 70 else "green" if rsi.get("value", 0) < 30 else "gray"
    kdj_status = kdj.get("status", "")
    kdj_color = "red" if kdj_status == "超买" or kdj_status == "死叉" else "green" if kdj_status == "超卖" or kdj_status == "金叉" else "gray"
    vol_color = "red" if volume.get("status") == "放量" else "green" if volume.get("status") == "缩量" else "gray"
    price_color = "red" if price.get("status") == "高位" else "green" if price.get("status") == "低位" else "gray"
    
    # 格式化成交量
    vol_value = volume.get("value", 0)
    vol_display = f"{vol_value/10000:.2f}万" if vol_value < 1000000 else f"{vol_value/10000000:.2f}千万"
    
    # 构建HTML内容
    html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between;">
        <!-- 均线状态 -->
        <div style="flex: 1; min-width: 150px; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
            <h4 style="margin:0; text-align:center;">均线状态</h4>
            <p style="color:{ma_color}; font-size:18px; text-align:center; margin:5px 0;">{ma.get("status", "")}</p>
            <p style="text-align:center; margin:0; font-size:12px;">
                MA5: {ma.get("ma5", 0):.2f}<br>
                MA10: {ma.get("ma10", 0):.2f}<br>
                MA20: {ma.get("ma20", 0):.2f}
            </p>
        </div>
        
        <!-- MACD状态 -->
        <div style="flex: 1; min-width: 150px; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
            <h4 style="margin:0; text-align:center;">MACD状态</h4>
            <p style="color:{macd_color}; font-size:18px; text-align:center; margin:5px 0;">{macd.get("status", "")}</p>
            <p style="text-align:center; margin:0; font-size:12px;">
                DIF: {macd.get("dif", 0):.3f}<br>
                DEA: {macd.get("dea", 0):.3f}<br>
                HIST: {macd.get("hist", 0):.3f}
            </p>
        </div>
        
        <!-- RSI状态 -->
        <div style="flex: 1; min-width: 150px; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
            <h4 style="margin:0; text-align:center;">RSI状态</h4>
            <p style="color:{rsi_color}; font-size:18px; text-align:center; margin:5px 0;">{rsi.get("status", "")}</p>
            <p style="text-align:center; margin:0; font-size:12px;">
                RSI: {rsi.get("value", 0):.2f}<br>
                变化: {rsi.get("change", 0):.2f}
            </p>
        </div>
        
        <!-- KDJ状态 -->
        <div style="flex: 1; min-width: 150px; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
            <h4 style="margin:0; text-align:center;">KDJ状态</h4>
            <p style="color:{kdj_color}; font-size:18px; text-align:center; margin:5px 0;">{kdj.get("status", "")}</p>
            <p style="text-align:center; margin:0; font-size:12px;">
                K: {kdj.get("k", 0):.2f}<br>
                D: {kdj.get("d", 0):.2f}<br>
                J: {kdj.get("j", 0):.2f}
            </p>
        </div>
        
        <!-- 成交量状态 -->
        <div style="flex: 1; min-width: 150px; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
            <h4 style="margin:0; text-align:center;">成交量状态</h4>
            <p style="color:{vol_color}; font-size:18px; text-align:center; margin:5px 0;">{volume.get("status", "")}</p>
            <p style="text-align:center; margin:0; font-size:12px;">
                成交量: {vol_display}<br>
                变化: {volume.get("change", 0):.2f}%
            </p>
        </div>
        
        <!-- 价格位置 -->
        <div style="flex: 1; min-width: 150px; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
            <h4 style="margin:0; text-align:center;">价格位置</h4>
            <p style="color:{price_color}; font-size:18px; text-align:center; margin:5px 0;">{price.get("status", "")}</p>
            <p style="text-align:center; margin:0; font-size:12px;">
                位置: {price.get("position", 0):.2f}%<br>
                价格: {price.get("value", 0):.2f}<br>
                涨跌: {price.get("change", 0):.2f}%
            </p>
        </div>
    </div>
    """
    
    return html