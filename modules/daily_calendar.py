"""
每日宜忌功能模块
基于农历显示每日宜忌事项（娱乐性质）
"""
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 尝试导入lunar库
try:
    from lunar_python import Lunar
    HAS_LUNAR = True
    LUNAR_ERROR = None
except ImportError as e:
    HAS_LUNAR = False
    LUNAR_ERROR = str(e)

# CSS样式
CALENDAR_STYLE = """
<style>
    .day-box {
        border: 1px solid #ddd;
        padding: 10px;
        min-height: 120px;
        border-radius: 5px;
        margin: 2px;
        background-color: white;
    }
    
    .today {
        background-color: #e8f4ff;
        border: 2px solid #2196F3;
    }
    
    .yi-tag {
        color: #4CAF50;
        font-size: 0.9em;
        margin-top: 5px;
    }
    
    .ji-tag {
        color: #f44336;
        font-size: 0.9em;
        margin-top: 5px;
    }
    
    .lunar-date {
        color: #666;
        font-size: 0.85em;
    }
</style>
"""

def get_lunar_info(date):
    """获取农历信息"""
    if not HAS_LUNAR:
        return None
    
    try:
        # 确保传入的是datetime对象
        if not isinstance(date, datetime):
            # 如果是date对象，转换为datetime
            date = datetime.combine(date, datetime.min.time())
        
        lunar = Lunar.fromDate(date)
        return {
            'lunar_date': f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            'year_gan_zhi': lunar.getYearInGanZhiExact(),
            'month_gan_zhi': lunar.getMonthInGanZhiExact(),
            'day_gan_zhi': lunar.getDayInGanZhi(),
            'yi': lunar.getDayYi(),
            'ji': lunar.getDayJi(),
            'chong': lunar.getDayChongDesc(),
            'sha': lunar.getDaySha()
        }
    except Exception as e:
        st.warning(f"⚠️ 获取农历信息失败: {e}")
        st.info("💡 提示：lunar-python 库可能需要重新安装")
        import traceback
        st.code(traceback.format_exc())
        return None

def generate_calendar_view(year, month):
    """生成月历视图"""
    cal = calendar.Calendar()
    month_days = cal.monthdays2calendar(year, month)
    
    today = datetime.now().date()
    
    # 日历头
    st.markdown(f"### {year}年{month}月")
    
    # 星期标题
    days = ["一", "二", "三", "四", "五", "六", "日"]
    cols = st.columns(7)
    for col, day in zip(cols, days):
        col.markdown(f"**{day}**", unsafe_allow_html=True)
    
    # 生成每日数据
    for week in month_days:
        cols = st.columns(7)
        for col, (day, weekday) in zip(cols, week):
            if day == 0:
                col.write("")
                continue
            
            date = datetime(year, month, day).date()
            is_today = date == today
            
            # 获取农历信息
            lunar_info = get_lunar_info(date)
            
            # 构建显示内容
            day_class = "today" if is_today else ""
            
            day_content = f"""
            <div class="day-box {day_class}">
                <div style="font-weight: bold; font-size: 1.1em;">{day}日</div>
            """
            
            if lunar_info:
                day_content += f"""
                <div class="lunar-date">{lunar_info['lunar_date']}</div>
                <div class="yi-tag">✓ {', '.join(lunar_info['yi'][:2]) if lunar_info['yi'] else '无'}</div>
                <div class="ji-tag">✗ {', '.join(lunar_info['ji'][:2]) if lunar_info['ji'] else '无'}</div>
                """
            
            day_content += "</div>"
            col.markdown(day_content, unsafe_allow_html=True)

