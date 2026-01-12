"""数据管理页面模块"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
import shutil
from pathlib import Path

def render_data_management(data_manager):
    """渲染数据管理页面"""
    st.header("💾 数据管理")
    
    # 使用标签页组织功能
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 数据导出", 
        "📥 数据导入", 
        "🔙 备份管理",
        "⚙️ 系统设置"
    ])
    
    # 数据导出模块
    with tab1:
        _render_export_tab(data_manager)
    
    # 数据导入模块
    with tab2:
        _render_import_tab(data_manager)
    
    # 备份管理模块
    with tab3:
        _render_backup_tab(data_manager)
    
    # 系统设置模块
    with tab4:
        _render_system_settings_tab(data_manager)

def _render_export_tab(data_manager):
    """渲染数据导出标签页"""
    st.subheader("📤 导出数据到Excel")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("""
        **导出功能说明:**
        - 导出所有数据到Excel文件
        - 包含项目、实验、原材料、合成实验、成品减水剂等所有数据
        - 自动生成数据字典说明
        - 文件格式: .xlsx (Excel 2007+)
        """)
    
    with col2:
        # 数据统计
        st.metric("项目数量", len(data_manager.get_all_projects()))
        st.metric("实验数量", len(data_manager.get_all_experiments()))
        st.metric("原材料数量", len(data_manager.get_all_raw_materials()))
    
    # 导出选项
    st.markdown("### 导出选项")
    
    col1, col2 = st.columns(2)
    with col1:
        filename = st.text_input(
            "导出文件名",
            value=f"聚羧酸减水剂研发数据_{datetime.now().strftime('%Y%m%d_%H%M')}",
            help="不需要添加.xlsx扩展名"
        )
    
    # 导出按钮
    if st.button("🚀 开始导出数据", type="primary", use_container_width=True):
        with st.spinner("正在准备导出数据..."):
            time.sleep(1)
            
            # 执行导出
            download_link = data_manager.export_to_excel()
            
            if download_link:
                st.success("✅ 数据导出成功！")
                st.markdown(download_link, unsafe_allow_html=True)
                
                # 显示导出统计
                with st.expander("📊 导出数据统计", expanded=False):
                    st.write(f"**项目:** {len(data_manager.get_all_projects())} 条")
                    st.write(f"**实验:** {len(data_manager.get_all_experiments())} 条")
                    st.write(f"**原材料:** {len(data_manager.get_all_raw_materials())} 条")
                    st.write(f"**合成实验:** {len(data_manager.get_all_synthesis_records())} 条")
                    st.write(f"**成品减水剂:** {len(data_manager.get_all_products())} 条")
            else:
                st.error("❌ 数据导出失败，请重试")

def _render_import_tab(data_manager):
    """渲染数据导入标签页"""
    st.subheader("📥 从Excel导入数据")
    
    st.warning("""
    ⚠️ **导入前请注意:**
    1. 建议先备份当前数据
    2. 导入将覆盖现有数据
    3. 确保导入文件格式正确
    4. 导入过程可能需要一些时间
    """)
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "选择Excel文件", 
        type=['xlsx', 'xls'],
        help="支持 .xlsx 和 .xls 格式"
    )
    
    if uploaded_file is not None:
        try:
            # 预览数据
            st.markdown("### 文件预览")
            excel_file = pd.ExcelFile(uploaded_file)
            
            # 显示工作表信息
            sheet_names = excel_file.sheet_names
            st.write(f"**检测到 {len(sheet_names)} 个工作表:**")
            
            for sheet in sheet_names:
                with st.expander(f"📋 {sheet}", expanded=False):
                    try:
                        df = pd.read_excel(uploaded_file, sheet_name=sheet, nrows=10)
                        st.dataframe(df.head(5))
                        st.write(f"总行数: {len(df)}")
                    except Exception as e:
                        st.error(f"读取工作表 '{sheet}' 失败: {e}")
            
            # 导入选项
            st.markdown("### 导入选项")
            
            col1, col2 = st.columns(2)
            with col1:
                import_mode = st.radio(
                    "导入模式",
                    options=["替换现有数据", "合并数据（不重复）"],
                    index=0
                )
            
            with col2:
                conflict_resolution = st.selectbox(
                    "数据冲突处理",
                    options=["跳过重复数据", "覆盖重复数据"],
                    disabled=(import_mode == "替换现有数据")
                )
            
            # 备份选项
            create_backup = st.checkbox("导入前自动备份当前数据", value=True)
            
            # 导入按钮
            if st.button("🚀 开始导入数据", type="primary", use_container_width=True):
                if create_backup:
                    with st.spinner("正在创建备份..."):
                        data_manager.create_backup()
                        st.success("✅ 数据备份完成")
                
                with st.spinner("正在导入数据，请稍候..."):
                    success, message = data_manager.import_from_excel(uploaded_file)
                    
                    if success:
                        st.success(f"✅ 数据导入成功！")
                        st.info(f"导入统计: {message}")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ 导入失败: {message}")
            
        except Exception as e:
            st.error(f"读取文件失败: {e}")

def _render_backup_tab(data_manager):
    """渲染备份管理标签页"""
    st.subheader("🔙 备份管理")
    
    col1, col2 = st.columns(2)
    with col1:
        # 立即备份
        if st.button("🔄 立即创建备份", use_container_width=True, type="primary"):
            with st.spinner("正在创建备份..."):
                if data_manager.create_backup():
                    st.success("✅ 备份创建成功！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 备份创建失败")
    
    with col2:
        # 手动触发备份清理
        if st.button("🧹 清理旧备份", use_container_width=True, type="secondary"):
            data_manager._cleanup_old_backups()
            st.success("✅ 备份清理完成")
            time.sleep(1)
            st.rerun()
    
    # 备份文件列表
    st.markdown("### 📋 备份文件列表")
    
    backup_files = list(data_manager.backup_dir.glob("data_backup_*.json"))
    
    if backup_files:
        # 按修改时间排序（最新的在前面）
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 备份统计
        total_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)  # MB
        st.write(f"**备份文件数量:** {len(backup_files)} 个")
        st.write(f"**总占用空间:** {total_size:.2f} MB")
        
        # 备份文件表格
        backup_data = []
        for i, file in enumerate(backup_files[:20], 1):
            file_size = file.stat().st_size / 1024  # KB
            modified_time = datetime.fromtimestamp(file.stat().st_mtime)
            backup_data.append({
                "序号": i,
                "文件名": file.name,
                "大小": f"{file_size:.1f} KB",
                "修改时间": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                "文件路径": str(file)
            })
        
        if backup_data:
            df = pd.DataFrame(backup_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 备份操作
        st.markdown("### 🔧 备份操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 选择要恢复的备份
            backup_options = {f"{i+1}. {f.name}": str(f) for i, f in enumerate(backup_files[:10])}
            if backup_options:
                selected_backup = st.selectbox(
                    "选择备份文件恢复",
                    options=list(backup_options.keys())
                )
        
        with col2:
            if st.button("📥 恢复备份", disabled=not backup_options):
                backup_file = Path(backup_options[selected_backup])
                if backup_file.exists():
                    # 先备份当前数据
                    data_manager.create_backup()
                    
                    # 恢复备份
                    try:
                        shutil.copy2(backup_file, data_manager.data_file)
                        st.success("✅ 备份恢复成功！系统将重新加载...")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"恢复失败: {e}")
        
        with col3:
            if st.button("🗑️ 删除所有备份", type="secondary"):
                confirm = st.checkbox("确认删除所有备份文件？")
                if confirm and st.button("永久删除", type="primary"):
                    for file in backup_files:
                        file.unlink()
                    st.success("✅ 所有备份文件已删除")
                    time.sleep(2)
                    st.rerun()
    else:
        st.info("暂无备份文件")

def _render_system_settings_tab(data_manager):
    """渲染系统设置标签页"""
    st.subheader("⚙️ 系统设置")
    
    # 系统信息
    st.markdown("### 系统信息")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if data_manager.data_file.exists():
            file_size = data_manager.data_file.stat().st_size / 1024  # KB
            st.metric("数据文件大小", f"{file_size:.1f} KB")
        else:
            st.metric("数据文件大小", "0 KB")
    
    with col2:
        backup_count = len(list(data_manager.backup_dir.glob("data_backup_*.json")))
        st.metric("备份文件数量", backup_count)
    
    with col3:
        if data_manager.data_file.exists():
            st.metric("最后修改", datetime.fromtimestamp(
                data_manager.data_file.stat().st_mtime).strftime("%m-%d %H:%M")
            )
        else:
            st.metric("最后修改", "无")
    
    # 数据清理选项
    st.markdown("### 🧹 数据清理")
    
    with st.expander("高级数据清理选项", expanded=False):
        st.warning("⚠️ 这些操作不可逆，请谨慎操作！")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 清理空数据
            if st.button("清理空记录", type="secondary"):
                st.info("清理空记录功能开发中...")
        
        with col2:
            # 重置系统
            if st.button("重置系统数据", type="secondary"):
                st.error("🚨 危险操作！")
                confirm = st.checkbox("我确认要重置所有数据")
                if confirm and st.button("确认重置", type="primary"):
                    # 备份当前数据
                    data_manager.create_backup()
                    
                    # 重置为初始数据
                    initial_data = data_manager.get_initial_data()
                    data_manager.save_data(initial_data)
                    
                    st.success("✅ 系统已重置为初始状态")
                    time.sleep(2)
                    st.rerun()