"""
Data Analysis Page
Handles data visualization, correlation analysis, and AI dataset preparation.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.data_service import DataService
from services.analysis_service import AnalysisService

def render_analysis(data_service: DataService):
    """Render the analysis page."""
    st.header("📈 数据分析与AI")
    
    # Initialize services
    analysis_service = AnalysisService(data_service)
    
    # Sidebar controls
    with st.sidebar:
        st.subheader("分析设置")
        data_type = st.selectbox(
            "数据类型",
            ["concrete", "mortar", "paste", "synthesis", "product"],
            format_func=lambda x: {
                "concrete": "混凝土实验",
                "mortar": "砂浆实验",
                "paste": "净浆实验",
                "synthesis": "合成记录",
                "product": "成品管理"
            }[x]
        )
    
    # Load data
    df = analysis_service.get_data_as_dataframe(data_type)
    
    if df.empty:
        st.warning("暂无数据可供分析")
        return

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 数据概览", "🔗 相关性分析", "📉 可视化图表", "🤖 AI准备"])
    
    # --- Tab 1: Data Overview ---
    with tab1:
        st.subheader("数据预览")
        st.dataframe(df, use_container_width=True)
        
        st.subheader("统计信息")
        st.write(df.describe())
        
    # --- Tab 2: Correlation ---
    with tab2:
        st.subheader("相关性热力图")
        corr_matrix = analysis_service.get_correlation_matrix(df)
        
        if not corr_matrix.empty:
            fig = px.imshow(
                corr_matrix,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="RdBu_r",
                title=f"{data_type} 相关性分析"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("数据中没有足够的数值列进行相关性分析")

    # --- Tab 3: Visualization ---
    with tab3:
        st.subheader("自定义绘图")
        
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        all_cols = df.columns.tolist()
        
        if len(numeric_cols) < 2:
            st.info("需要至少两个数值列进行绘图")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                x_axis = st.selectbox("X轴", all_cols, index=0)
            with col2:
                y_axis = st.selectbox("Y轴", numeric_cols, index=min(1, len(numeric_cols)-1))
            with col3:
                color_by = st.selectbox("颜色分组", ["None"] + all_cols)
                
            plot_type = st.radio("图表类型", ["散点图", "折线图", "柱状图"], horizontal=True)
            
            color_arg = None if color_by == "None" else color_by
            
            if plot_type == "散点图":
                fig = px.scatter(df, x=x_axis, y=y_axis, color=color_arg, title=f"{y_axis} vs {x_axis}")
            elif plot_type == "折线图":
                fig = px.line(df, x=x_axis, y=y_axis, color=color_arg, title=f"{y_axis} over {x_axis}")
            else:
                fig = px.bar(df, x=x_axis, y=y_axis, color=color_arg, title=f"{y_axis} by {x_axis}")
                
            st.plotly_chart(fig, use_container_width=True)

    # --- Tab 4: AI Preparation ---
    with tab4:
        st.subheader("AI 数据集生成")
        
        st.markdown("选择目标变量（预测对象）和特征变量（输入），生成用于PyTorch或TensorFlow的训练代码。")
        
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        if not numeric_cols:
            st.warning("没有数值列可用于AI训练")
        else:
            col1, col2 = st.columns(2)
            with col1:
                target_col = st.selectbox("目标变量 (y)", numeric_cols)
            
            with col2:
                feature_cols = st.multiselect(
                    "特征变量 (X)", 
                    numeric_cols, 
                    default=[c for c in numeric_cols if c != target_col]
                )
            
            if feature_cols:
                st.subheader("代码生成")
                framework = st.radio("深度学习框架", ["PyTorch", "TensorFlow"])
                
                if framework == "PyTorch":
                    code = analysis_service.generate_pytorch_code(feature_cols, target_col)
                    st.code(code, language="python")
                else:
                    code = analysis_service.generate_tensorflow_code(feature_cols, target_col)
                    st.code(code, language="python")
                    
                if st.button("导出预处理后的CSV"):
                    # Prepare and allow download
                    processed_data = analysis_service.prepare_ai_dataset(df, target_col, feature_cols)
                    if isinstance(processed_data, dict):
                        # Create a downloadable CSV of the processed data (just simple merge for demo)
                        # Actually just downloading the selected columns is enough
                        export_df = df[feature_cols + [target_col]].fillna(0)
                        csv = export_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "下载训练数据 CSV",
                            csv,
                            "train_data.csv",
                            "text/csv",
                            key='download-csv'
                        )
            else:
                st.info("请至少选择一个特征变量")
