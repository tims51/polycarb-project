import logging
from typing import List, Dict, Any, Union, Optional
from datetime import datetime

from schemas.bom import BOMItem
from core.enums import DataCategory, UnitType, MaterialType
from services.data_service import DataService

logger = logging.getLogger(__name__)

class BOMService:
    def __init__(self, data_service: DataService = None):
        self.data_service = data_service or DataService()

    def explode_bom(self, bom_version_id: Union[int, str], target_qty: float = 1000.0) -> List[Dict[str, Any]]:
        """
        BOM 展开计算
        Args:
            bom_version_id: 版本ID
            target_qty: 目标产量
        Returns:
            list: [{item_id, item_name, item_type, required_qty, uom, ...}]
        """
        return self.data_service.explode_bom(bom_version_id, target_qty)

    def get_bom_tree_structure(self, bom_id: int, depth: int = 0, max_depth: int = 5) -> Optional[Dict[str, Any]]:
        """
        构建 BOM 多级树状结构
        """
        if depth > max_depth:
            return {"name": "Max Depth Reached", "code": "", "is_loop": True}

        data = self.data_service.load_data()
        boms = data.get(DataCategory.BOMS.value, [])
        
        bom = next((b for b in boms if b.get("id") == bom_id), None)
        if not bom:
            return None

        # 获取当前有效版本
        version = self.data_service.get_effective_bom_version(bom_id)
        
        node = {
            "id": bom.get("id"),
            "name": bom.get("bom_name"),
            "code": bom.get("bom_code"),
            "type": bom.get("bom_type"),
            "version": version.get("version") if version else None,
            "version_id": version.get("id") if version else None,
            "level": depth,
            "children": []
        }

        if version:
            lines = version.get("lines", [])
            for line in lines:
                item_type = line.get("item_type", MaterialType.RAW_MATERIAL.value)
                item_id = line.get("item_id")
                
                child_node = {
                    "item_id": item_id,
                    "item_name": line.get("item_name"),
                    "item_type": item_type,
                    "qty": line.get("qty"),
                    "uom": line.get("uom"),
                    "phase": line.get("phase"),
                    "substitutes": line.get("substitutes"),
                    "level": depth + 1
                }

                # 如果是半成品/成品，递归查找其 BOM
                # 这里假设 item_type == 'product' 时，item_id 对应 product_inventory 的 ID
                # 我们需要找到该 product 对应的 BOM
                # 这是一个反向查找：Product -> BOM
                # 通常 Product Name == BOM Name
                if item_type == MaterialType.PRODUCT.value:
                    sub_bom = None
                    # 尝试通过名称匹配 BOM
                    for b in boms:
                        # 简化匹配逻辑：BOM Name == Item Name
                        if b.get("bom_name") == line.get("item_name"):
                            sub_bom = b
                            break
                    
                    if sub_bom:
                        # 递归
                        sub_tree = self.get_bom_tree_structure(sub_bom.get("id"), depth + 1, max_depth)
                        child_node["sub_bom"] = sub_tree
                
                node["children"].append(child_node)

        return node

    def get_bom_version_diff(self, version_a: Dict[str, Any], version_b: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        比较两个 BOM 版本的差异
        Returns: List of diffs
        """
        lines_a = version_a.get("lines", []) or []
        lines_b = version_b.get("lines", []) or []
        
        # Map by (item_type, item_id)
        map_a = {}
        for l in lines_a:
            key = (l.get("item_type"), l.get("item_id"))
            map_a[key] = l
            
        map_b = {}
        for l in lines_b:
            key = (l.get("item_type"), l.get("item_id"))
            map_b[key] = l
            
        diffs = []
        all_keys = set(map_a.keys()) | set(map_b.keys())
        
        for key in all_keys:
            la = map_a.get(key)
            lb = map_b.get(key)
            
            if la and not lb:
                diffs.append({
                    "type": "deleted",
                    "item_name": la.get("item_name"),
                    "uom": la.get("uom"),
                    "qty": float(la.get("qty", 0)),
                    "old_qty": float(la.get("qty", 0)),
                    "new_qty": 0
                })
            elif not la and lb:
                diffs.append({
                    "type": "added",
                    "item_name": lb.get("item_name"),
                    "uom": lb.get("uom"),
                    "qty": float(lb.get("qty", 0)),
                    "old_qty": 0,
                    "new_qty": float(lb.get("qty", 0))
                })
            else:
                qty_a = float(la.get("qty", 0))
                qty_b = float(lb.get("qty", 0))
                if abs(qty_a - qty_b) > 1e-6:
                     diffs.append({
                        "type": "modified",
                        "item_name": lb.get("item_name"),
                        "uom": lb.get("uom"),
                        "qty": qty_b - qty_a,
                        "old_qty": qty_a,
                        "new_qty": qty_b
                    })
        
        return diffs
