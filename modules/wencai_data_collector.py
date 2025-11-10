"""
问财数据采集模块
使用 pywencai 接口批量采集历史股票数据
"""
import streamlit as st
import time
import os
import random
import shutil
from datetime import datetime, timedelta
import pandas as pd
import re
import base64
from typing import List, Dict, Optional

# 尝试导入依赖
try:
    import pywencai
    HAS_PYWENCAI = True
    PYWENCAI_ERROR = None
except Exception as e:
    HAS_PYWENCAI = False
    PYWENCAI_ERROR = str(e)

try:
    from chinese_calendar import is_holiday
    HAS_CHINESE_CALENDAR = True
except ImportError:
    HAS_CHINESE_CALENDAR = False


# 核心股票查询类
class StockQueryTemplate:
    _DATE_VARS = {
        'current_date': ('%Y%m%d', 0),
        'pre1': ('%Y%m%d', -1),
        'pre2': ('%Y%m%d', -2),
        'pre3': ('%Y%m%d', -3),
        'next1': ('%Y%m%d', 1),
        'next2': ('%Y%m%d', 2),
        'next3': ('%Y%m%d', 3),
        'lookback3_date': ('%Y%m%d', -3),
        'week_start': ('%Y%m%d', 'week_start'),
        'month_start': ('%Y%m%d', 'month_start')
    }

    def __init__(self, start_date: str, end_date: str):
        self.trading_dates = self._generate_trading_calendar(start_date, end_date)
        self.query_dates = self._generate_query_calendar(start_date, end_date)

    def _generate_trading_calendar(self, start: str, end: str) -> List[str]:
        start_date = datetime.strptime(start, "%Y%m%d")
        end_date = datetime.strptime(end, "%Y%m%d")
        extended_start = start_date - timedelta(days=30)
        dates = pd.date_range(extended_start, end_date)
        
        if HAS_CHINESE_CALENDAR:
            # 使用 chinese_calendar 库判断节假日
            return [
                d.strftime("%Y%m%d") for d in dates
                if not is_holiday(d) and d.weekday() < 5
            ]
        else:
            # 简单判断：只排除周末
            return [
                d.strftime("%Y%m%d") for d in dates
                if d.weekday() < 5
            ]

    def _generate_query_calendar(self, start: str, end: str) -> List[str]:
        start_date = datetime.strptime(start, "%Y%m%d")
        end_date = datetime.strptime(end, "%Y%m%d")
        extended_start = start_date - timedelta(days=0)
        dates = pd.date_range(extended_start, end_date)
        
        if HAS_CHINESE_CALENDAR:
            return [
                d.strftime("%Y%m%d") for d in dates
                if not is_holiday(d) and d.weekday() < 5
            ]
        else:
            return [
                d.strftime("%Y%m%d") for d in dates
                if d.weekday() < 5
            ]

    def _get_relative_date(self, base_date: str, offset: int) -> Optional[str]:
        try:
            idx = self.trading_dates.index(base_date)
            new_idx = idx + offset
            if new_idx < 0 or new_idx >= len(self.trading_dates):
                return None
            return self.trading_dates[new_idx]
        except ValueError:
            return None

    def resolve_query(self, query_template: str, target_date: str) -> str:
        date_vars = set(re.findall(r'\$\{(\w+)\}', query_template))
        replacements = {}
        for var in date_vars:
            if var in self._DATE_VARS:
                fmt, offset = self._DATE_VARS[var]
                resolved = None
                if isinstance(offset, str):
                    if offset == 'week_start':
                        base_date = datetime.strptime(target_date, "%Y%m%d")
                        resolved = (base_date - timedelta(days=base_date.weekday())).strftime(fmt)
                    elif offset == 'month_start':
                        resolved = target_date[:6] + '01'
                else:
                    resolved = self._get_relative_date(target_date, offset)
                if resolved:
                    replacements[f'${{{var}}}'] = resolved
        query = query_template
        for k, v in replacements.items():
            query = query.replace(k, v)
        return query