def display_daily_detail(date):
    """显示指定日期的详细信息"""
    lunar_info = get_lunar_info(date)
    
    if not lunar_info:
        st.warning("⚠️ 无法获取农历信息")
        return
    
    st.markdown(f"### 📅 {date.strftime('%Y年%m月%d日')} 详情")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📆 日期信息")
        st.markdown(f"""
        - **农历**: {lunar_info['lunar_date']}
        - **年干支**: {lunar_info['year_gan_zhi']}
        - **月干支**: {lunar_info['month_gan_zhi']}
        - **日干支**: {lunar_info['day_gan_zhi']}
        """)
        
        if lunar_info.get('chong'):
            st.markdown(f"- **冲**: {lunar_info['chong']}")
        if lunar_info.get('sha'):
            st.markdown(f"- **煞**: {lunar_info['sha']}")
    
    with col2:
        st.markdown("#### ✅ 宜")
        if lunar_info['yi']:
            for item in lunar_info['yi']:
                st.markdown(f"- {item}")
        else:
            st.markdown("- 无特别事项")
        
        st.markdown("#### ❌ 忌")
        if lunar_info['ji']:
            for item in lunar_info['ji']:
                st.markdown(f"- {item}")
        else:
            st.markdown("- 无特别事项")
    
    # 趣味解读（娱乐性质）
    st.markdown("---")
    with st.expander("💡 今日股市宜忌建议（仅供娱乐）"):
        yi_items = lunar_info['yi'] if lunar_info['yi'] else []
        ji_items = lunar_info['ji'] if lunar_info['ji'] else []
        
        stock_yi = []
        stock_ji = []
        
        # 简单的映射规则（娱乐性质）
        yi_mapping = {
            '嫁娶': '建仓',
            '纳财': '买入',
            '开市': '交易',
            '交易': '买卖',
            '求财': '投资',
            '纳采': '选股',
            '移徙': '换仓',
            '出行': '看盘'
        }
        
        ji_mapping = {
            '破土': '重仓',
            '动土': '激进',
            '安葬': '抄底',
            '修造': '调仓',
            '出行': '追高',
            '嫁娶': '全仓'
        }
        
        for item in yi_items:
            for key, value in yi_mapping.items():
                if key in item:
                    stock_yi.append(value)
                    break
        
        for item in ji_items:
            for key, value in ji_mapping.items():
                if key in item:
                    stock_ji.append(value)
                    break
        
        if stock_yi:
            st.success(f"✅ **今日宜**: {', '.join(stock_yi)}")
        else:
            st.info("✅ **今日宜**: 观望")
        
        if stock_ji:
            st.error(f"❌ **今日忌**: {', '.join(stock_ji)}")
        else:
            st.info("❌ **今日忌**: 无特别禁忌")
        
        st.caption("⚠️ 以上内容仅供娱乐，不构成任何投资建议！")

def display_daily_calendar():
    """显示每日宜忌主界面"""
    st.title("📅 每日宜忌")
    
    st.markdown("""
    ### 功能说明
    基于传统农历黄历，提供每日宜忌事项查询。
    
    **⚠️ 特别声明**：
    - 本功能仅供**娱乐参考**
    - 不构成任何投资建议
    - 投资决策请基于基本面和技术分析
    """)
    
    st.markdown(CALENDAR_STYLE, unsafe_allow_html=True)
    
    # 检查依赖
    if not HAS_LUNAR:
        st.error("❌ lunar-python库未安装")
        st.info(f"错误详情: {LUNAR_ERROR}")
        st.code("pip install lunar-python", language="bash")
        return
    
    st.markdown("---")
    
    # 选择查看模式
    view_mode = st.radio(
        "查看模式",
        ["📋 今日详情", "📆 月历视图"],
        horizontal=True
    )
    
    if view_mode == "📋 今日详情":
        # 日期选择
        today = datetime.now().date()
        selected_date = st.date_input(
            "选择日期",
            value=today,
            help="选择要查看的日期"
        )
        
        st.markdown("---")
        display_daily_detail(selected_date)
        
    else:
        # 月份选择
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.number_input(
                "年份",
                min_value=2000,
                max_value=2100,
                value=datetime.now().year,
                step=1
            )
        with col2:
            selected_month = st.number_input(
                "月份",
                min_value=1,
                max_value=12,
                value=datetime.now().month,
                step=1
            )
        
        st.markdown("---")
        generate_calendar_view(selected_year, selected_month)
    
    # 使用说明
    st.markdown("---")
    with st.expander("📖 使用说明"):
        st.markdown("""
        ### 传统黄历说明
        
        **宜**: 适合进行的活动
        - 嫁娶：结婚、建立关系
        - 纳财：收钱、接受财物
        - 开市：开业、开工
        - 出行：外出、旅行
        
        **忌**: 不适合进行的活动
        - 破土：开工、动工
        - 安葬：埋葬、结束
        - 出行：外出不利
        
        ### 干支纪年
        - 天干：甲、乙、丙、丁、戊、己、庚、辛、壬、癸
        - 地支：子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥
        
        ### 重要提示
        1. 本功能为传统文化展示，仅供娱乐
        2. 股市投资需要理性分析
        3. 不要迷信，要相信科学
        4. 投资有风险，入市需谨慎
        """)

if __name__ == "__main__":
    display_daily_calendar()

