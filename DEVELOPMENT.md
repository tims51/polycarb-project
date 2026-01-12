# 开发指南 (Development Guide)

本指南旨在帮助开发人员理解项目架构，进行功能扩展和维护。

## 1. 架构设计

项目采用服务导向架构 (Service-Oriented Architecture)，主要层级如下：

*   **UI层 (`app/ui/`)**：负责页面渲染和用户交互，通过Streamlit实现。
*   **组件层 (`app/components/`)**：提供通用的UI组件（如侧边栏、样式管理器）。
*   **服务层 (`app/services/`)**：核心业务逻辑，包括数据读写、分析计算等。
*   **数据层 (`data.json`)**：基于JSON的文件存储，由 `DataService` 统一管理。

## 2. 核心服务

### DataService (`app/services/data_service.py`)
负责所有数据的CRUD操作。
*   使用 `_get_items`, `_add_item` 等通用方法减少代码重复。
*   自动处理数据备份。

### TimelineService (`app/services/timeline_service.py`)
负责项目时间线的计算逻辑。
*   输入：项目开始/结束日期。
*   输出：项目状态、进度百分比、剩余天数等。

### AnalysisService (`app/services/analysis_service.py`)
负责数据分析和AI预处理。
*   将嵌套的JSON数据转换为Pandas DataFrame。
*   计算相关性矩阵。
*   生成深度学习训练代码。

## 3. 开发流程

### 添加新页面
1.  在 `app/ui/pages/` 下创建新的页面文件（如 `new_page.py`）。
2.  定义渲染函数 `def render_new_page(data_service): ...`。
3.  在 `main.py` 的 `page_routes` 字典中注册新页面。

### 添加新数据类型
1.  在 `DataService` 中添加相应的CRUD方法（可复用通用Helper）。
2.  在 `DataService._ensure_data_structure` 中初始化数据键值。
3.  更新 `conftest.py` 中的测试夹具以包含新数据类型。

## 4. 测试

项目使用 `pytest` 进行单元测试。

### 运行测试
在项目根目录下运行：
```bash
python -m pytest tests
```

### 编写测试
测试文件位于 `tests/` 目录下。编写测试时，请使用 `data_service` fixture 来获取模拟的数据服务实例，避免污染真实数据。

```python
def test_new_feature(data_service):
    # Your test code here
    pass
```

## 5. 代码规范
*   遵循 PEP 8 编码规范。
*   所有新模块必须包含文档字符串 (Docstrings)。
*   关键逻辑必须添加单元测试。
*   使用类型注解 (Type Hints) 提高代码可读性。

## 6. 版本控制
*   提交代码前请确保所有测试通过。
*   保持提交信息清晰明了。
