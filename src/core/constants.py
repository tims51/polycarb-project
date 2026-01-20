# 全局常量定义

# 日期时间格式
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 系统默认值
DEFAULT_OPERATOR_NAME = "User"
DEFAULT_UNIT_KG = "kg"
DEFAULT_UNIT_TON = "吨"
DEFAULT_BOM_PLAN_QTY = 1000.0  # BOM计算默认基准数量
BACKUP_INTERVAL_SECONDS = 3600 # 自动备份间隔

# 特殊物料列表
# 这些物料通常不参与库存严格校验或有特殊逻辑
WATER_MATERIAL_ALIASES = [
    "水", 
    "自来水", 
    "纯水", 
    "去离子水", 
    "工业用水", 
    "生产用水"
]

# 特殊产品名称常量
PRODUCT_NAME_WJSNJ = "WJSNJ-无碱速凝剂"
PRODUCT_NAME_YJSNJ = "YJSNJ-有碱速凝剂"

# 实验默认值
DEFAULT_EXPERIMENT_PRIORITY = "中"
