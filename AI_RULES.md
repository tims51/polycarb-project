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


##6。 启用 Linter（代码检查器）： 在您的 IDE（如 VS Code）中配置 Ruff 或 Pylint。它们能瞬间标红未定义的变量（如之前的 inventory_service 或 stock_opening），防止低级错误进入运行时。

##7. 引入类型检查（Type Hinting）： 继续坚持使用类型注解（如 def func(data: pd.DataFrame) -> None:）。配合 Mypy 工具，它能检查出您是否对一个 None 对象调用了方法，或者传入了错误的参数类型。

##8 防御性初始化： 涉及累加或条件赋值的变量（如库存计算中的中间变量），务必在逻辑块的最开始给予默认值（如 0.0 或 None），避免因 if 分支未命中导致的变量未定义。

##9 Pydantic 严格模式： 利用 Pydantic 进行更严格的数据清洗。在数据进入核心计算逻辑前，先通过 Model 过滤，确保所有必需字段（字段名、数据类型）都符合预期，避免运行时的 KeyError。

##10 检查前置条件： 在执行写入/更新操作前，先检查目标状态。例如：if current_stock != target_stock: update()。
使用数据库事务： 如果使用数据库，确保关键操作在事务（Transaction）中执行。要么全部成功，要么全部回滚，避免出现“扣了原材料但没生成成品”的中间状态。
唯一约束（Unique Constraints）： 在数据库层面对关键字段（如产品编码、订单号）设置唯一索引，从底层防止重复数据的产生。

##11参数传递规范： 规定 Service 层之间必须通过 Context 或 Container 传递，禁止散乱的参数列表。
单位处理铁律： 再次强调“数据库存基准单位（如 kg），UI 负责转换”，并在代码审查中将其作为必查项。