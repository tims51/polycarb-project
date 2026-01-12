
import streamlit as st
import pandas as pd
import plotly.express as px
from core.analysis_manager import AnalysisManager
import json

def render_analysis_page(data_manager):
    """渲染数据分析页面"""
    st.header("📈 数据分析与AI训练")
    
    # 初始化分析管理器
    am = AnalysisManager(data_manager)
    
    # 数据源选择
    with st.sidebar:
        st.subheader("分析设置")
        data_source = st.selectbox(
            "选择数据源",
            ["混凝土实验 (Concrete)", "砂浆实验 (Mortar)", "净浆实验 (Paste)", "成品数据 (Product)"],
            key="analysis_source"
        )
        
        source_map = {
            "混凝土实验 (Concrete)": "concrete",
            "砂浆实验 (Mortar)": "mortar",
            "净浆实验 (Paste)": "paste",
            "成品数据 (Product)": "product"
        }
        
        current_type = source_map[data_source]
    
    # 获取数据
    df = am.get_data_as_dataframe(current_type)
    
    if df.empty:
        st.warning(f"⚠️ {data_source} 暂无数据，请先在数据记录页面添加数据。")
        return

    # -------------------- 标签页布局 --------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 数据概览", 
        "🔍 关联分析", 
        "📉 趋势可视化", 
        "🤖 AI训练准备"
    ])
    
    # ==================== Tab 1: 数据概览 ====================
    with tab1:
        st.subheader("数据概览")
        st.write(f"共加载 {len(df)} 条记录，包含 {len(df.columns)} 个特征。")
        
        # 显示数据表
        st.dataframe(df, use_container_width=True)
        
        # 统计描述
        st.subheader("统计描述")
        st.dataframe(df.describe(), use_container_width=True)
        
        # 数据质量检查
        st.subheader("数据质量")
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            st.warning("检测到缺失值：")
            st.write(null_counts[null_counts > 0])
        else:
            st.success("✅ 数据完整，无缺失值。")

    # ==================== Tab 2: 关联分析 ====================
    with tab2:
        st.subheader("特征关联分析")
        
        # 计算相关性
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        if len(numeric_cols) < 2:
            st.info("数值型特征不足，无法进行关联分析。")
        else:
            # 热力图
            st.markdown("#### 相关性热力图")
            corr_matrix = df[numeric_cols].corr()
            fig_heatmap = px.imshow(
                corr_matrix, 
                text_auto=True, 
                aspect="auto",
                color_continuous_scale="RdBu_r",
                title="特征相关性矩阵"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.divider()
            
            # 散点图探索
            st.markdown("#### 双变量关系探索")
            col_x, col_y, col_color = st.columns(3)
            
            with col_x:
                x_axis = st.selectbox("X轴变量", numeric_cols, index=0)
            with col_y:
                y_axis = st.selectbox("Y轴变量", numeric_cols, index=min(1, len(numeric_cols)-1))
            with col_color:
                # 尝试找到分类变量用于着色
                cat_cols = df.select_dtypes(include=['object']).columns.tolist()
                color_axis = st.selectbox("颜色分组 (可选)", ["无"] + cat_cols)
            
            if color_axis == "无":
                color_arg = None
            else:
                color_arg = color_axis
                
            fig_scatter = px.scatter(
                df, x=x_axis, y=y_axis, color=color_arg,
                title=f"{x_axis} vs {y_axis}",
                trendline="ols" if len(df) > 2 else None
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

    # ==================== Tab 3: 趋势可视化 ====================
    with tab3:
        st.subheader("数据分布与趋势")
        
        viz_col = st.selectbox("选择要分析的变量", numeric_cols)
        
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown(f"**{viz_col} 分布直方图**")
            fig_hist = px.histogram(df, x=viz_col, nbins=20, marginal="box")
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with col_v2:
            st.markdown(f"**{viz_col} 序列图 (按索引)**")
            fig_line = px.line(df, y=viz_col, markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

    # ==================== Tab 4: AI训练准备 ====================
    with tab4:
        st.subheader("🤖 AI 数据集生成")
        st.info("在此配置并导出用于机器学习/深度学习的数据集。")
        
        ai_col1, ai_col2 = st.columns([1, 2])
        
        with ai_col1:
            st.markdown("#### 1. 特征选择")
            target_col = st.selectbox("选择目标变量 (Target)", numeric_cols, index=len(numeric_cols)-1)
            
            feature_options = [c for c in numeric_cols if c != target_col]
            selected_features = st.multiselect(
                "选择特征变量 (Features)", 
                feature_options, 
                default=feature_options
            )
            
            split_ratio = st.slider("训练集比例", 0.5, 0.9, 0.8, 0.05)
            
        with ai_col2:
            if not selected_features:
                st.warning("请至少选择一个特征变量。")
            else:
                st.markdown("#### 2. 数据预览")
                # 准备数据
                dataset = am.prepare_ai_dataset(df, target_col, selected_features, split_ratio)
                
                if "error" in dataset: # 简单的错误处理假设
                     pass
                else:
                    st.write(f"**训练集样本数:** {len(dataset['X_train'])} | **测试集样本数:** {len(dataset['X_test'])}")
                    
                    st.markdown("**X_train (前5行):**")
                    st.dataframe(dataset['X_train'].head(), use_container_width=True)
                    
                    # 下载按钮
                    st.markdown("#### 3. 导出数据")
                    
                    # 将训练集和测试集转换为CSV字符串
                    train_df = dataset['X_train'].copy()
                    train_df[target_col] = dataset['y_train']
                    csv_train = train_df.to_csv(index=False).encode('utf-8')
                    
                    test_df = dataset['X_test'].copy()
                    test_df[target_col] = dataset['y_test']
                    csv_test = test_df.to_csv(index=False).encode('utf-8')
                    
                    d_col1, d_col2 = st.columns(2)
                    with d_col1:
                        st.download_button(
                            label="⬇️ 下载训练集 (train.csv)",
                            data=csv_train,
                            file_name="polycarb_train.csv",
                            mime="text/csv",
                            type="primary"
                        )
                    with d_col2:
                        st.download_button(
                            label="⬇️ 下载测试集 (test.csv)",
                            data=csv_test,
                            file_name="polycarb_test.csv",
                            mime="text/csv"
                        )
                        
                    # 代码生成
                    st.divider()
                    st.markdown("#### 4. 代码集成")
                    code_tab1, code_tab2 = st.tabs(["PyTorch", "TensorFlow"])
                    
                    with code_tab1:
                        st.code(am.generate_pytorch_code(selected_features, target_col), language="python")
                        
                    with code_tab2:
                        st.code(am.generate_tensorflow_code(selected_features, target_col), language="python")

