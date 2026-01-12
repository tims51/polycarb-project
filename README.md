# 聚羧酸减水剂研发管理系统 (Polycarboxylate Superplasticizer R&D Management System)

## 项目简介
本项目是一个用于管理聚羧酸减水剂研发过程的综合管理系统，涵盖了从项目立项、实验设计、数据记录（合成、净浆、砂浆、混凝土）到数据分析和报表生成的全流程管理。

## 目录结构
项目采用了模块化的服务架构，主要目录结构如下：

```
polycarb_project/
├── app/
│   ├── components/     # UI组件 (Sidebar, UI Manager等)
│   ├── services/       # 业务逻辑服务 (DataService, AnalysisService, TimelineService)
│   ├── ui/
│   │   └── pages/      # 页面模块 (Dashboard, Experiments, DataEntry等)
│   ├── utils/          # 工具函数 (Logger, Helpers)
│   ├── config.py       # 配置文件
│   └── requirements.txt # 依赖列表
├── tests/              # 单元测试
├── data.json           # 数据存储文件
├── main.py             # 程序入口
├── README.md           # 项目说明文档
└── DEVELOPMENT.md      # 开发指南
```

## 功能特性

1.  **项目管理**：支持项目的创建、进度跟踪和时间线管理。
2.  **实验管理**：
    *   **合成实验**：记录合成工艺参数及产品性能。
    *   **净浆/砂浆/混凝土实验**：记录应用性能测试数据。
3.  **数据分析**：
    *   自动生成相关性热力图。
    *   支持自定义数据可视化（散点图、折线图、柱状图）。
    *   AI数据集准备（支持PyTorch/TensorFlow代码生成）。
4.  **报表生成**：支持生成日报、周报等实验汇总报表。
5.  **移动端适配**：优化的移动端访问体验，支持扫码访问。

## 安装与运行

### 环境要求
*   Python 3.8+
*   Streamlit

### 安装依赖
```bash
pip install -r app/requirements.txt
```

### 运行系统
```bash
streamlit run main.py
```

## 数据备份
系统会自动在 `app/backups/` 目录下创建数据备份，确保数据安全。

## 许可证
Private (内部使用)
