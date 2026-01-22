# Polycarb Project - Core Development Standards & Rules

这是一份最高优先级的开发规范。所有生成的代码、修复脚本和逻辑修改必须严格遵守以下原则。

## 1. 🛡️ 脚本与数据修复原则 (Script Safety)
- **必须是幂等的 (Idempotency Required)**:
  - ❌ 禁止：直接做增量计算 (如 `stock += 5`)。
  - ✅ 强制：**设定目标值** (如 `stock = target_value`) 或 **检查前置条件** (如 `if stock != target: update`).
  - *理由：修复脚本可能会被重复运行，非幂等逻辑会导致数据错误的无限叠加。*
- **日志记录**: 所有数据变更脚本必须打印变更前后的值 (Old vs New)。

## 2. 🆔 身份唯一性原则 (Unique Identity)
- **唯一编码 (Unique Code/SKU)**:
  - 所有产品/原材料必须有唯一编码 (如 `YJSNJ-001`)。
  - ❌ 禁止：仅依赖 `product_name` 进行查找或关联。
  - ✅ 强制：后台逻辑、数据库关联必须使用 `id` 或 `product_code`。
- **UI 下拉框规范**:
  - 显示格式：`"{product_name} ({product_code})"` 或 `"{product_name} (ID: {id})"`。
  - 绑定值：必须是 `id`。
  - *目的：防止同名不同 ID 的“僵尸产品”导致用户选错。*

## 3. ⚖️ 单位与数值标准 (Unit Single Source of Truth)
- **数据库层 (Database)**:
  - **基础单位唯一**：所有重量数据在数据库中 **必须存储为千克 (kg)**。
  - ❌ 禁止：数据库中混存吨和千克。
- **输入层 (Input Layer)**:
  - **立即转换**：用户在 UI 输入“吨” (Tons) 时，代码必须在**保存前**立即乘以 1000。
  - `save_to_db(input_val * 1000)`
- **展示层 (Display Layer)**:
  - **按需转换**：仅在渲染 UI 给用户看时，除以 1000 显示为“吨”。
  - `render(db_val / 1000)`

## 4. 🚫 禁止模糊逻辑 (No Ambiguity)
- **禁止猜测单位**:
  - ❌ 严禁出现：`if val < 10: assume tons else assume kg` 这类启发式逻辑。
  - ✅ 强制：必须明确读取元数据中的单位，或依据上述第 3 条的“强制 kg”规则处理。
- **显式声明**: 在变量命名上明确单位，例如 `stock_qty_kg` 或 `input_qty_tons`，避免歧义。

## 5. UI/UX 规范
- **Master-Detail**: 管理类页面优先采用“左侧列表 + 右侧详情”布局。
- **状态可视化**: 使用颜色标签区分状态 (Draft=Grey, Posted=Green, Cancelled=Red)。