# 数据处理类（添加进度反馈功能）
class SafeStockProcessor:
    def __init__(self, config: Dict, log_callback=None, progress_callback=None):
        self.config = self._validate_config(config)
        self.temp_folder = self.config['temp_folder']
        self.query_engine = StockQueryTemplate(
            self.config['start_date'],
            self.config['end_date']
        )
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self._init_folders()

    def _validate_config(self, config: Dict) -> Dict:
        required_keys = ['query', 'start_date', 'end_date', 'output_file']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"缺少必要参数: {key}")
        if config.get('use_pro', False) and 'pro_cookie' not in config:
            raise ValueError("专业版必须提供pro_cookie")
        return config

    def _init_folders(self):
        os.makedirs(self.temp_folder, exist_ok=True)
        os.makedirs(self.config.get('backup_folder', 'backups'), exist_ok=True)

    def _build_request_params(self, date: str) -> Dict:
        params = {
            'query': self.query_engine.resolve_query(self.config['query'], date),
            'loop': True,
            'query_type': self.config['query_type']
        }
        if self.config.get('use_pro', False):
            params.update({
                'pro': True,
                'cookie': self.config['pro_cookie']
            })
        if self.config.get('enable_proxy', False):
            params['request_params'] = {
                'proxies': self.config['proxies'],
                'verify': False,
                'timeout': 30
            }
        return params

    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [
            re.sub(r'\[\d{8}\]|\d{8} \d{2}:\d{2}:\d{2}', '', col).strip()
            for col in df.columns
        ]
        return df

    def collect_data(self):
        if self.log_callback:
            self.log_callback("🚀 开始采集数据...")
        dates = self.query_engine.query_dates
        total_dates = len(dates)

        # 初始化进度
        if self.progress_callback:
            self.progress_callback(0, f"准备采集 {total_dates} 个交易日数据")

        for idx, date in enumerate(dates):
            # 更新进度
            progress = (idx + 1) / total_dates
            if self.progress_callback:
                self.progress_callback(progress, f"处理 {date} ({idx + 1}/{total_dates})")

            if self.log_callback:
                self.log_callback(f"▷ 处理 {date} ({idx + 1}/{total_dates})")

            try:
                request_params = self._build_request_params(date)
                data = pywencai.get(**request_params)
                if not data.empty:
                    clean_data = self._clean_columns(data)
                    clean_data.insert(0, '数据日期', date)
                    save_path = os.path.join(self.temp_folder, f"{date}.xlsx")
                    clean_data.to_excel(save_path, index=False)
                else:
                    if self.log_callback:
                        self.log_callback(f"⏩ {date} 无数据，跳过")
                time.sleep(max(1, random.uniform(*self.config.get('request_interval', (3, 5)))))
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"\n× 采集失败 {date}: {str(e)}")

        # 完成进度
        if self.progress_callback:
            self.progress_callback(1.0, "✅ 数据采集完成")

        if self.log_callback:
            self.log_callback("\n✅ 数据采集完成")

    def merge_and_clean(self):
        if self.log_callback:
            self.log_callback("🔄 开始合并数据...")
        all_files = [
            os.path.join(self.temp_folder, f)
            for f in os.listdir(self.temp_folder)
            if f.endswith('.xlsx')
        ]
        final_df = pd.DataFrame()
        for file in all_files:
            try:
                df = pd.read_excel(file)
                final_df = pd.concat([final_df, df], ignore_index=True)
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"× 合并失败 {file}: {str(e)}")
        if not final_df.empty:
            if self.config['query_type'] == 'zhishu':
                final_df = final_df.drop_duplicates(
                    subset=['指数代码', '数据日期'],
                    keep='last'
                ).sort_values('数据日期')
                final_df.to_excel(self.config['output_file'], index=False)
            if self.config['query_type'] == 'stock':
                final_df = final_df.drop_duplicates(
                    subset=['股票代码', '数据日期'],
                    keep='last'
                ).sort_values('数据日期')
                final_df.to_excel(self.config['output_file'], index=False)
            if self.log_callback:
                self.log_callback(f"✅ 结果已保存至 {self.config['output_file']}")
            return self.config['output_file']
        else:
            if self.log_callback:
                self.log_callback("⚠️ 无有效数据可保存")
            return None


