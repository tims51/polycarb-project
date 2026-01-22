import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

from core.enums import DataCategory
from services.data_service import DataService
from utils.unit_helper import convert_to_base_unit, BASE_UNIT_RAW_MATERIAL

logger = logging.getLogger(__name__)

class ExperimentService:
    """实验管理服务，处理合成、净浆、砂浆和混凝土实验逻辑"""
    
    def __init__(self, data_service: DataService = None):
        self.data_service = data_service or DataService()

    # ------------------ 标签格式化工具 ------------------
    
    def get_raw_material_options(self) -> List[Dict[str, Any]]:
        """获取带 ID 的原材料选项列表"""
        materials = self.data_service.get_all_raw_materials()
        return [
            {
                "id": m["id"],
                "label": f"{m['name']} (ID: {m['id']})" + (f" ({m['abbreviation']})" if m.get('abbreviation') else ""),
                "data": m
            }
            for m in materials
        ]

    def get_synthesis_record_options(self) -> List[Dict[str, Any]]:
        """获取带 ID 的合成实验选项列表"""
        records = self.data_service.get_all_synthesis_records()
        return [
            {
                "id": r["id"],
                "label": f"{r.get('formula_id', '未命名')} (ID: {r['id']}) ({r.get('synthesis_date', '')})",
                "data": r
            }
            for r in records
        ]

    def get_mother_liquor_options(self) -> List[Dict[str, Any]]:
        """获取带 ID 的母液选项列表"""
        mother_liquors = self.data_service.load_data().get(DataCategory.MOTHER_LIQUORS.value, [])
        return [
            {
                "id": ml["id"],
                "label": f"{ml['name']} (ID: {ml['id']})" + (f" (批号:{ml['batch_number']})" if ml.get('batch_number') else ""),
                "data": ml
            }
            for ml in mother_liquors
        ]

    def get_product_options(self) -> List[Dict[str, Any]]:
        """获取带 ID 的成品选项列表"""
        products = self.data_service.get_all_products()
        return [
            {
                "id": p["id"],
                "label": f"{p['product_name']} (ID: {p['id']})" + (f" (批号:{p.get('batch_number', '')})" if p.get('batch_number') else ""),
                "data": p
            }
            for p in products
        ]

    # ------------------ 合成实验业务逻辑 ------------------

    def _convert_material_list_to_kg(self, materials: List[Dict[str, Any]], from_unit: str = "g") -> List[Dict[str, Any]]:
        """将物料列表中的用量转换为 kg"""
        if not materials:
            return []
        
        converted = []
        for m in materials:
            new_m = m.copy()
            qty = float(m.get("amount", 0.0))
            # 强制转换为 kg
            qty_kg, success = convert_to_base_unit(qty, from_unit, 'raw_material')
            if success:
                new_m["amount"] = qty_kg
                new_m["unit"] = "kg"
                # 保留原始单位和用量信息用于追踪
                if from_unit != "kg":
                    new_m["original_amount"] = qty
                    new_m["original_unit"] = from_unit
            converted.append(new_m)
        return converted

    def add_synthesis_record(self, record: Dict[str, Any], input_unit: str = "g") -> bool:
        """添加合成实验记录，处理单位转换 (默认 g -> kg)"""
        # 转换各个部分的物料用量
        for key in ["reactor_materials", "a_materials", "b_materials", "additive_materials"]:
            if key in record:
                record[key] = self._convert_material_list_to_kg(record[key], from_unit=input_unit)
        
        # 转换汇总用量
        for key in ["reactor_total_amount", "a_total_amount", "b_total_amount"]:
            if key in record:
                qty = float(record[key])
                qty_kg, _ = convert_to_base_unit(qty, input_unit, 'raw_material')
                record[key] = qty_kg
        
        # 滴加速度通常也涉及质量，但它是 g/min。如果我们要存 kg，它就变成了 kg/min。
        # 考虑到 UI 显示，这里可能需要谨慎处理。
        # 根据 AI_RULES.md，底层应存 kg。
        if "a_drip_speed" in record:
             val = float(record["a_drip_speed"])
             record["a_drip_speed"], _ = convert_to_base_unit(val, input_unit, 'raw_material')
        if "b_drip_speed" in record:
             val = float(record["b_drip_speed"])
             record["b_drip_speed"], _ = convert_to_base_unit(val, input_unit, 'raw_material')

        return self.data_service.add_synthesis_record(record)

    # ------------------ 净浆/砂浆/混凝土实验业务逻辑 ------------------

    def add_paste_experiment(self, data: Dict[str, Any], input_unit: str = "g") -> bool:
        """添加净浆实验记录，处理单位转换"""
        # 转换质量字段
        mass_fields = ["cement_amount_g", "water_amount_g", "admixture_dosage_g"]
        for field in mass_fields:
            if field in data:
                val = float(data[field])
                val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                data[field] = val_kg
                # 记录原始单位
                data[f"original_{field}"] = val
        
        return self.data_service.add_paste_experiment(data)

    def add_mortar_experiment(self, data: Dict[str, Any], input_unit: str = "g") -> bool:
        """添加砂浆实验记录，处理单位转换"""
        # 1. 转换基础质量字段
        mass_fields = ["cement_amount", "sand_amount", "water_amount", "admixture_amount"]
        for field in mass_fields:
            if field in data:
                val = float(data[field])
                val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                data[field] = val_kg

        # 2. 转换嵌套的材料列表 (binders, aggregates)
        if "materials" in data:
            materials = data["materials"]
            # 转换 binders
            if "binders" in materials:
                for b in materials["binders"]:
                    if "dosage" in b:
                        val = float(b["dosage"])
                        val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                        b["dosage"] = val_kg
                        b["unit"] = "kg"
            
            # 转换 aggregates
            if "aggregates" in materials:
                for a in materials["aggregates"]:
                    if "dosage" in a:
                        val = float(a["dosage"])
                        val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                        a["dosage"] = val_kg
                        a["unit"] = "kg"
            
            # 转换汇总字段
            summary_fields = ["water", "actual_water", "total_binder", "total_aggregate"]
            for field in summary_fields:
                if field in materials:
                    val = float(materials[field])
                    val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                    materials[field] = val_kg

        # 3. 转换测试配方中的组分用量
        if "test_recipes" in data:
            for recipe in data["test_recipes"]:
                if "components" in recipe:
                    for comp in recipe["components"]:
                        if "dosage" in comp:
                            val = float(comp["dosage"])
                            # 配方组分通常也是 g
                            val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                            comp["dosage"] = val_kg
                            comp["unit"] = "kg"
        
        return self.data_service.add_mortar_experiment(data)

    def add_concrete_experiment(self, data: Dict[str, Any], input_unit: str = "kg") -> bool:
        """添加混凝土实验记录，处理单位转换"""
        # 混凝土通常使用 kg/m³，如果 input_unit 是 kg，则不需要转换数值，只需确保单位标识正确。
        # 如果 input_unit 是 g (小拌量实验)，则需要转换。
        
        # 1. 转换基础字段
        mass_fields = ["cement", "water", "sand", "stone_small", "stone_large", "admixture", "fly_ash", "mineral_powder"]
        for field in mass_fields:
            if field in data:
                val = float(data[field])
                val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                data[field] = val_kg

        # 2. 转换嵌套的材料列表 (binders, aggregates)
        if "materials" in data:
            materials = data["materials"]
            # 转换 binders
            if "binders" in materials:
                for b in materials["binders"]:
                    qty_key = "用量(kg/m³)" if "用量(kg/m³)" in b else "dosage"
                    if qty_key in b:
                        val = float(b[qty_key])
                        val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                        b[qty_key] = val_kg
            
            # 转换 aggregates
            if "aggregates" in materials:
                for a in materials["aggregates"]:
                    qty_key = "用量(kg/m³)" if "用量(kg/m³)" in b else "dosage"
                    if qty_key in a:
                        val = float(a[qty_key])
                        val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                        a[qty_key] = val_kg
            
            # 转换汇总字段
            summary_fields = ["water", "actual_water", "total_binder", "total_aggregate"]
            for field in summary_fields:
                if field in materials:
                    val = float(materials[field])
                    val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                    materials[field] = val_kg

        # 3. 转换测试配方中的组分用量
        if "test_recipes" in data:
            for recipe in data["test_recipes"]:
                if "components" in recipe:
                    for comp in recipe["components"]:
                        if "dosage" in comp:
                            val = float(comp["dosage"])
                            val_kg, _ = convert_to_base_unit(val, input_unit, 'raw_material')
                            comp["dosage"] = val_kg
                            comp["unit"] = "kg"
        
        return self.data_service.add_concrete_experiment(data)
