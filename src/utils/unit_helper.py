"""
单位转换工具模块
用于处理库存管理中的单位转换问题
"""

# 质量单位基准表 (以 kg 为基准)
MASS_UNITS = {
    'kg': 1.0,
    'kgs': 1.0,
    '公斤': 1.0,
    '千克': 1.0,
    'ton': 1000.0,
    'tons': 1000.0,
    't': 1000.0,
    '吨': 1000.0,
    'g': 0.001,
    'gram': 0.001,
    '克': 0.001,
    'mg': 0.000001,
    '毫克': 0.000001,
    'lb': 0.453592,
    'lbs': 0.453592,
    '磅': 0.453592
}

# 体积单位基准表 (以 L 为基准)
VOLUME_UNITS = {
    'l': 1.0,
    'liter': 1.0,
    'liters': 1.0,
    '升': 1.0,
    'ml': 0.001,
    'milliliter': 0.001,
    '毫升': 0.001,
    'm3': 1000.0,
    '立方米': 1000.0
}

# 基准单位定义
BASE_UNIT_RAW_MATERIAL = "kg"
BASE_UNIT_PRODUCT = "kg"

def normalize_unit(unit_str):
    """标准化单位字符串"""
    if not unit_str:
        return ""
    return unit_str.lower().strip()

def get_supported_units(category='mass'):
    """获取支持的单位列表"""
    if category == 'mass':
        return sorted(list(MASS_UNITS.keys()))
    elif category == 'volume':
        return sorted(list(VOLUME_UNITS.keys()))
    else:
        return sorted(list(MASS_UNITS.keys()) + list(VOLUME_UNITS.keys()))

def get_conversion_factor(from_unit, to_unit):
    """
    获取转换系数 (from_unit -> to_unit)
    例如: from='ton', to='kg' -> 1000.0
    如果无法转换返回 None
    """
    u1 = normalize_unit(from_unit)
    u2 = normalize_unit(to_unit)
    
    if not u1 or not u2:
        return None
        
    if u1 == u2:
        return 1.0
        
    # 尝试质量转换
    if u1 in MASS_UNITS and u2 in MASS_UNITS:
        return MASS_UNITS[u1] / MASS_UNITS[u2]
        
    # 尝试体积转换
    if u1 in VOLUME_UNITS and u2 in VOLUME_UNITS:
        return VOLUME_UNITS[u1] / VOLUME_UNITS[u2]
        
    # 尝试跨类转换 (假设水密度 1kg = 1L) - 这是一个简单的兜底，仅适用于水
    # 但为了安全起见，如果不匹配则返回 None，由上层决定是否警告
    return None

def convert_quantity(qty, from_unit, to_unit):
    """
    转换数量
    返回: (转换后的数量, 是否成功)
    """
    try:
        val = float(qty)
    except:
        return 0.0, False
        
    factor = get_conversion_factor(from_unit, to_unit)
    if factor is not None:
        return val * factor, True
    return val, False

def convert_to_base_unit(qty, from_unit, material_type='raw_material'):
    """
    将数量转换为系统的基准存储单位
    Raw Material -> kg
    Product -> kg (根据 AI_RULES.md 强制要求)
    """
    target_unit = BASE_UNIT_RAW_MATERIAL if material_type == 'raw_material' else BASE_UNIT_PRODUCT
    return convert_quantity(qty, from_unit, target_unit)