# Streamlit应用主界面
def display_wencai_collector():
    """显示问财数据采集界面"""
    
    # 检查依赖
    if not HAS_PYWENCAI:
        st.error("❌ pywencai 模块不可用")
        st.info("💡 此功能需要 pywencai 库支持。")
        st.code("pip install pywencai", language="bash")
        if PYWENCAI_ERROR:
            with st.expander("查看错误详情"):
                st.code(PYWENCAI_ERROR)
        return
    
    if not HAS_CHINESE_CALENDAR:
        st.warning("⚠️ 未安装 chinese_calendar 库，将使用简化的交易日判断（只排除周末）")
        with st.expander("安装 chinese_calendar 以获得更准确的交易日判断"):
            st.code("pip install chinesecalendar", language="bash")

    st.title("📈 问财数据采集系统")
    st.caption("使用问财接口批量采集历史股票数据")

    # 初始化会话状态
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'output_file' not in st.session_state:
        st.session_state.output_file = None
    if 'progress_value' not in st.session_state:
        st.session_state.progress_value = 0
    if 'progress_text' not in st.session_state:
        st.session_state.progress_text = "准备开始"

    # 日志回调函数
    def log_callback(message):
        st.session_state.log_messages.append(message)
        if len(st.session_state.log_messages) > 100:  # 限制日志长度
            st.session_state.log_messages.pop(0)

    # 进度回调函数
    def progress_callback(progress, text):
        st.session_state.progress_value = progress
        st.session_state.progress_text = text

    # ========== 主界面 - 参数配置区 ==========
    st.header("⚙️ 参数配置")
    
    # 智能日期提示
    def get_last_trading_date():
        """获取最近的交易日期"""
        now = datetime.now()
        current_hour = now.hour
        
        # 如果是交易日的15:00之后，当天数据可用
        # 否则使用前一个交易日
        if current_hour < 15:
            # 使用前一天
            last_date = now - timedelta(days=1)
        else:
            last_date = now
        
        # 跳过周末
        while last_date.weekday() >= 5:  # 5=周六, 6=周日
            last_date = last_date - timedelta(days=1)
        
        return last_date.date()
    
    last_trading_date = get_last_trading_date()
    
    # 显示提示
    now_hour = datetime.now().hour
    if now_hour < 9 or now_hour >= 15:
        st.info(f"💡 当前非交易时段，建议使用最近交易日数据。最近交易日: **{last_trading_date.strftime('%Y-%m-%d')}**")
    
    # 第一行：日期选择和查询类型
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        # 默认使用最近交易日前30天
        default_start = last_trading_date - timedelta(days=30)
        start_date = st.date_input("📅 开始日期", value=default_start)
    with col2:
        # 默认使用最近交易日
        end_date = st.date_input("📅 结束日期", value=last_trading_date, max_value=last_trading_date)
    with col3:
        query_type = st.selectbox("查询类型", ["stock", "zhishu"], index=0)
    
    # 日期有效性检查
    if end_date > last_trading_date:
        st.warning(f"⚠️ 结束日期 {end_date} 超过最近交易日 {last_trading_date}，数据可能不完整或为空！")
    
    # 查询模式选择
    st.subheader("🔍 查询设置")
    query_mode = st.radio(
        "查询模式",
        ["简单模式（推荐）", "高级模式（使用日期变量）"],
        horizontal=True,
        help="简单模式：直接输入查询条件，系统自动处理日期\n高级模式：可以使用${current_date}等日期变量"
    )
    
    if query_mode == "简单模式（推荐）":
        # 简单模式：预设模板
        simple_query_options = {
            "涨停股票分析": "涨停,原因,概念",
            "指数成分股": "上证50成分股",
            "行业龙头": "行业龙头",
            "新高突破": "创60日新高,成交量>1亿",
            "强势股": "5日涨幅>10%,换手率>5%",
            "自定义查询": ""
        }
        selected_template = st.selectbox("🎯 选择查询模板", list(simple_query_options.keys()))
        
        if selected_template == "自定义查询":
            user_query = st.text_area(
                "✏️ 输入查询条件",
                value="",
                height=80,
                placeholder="例如：市值>100亿,5日涨幅>10%,换手率>5%\n或：人工智能概念,MACD金叉\n或：连续3天涨停",
                help="直接输入查询条件，无需添加日期。系统会自动为日期范围内的每个交易日查询。"
            )
        else:
            user_query = st.text_area(
                "✏️ 查询条件（可修改）",
                value=simple_query_options[selected_template],
                height=80,
                help="直接输入查询条件，无需添加日期。系统会自动为日期范围内的每个交易日查询。"
            )
        
        # 自动添加日期变量
        custom_query = f"${{current_date}}{user_query}" if user_query else "${current_date}涨停"
        
        st.info(f"💡 将查询日期范围内每个交易日的数据：**{user_query if user_query else '涨停'}**")
        
    else:
        # 高级模式：使用日期变量
        advanced_query_options = {
            "涨停股票分析": "${current_date}涨停,${current_date}原因,概念",
            "指数成分股": "${current_date}上证50成分股",
            "行业龙头": "${current_date}行业龙头",
            "新高突破": "${current_date}创60日新高,成交量>1亿",
            "强势股": "${current_date}5日涨幅>10%,换手率>5%"
        }
        selected_query = st.selectbox("🎯 查询模板", list(advanced_query_options.keys()))
        
        custom_query = st.text_area(
            "✏️ 高级查询模板",
            value=advanced_query_options[selected_query],
            height=80,
            help="可以使用日期变量：${current_date}, ${pre1}, ${pre2}等"
        )
        
        # 日期变量说明
        with st.expander("📖 日期变量说明"):
            st.markdown("""
            - **`${current_date}`**: 当前采集的交易日（循环遍历开始日期到结束日期）
            - **`${pre1}`**: 前1个交易日
            - **`${pre2}`**: 前2个交易日  
            - **`${pre3}`**: 前3个交易日
            
            **示例**：
            - 采集范围：2024-10-25 至 2024-10-28
            - 查询：`${current_date}涨停`
            - 实际会查询4次：10-25涨停, 10-26涨停, 10-27涨停, 10-28涨停
            """)

    
    # 高级选项
    with st.expander("🔧 高级选项"):
        col1, col2 = st.columns(2)
        with col1:
            request_interval = st.slider("请求间隔(秒)", 1.0, 10.0, (3.0, 5.0), 0.5)
            keep_temp_files = st.checkbox("保留临时文件", False)
        with col2:
            use_pro = st.checkbox("使用专业版", False)
            pro_cookie = st.text_input("专业版Cookie", type="password", disabled=not use_pro)
        
        enable_proxy = st.checkbox("启用代理", False)
        if enable_proxy:
            col1, col2 = st.columns(2)
            with col1:
                http_proxy = st.text_input("HTTP代理")
            with col2:
                https_proxy = st.text_input("HTTPS代理")
    
    st.divider()
    
    # ========== 主区域 - 控制和日志 ==========
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("🔄 数据采集控制")
        
        # 显示采集范围提示
        days_diff = (end_date - start_date).days + 1
        estimated_trading_days = int(days_diff * 5 / 7)  # 粗略估算
        st.info(f"📊 日期范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}\n\n⏱️ 约 {estimated_trading_days} 个交易日，预计耗时 {estimated_trading_days * 3}~{estimated_trading_days * 5} 秒")
        
        # 操作按钮
        if st.button("开始采集", type="primary", disabled=st.session_state.processing):
            st.session_state.processing = True
            st.session_state.log_messages = []
            log_callback("🚀 开始采集任务...")

            # 构建配置
            config = {
                'query': custom_query,
                'query_type': query_type,
                'start_date': start_date.strftime("%Y%m%d"),
                'end_date': end_date.strftime("%Y%m%d"),
                'output_file': f"stock_data_{int(time.time())}.xlsx",
                'temp_folder': f"temp_data_{int(time.time())}",
                'backup_folder': 'backups',
                'keep_temp_files': keep_temp_files,
                'request_interval': request_interval,
                'use_pro': use_pro,
                'pro_cookie': pro_cookie if use_pro else None,
                'enable_proxy': enable_proxy
            }

            if enable_proxy:
                config['proxies'] = {
                    'http': http_proxy,
                    'https': https_proxy
                }

            try:
                # 进度条容器
                progress_container = st.container()
                with progress_container:
                    # 显示进度条和状态文本
                    progress_bar = st.progress(st.session_state.progress_value)
                    status_text = st.empty()
                    status_text.info(st.session_state.progress_text)

                # 定义更新函数
                def update_progress(progress, text):
                    st.session_state.progress_value = progress
                    st.session_state.progress_text = text
                    progress_bar.progress(progress)
                    status_text.info(text)

                # 执行采集任务
                with st.spinner("数据采集中，请耐心等待..."):
                    processor = SafeStockProcessor(config, log_callback=log_callback, progress_callback=update_progress)
                    processor.collect_data()
                    output_file = processor.merge_and_clean()

                if output_file and os.path.exists(output_file):
                    st.session_state.output_file = output_file
                    log_callback("✅ 数据处理完成,可下载结果")
                else:
                    log_callback("⚠️ 未生成有效输出文件")

            except Exception as e:
                log_callback(f"‼️ 程序异常: {str(e)}")
            finally:
                st.session_state.processing = False
                # 清除进度状态
                st.session_state.progress_value = 0
                st.session_state.progress_text = "任务完成"
                # 刷新页面
                st.rerun()

        if st.button("停止采集", disabled=not st.session_state.processing):
            st.session_state.processing = False
            log_callback("⏹️ 用户手动停止采集任务")

    with col2:
        st.header("📋 操作日志")
        log_container = st.container(height=300, border=True)

        with log_container:
            for msg in st.session_state.log_messages:
                if msg.startswith("▷"):
                    st.info(msg)
                elif msg.startswith("×") or msg.startswith("‼️"):
                    st.error(msg)
                elif msg.startswith("⏩"):
                    st.warning(msg)
                elif msg.startswith("🔄") or msg.startswith("🚀"):
                    st.success(msg)
                else:
                    st.text(msg)

    # 结果下载区
    if st.session_state.output_file:
        st.divider()
        st.header("📥 结果下载")

        if os.path.exists(st.session_state.output_file):
            file_size = os.path.getsize(st.session_state.output_file) / (1024 * 1024)

            with open(st.session_state.output_file, "rb") as f:
                bytes_data = f.read()
                st.download_button(
                    label=f"📥 下载结果文件 ({file_size:.2f}MB)",
                    data=bytes_data,
                    file_name=os.path.basename(st.session_state.output_file),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # 预览数据
            try:
                preview_df = pd.read_excel(st.session_state.output_file)
                
                # 显示数据统计信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 总记录数", len(preview_df))
                with col2:
                    st.metric("📋 字段数", len(preview_df.columns))
                with col3:
                    if '数据日期' in preview_df.columns:
                        unique_dates = preview_df['数据日期'].nunique()
                        st.metric("📅 日期数", unique_dates)
                    else:
                        st.metric("📂 文件大小", f"{file_size:.2f}MB")
                
                # 显示完整数据表格（可滚动）
                st.subheader("📄 数据预览")
                st.dataframe(
                    preview_df, 
                    height=600,  # 增加高度
                    width="stretch"  # 使用容器全宽
                )
            except Exception as e:
                st.error(f"预览失败: {str(e)}")
        else:
            st.warning("输出文件不存在")

