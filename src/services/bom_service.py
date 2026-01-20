from typing import List, Dict, Any, Optional, Set, Tuple
from core.data_manager import DataManager
from utils.unit_helper import convert_quantity
from core.models import BOM, BOMVersion
from core.enums import MaterialType, UnitType

class BOMService:
    """
    BOM 业务逻辑服务层
    处理 BOM 树构建、版本比对、生产计划计算等复杂逻辑
    """
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def get_bom_tree_structure(self, bom_id: int, level: int = 0, visited: Optional[Set[int]] = None) -> Dict[str, Any]:
        """
        构建 BOM 树形结构数据
        Returns:
            Dict: {
                "id": bom_id,
                "name": str,
                "code": str,
                "version": str,
                "children": List[Dict],
                "is_loop": bool,
                "error": str
            }
        """
        if visited is None:
            visited = set()
            
        # 防止无限递归
        if bom_id in visited:
            return {
                "id": bom_id,
                "name": "循环引用",
                "is_loop": True,
                "level": level
            }
        
        current_visited = visited.copy()
        current_visited.add(bom_id)
        
        # 获取 BOM 信息
        boms = self.data_manager.get_all_boms()
        bom = next((b for b in boms if b['id'] == bom_id), None)
        if not bom:
            return None
            
        # 获取最新有效版本
        latest_ver = self.data_manager.get_effective_bom_version(bom_id)
        
        node = {
            "id": bom_id,
            "name": bom.get('bom_name', ''),
            "code": bom.get('bom_code', ''),
            "version": latest_ver.get('version', '无版本') if latest_ver else None,
            "level": level,
            "children": [],
            "has_version": bool(latest_ver)
        }
        
        if not latest_ver:
            return node
            
        # 构建子节点
        for line in latest_ver.get("lines", []):
            item_type = line.get('item_type', MaterialType.RAW_MATERIAL.value)
            item_id = line.get('item_id')
            
            child_node = {
                "item_name": line.get('item_name', 'Unknown'),
                "qty": line.get('qty', 0),
                "uom": line.get('uom', UnitType.KG.value),
                "item_type": item_type,
                "substitutes": line.get('substitutes', ''),
                "level": level + 1,
                "children": [] # 用于递归
            }
            
            if item_type == MaterialType.PRODUCT.value and item_id:
                # 递归获取子结构
                sub_structure = self.get_bom_tree_structure(item_id, level + 1, current_visited)
                if sub_structure:
                    child_node["sub_bom"] = sub_structure
                    
            node["children"].append(child_node)
            
        return node

    def calculate_production_plan(self, plan_batch_kg: float, target_types: List[str]) -> List[Dict[str, Any]]:
        """
        计算生产计划可行性与原材料需求
        """
        all_boms = self.data_manager.get_all_boms()
        raw_materials = self.data_manager.get_all_raw_materials()
        
        # 构建库存映射
        mat_inv = {m["id"]: float(m.get("stock_quantity", 0.0)) for m in raw_materials}
        bom_map = {b["id"]: f"{b.get('bom_code')}-{b.get('bom_name')}" for b in all_boms}
        
        # 筛选目标类型的 BOM
        type_boms = [b for b in all_boms if b.get("bom_type") in target_types]
        
        candidates = []
        for b in type_boms:
            v = self.data_manager.get_effective_bom_version(b["id"])
            if not v:
                continue
                
            req = self._calculate_per_batch_requirement(v, plan_batch_kg)
            if not req:
                continue
                
            score = self._calculate_scarcity_score(req, mat_inv)
            
            # 计算最大可生产批次
            batches = 0
            if req:
                batch_limits = []
                for mid, q in req.items():
                    if q > 0:
                        batch_limits.append(int((mat_inv.get(mid, 0.0)) // q))
                    else:
                        batch_limits.append(999999)
                batches = min(batch_limits) if batch_limits else 0
            
            candidates.append({
                "bom_id": b["id"],
                "bom_label": bom_map.get(b["id"]),
                "bom_type": b.get("bom_type"),
                "version_id": v["id"],
                "per_batch_require": req,
                "scarcity_score": score,
                "max_batches_possible": batches
            })
            
        # 按类型选择最优（紧缺度最低）
        by_type = {}
        for c in candidates:
            t = c["bom_type"]
            if t not in by_type or c["scarcity_score"] < by_type[t]["scarcity_score"]:
                by_type[t] = c
                
        # 格式化结果
        report_rows = []
        for t, sel in by_type.items():
            total_req = sum(sel["per_batch_require"].values())
            report_rows.append({
                "产品类型": t,
                "选用配方": sel["bom_label"],
                "可生产批次": sel["max_batches_possible"],
                "每批次原材料合计(kg)": round(total_req, 4),
                "_raw_data": sel # 保留原始数据供后续使用
            })
            
        return report_rows

    def _calculate_per_batch_requirement(self, version: Dict, plan_batch_kg: float) -> Dict[int, float]:
        """计算单批次原材料需求"""
        base = float(version.get("yield_base", 1000.0) or 1000.0)
        if base <= 0: base = 1000.0
        
        ratio = plan_batch_kg / base
        req = {}
        
        for line in version.get("lines", []):
            if line.get("item_type", MaterialType.RAW_MATERIAL.value) == MaterialType.RAW_MATERIAL.value:
                mid = line.get("item_id")
                lqty = float(line.get("qty", 0.0))
                luom = line.get("uom", UnitType.KG.value)
                
                need = lqty * ratio
                need_kg, ok = convert_quantity(need, luom, UnitType.KG.value)
                
                req[mid] = req.get(mid, 0.0) + (need_kg if ok else need)
        return req

    def _calculate_scarcity_score(self, requirements: Dict[int, float], inventory: Dict[int, float]) -> float:
        """计算紧缺度评分 (分数越高越紧缺)"""
        s = 0.0
        for mid, q in requirements.items():
            avail = inventory.get(mid, 0.0)
            # 可用量越少，权重越大
            w = 1.0 / (avail if avail > 0 else 1e-9)
            s += q * w
        return s

    def get_bom_version_diff(self, old_ver: Dict, new_ver: Dict) -> List[Dict[str, Any]]:
        """计算两个 BOM 版本的差异"""
        diffs = []
        
        old_lines = {l.get("item_id"): l for l in old_ver.get("lines", [])}
        new_lines = {l.get("item_id"): l for l in new_ver.get("lines", [])}
        
        all_ids = set(old_lines.keys()) | set(new_lines.keys())
        
        for mid in all_ids:
            old_l = old_lines.get(mid)
            new_l = new_lines.get(mid)
            
            if old_l and new_l:
                # 比较数量
                q1 = float(old_l.get("qty", 0))
                q2 = float(new_l.get("qty", 0))
                if abs(q1 - q2) > 1e-6:
                    diffs.append({
                        "type": "modified",
                        "item_name": new_l.get("item_name"),
                        "old_qty": q1,
                        "new_qty": q2,
                        "uom": new_l.get("uom")
                    })
            elif old_l:
                diffs.append({
                    "type": "deleted",
                    "item_name": old_l.get("item_name"),
                    "qty": old_l.get("qty"),
                    "uom": old_l.get("uom")
                })
            elif new_l:
                diffs.append({
                    "type": "added",
                    "item_name": new_l.get("item_name"),
                    "qty": new_l.get("qty"),
                    "uom": new_l.get("uom")
                })
                
        return diffs
    
    def get_material_usage_stats(self, target_types: List[str]) -> Dict[int, int]:
        """统计指定类型的 BOM 在生产单中的原材料使用频次"""
        orders_all = self.data_manager.get_all_production_orders()
        all_boms = self.data_manager.get_all_boms()
        all_versions = self.data_manager.get_all_bom_versions()
        
        bom_type_map = {b.get("id"): b.get("bom_type") for b in all_boms}
        ver_map = {v.get("id"): v for v in all_versions}
        
        mat_prod_count = {}
        
        for o in orders_all:
            status = o.get("status")
            if status not in ["released", "issued", "finished"]:
                continue
                
            bid = o.get("bom_id")
            if bom_type_map.get(bid) not in target_types:
                continue
                
            ver = ver_map.get(o.get("bom_version_id"))
            if not ver:
                continue
                
            used_mids = set()
            for line in ver.get("lines", []):
                if line.get("item_type", MaterialType.RAW_MATERIAL.value) == MaterialType.RAW_MATERIAL.value:
                    mid = line.get("item_id")
                    if mid:
                        used_mids.add(mid)
            
            for mid in used_mids:
                mat_prod_count[mid] = mat_prod_count.get(mid, 0) + 1
                
        return mat_prod_count
