"""
Reports Page
Handles report generation and export.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from services.data_service import DataService

def render_reports(data_service: DataService):
    """Render the reports generation page."""
    st.header("📑 报表生成")
    
    report_type = st.selectbox("报表类型", ["实验汇总日报", "项目进度周报", "月度质量分析"])
    
    if report_type == "实验汇总日报":
        render_daily_report(data_service)
    elif report_type == "项目进度周报":
        render_weekly_report(data_service)
    else:
        render_monthly_report(data_service)

def render_daily_report(data_service: DataService):
    """Render daily report generation UI."""
    st.subheader("实验汇总日报")
    
    date = st.date_input("选择日期", datetime.now())
    date_str = date.strftime("%Y-%m-%d")
    
    if st.button("生成预览"):
        # Fetch data for the date
        synthesis = [x for x in data_service.get_all_synthesis_records() if x.get("record_date") == date_str]
        paste = [x for x in data_service.get_all_paste_experiments() if x.get("record_date") == date_str]
        
        st.markdown(f"### {date_str} 实验汇总")
        
        st.markdown("#### 1. 合成实验")
        if synthesis:
            st.table(pd.DataFrame(synthesis)[["batch_no", "operator", "water_reduction", "solid_content"]])
        else:
            st.info("无合成记录")
            
        st.markdown("#### 2. 净浆实验")
        if paste:
            st.table(pd.DataFrame(paste)[["sample_id", "operator", "cement_type", "initial_diameter"]])
        else:
            st.info("无净浆记录")
            
        # Mock export
        st.download_button("导出PDF (模拟)", b"Mock PDF Content", f"report_{date_str}.pdf")

def render_weekly_report(data_service: DataService):
    st.info("周报生成功能开发中...")

def render_monthly_report(data_service: DataService):
    st.info("月报生成功能开发中...")
