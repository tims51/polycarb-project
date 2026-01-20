
import pandas as pd
from datetime import datetime, date
import streamlit as st
from core.data_manager import DataManager

class InventoryService:
    def __init__(self, data_manager: DataManager):
        self.dm = data_manager

    def get_products(self):
        raw_inventory = self.dm.get_product_inventory()
        # Create a copy to avoid modifying the original data structure in memory (unless we want to persist this change)
        # For display purposes, we return a modified copy.
        inventory = [dict(item) for item in raw_inventory]
        
        bom_map = self._get_production_mode_map()
        
        for item in inventory:
            # Update type based on BOM
            item["type"] = self._determine_mode(item.get("product_name", ""), bom_map)
            # Ensure unit exists
            if "unit" not in item:
                item["unit"] = "吨"
                
        return inventory

    def _get_production_mode_map(self):
        try:
            boms = self.dm.get_all_boms()
            bom_map = {}
            for bom in boms:
                mode = bom.get("production_mode", "自产")
                code = bom.get("bom_code", "").strip()
                name = bom.get("bom_name", "").strip()
                
                # Strategy 1: "Code-Name"
                if code and name:
                    bom_map[f"{code}-{name}"] = mode
                
                # Strategy 2: "Name" only
                if name:
                    bom_map[name] = mode
            return bom_map
        except Exception:
            return {}

    def _determine_mode(self, product_name, bom_map):
        p_name = str(product_name).strip()
        # Exact match
        if p_name in bom_map:
            return bom_map[p_name]
        
        # Fuzzy match
        for b_name, mode in bom_map.items():
            if b_name in p_name and len(b_name) > 1:
                return mode
        
        return "未知"

    def get_inventory_summary(self, low_stock_threshold=10.0):
        """
        获取库存概览：总库存、预警列表等
        """
        inventory = self.get_products()
        if not inventory:
            return {
                "total_stock": 0.0,
                "product_count": 0,
                "low_stock_items": [],
                "stock_distribution": pd.DataFrame()
            }
        
        df = pd.DataFrame(inventory)
        
        # 确保必要字段存在
        required_cols = ["product_name", "type", "unit", "current_stock"]
        for col in required_cols:
            if col not in df.columns:
                if col == "current_stock":
                    df[col] = 0.0
                elif col == "unit":
                    df[col] = "吨"
                else:
                    df[col] = "未知"

        # 填充缺失值
        df["type"] = df["type"].fillna("未知")
        df["unit"] = df["unit"].fillna("吨")

        # 确保数值类型
        df["current_stock"] = pd.to_numeric(df["current_stock"], errors='coerce').fillna(0.0)
        
        total_stock = df["current_stock"].sum()
        
        # 预警列表
        low_stock = df[df["current_stock"] < low_stock_threshold].to_dict('records')
        
        return {
            "total_stock": total_stock,
            "product_count": len(df),
            "low_stock_items": low_stock,
            "stock_distribution": df[["product_name", "current_stock", "type", "unit"]]
        }

    def process_inbound(self, product_name, product_type, quantity, batch_number, operator="User", date_str=None):
        """
        处理生产入库
        """
        if quantity <= 0:
            return False, "数量必须大于0"
        
        if not batch_number:
            return False, "必须提供生产批号"
            
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 构造记录
        record_data = {
            "product_name": product_name,
            "product_type": product_type,
            "quantity": quantity,
            "type": "produce_in",
            "reason": f"生产入库: {batch_number}",
            "operator": operator,
            "date": date_str,
            "batch_number": batch_number
        }
        
        return self.dm.add_product_inventory_record(record_data)

    def process_outbound(self, product_name, quantity, customer, remark="", operator="User", date_str=None):
        """
        处理销售出库
        """
        if quantity <= 0:
            return False, "数量必须大于0"
            
        # 检查库存
        inventory = self.get_products()
        prod = next((p for p in inventory if p.get("product_name") == product_name), None)
        if not prod:
            return False, "产品不存在"
            
        current_stock = float(prod.get("current_stock", 0))
        if current_stock < quantity:
            return False, f"库存不足 (当前: {current_stock})"

        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        reason = f"销售出库: {customer}"
        if remark:
            reason += f" ({remark})"

        record_data = {
            "product_name": product_name,
            "product_type": prod.get("type", "其他"),
            "quantity": quantity,
            "type": "ship_out",
            "reason": reason,
            "operator": operator,
            "date": date_str
        }
        
        return self.dm.add_product_inventory_record(record_data)

    def calibrate_stock(self, product_name, actual_stock, reason_note, operator="User"):
        """
        库存校准
        """
        inventory = self.get_products()
        prod = next((p for p in inventory if p.get("product_name") == product_name), None)
        if not prod:
            return False, "产品不存在"
            
        current_stock = float(prod.get("current_stock", 0))
        diff = actual_stock - current_stock
        
        if abs(diff) < 0.0001:
            return True, "库存无差异，无需调整"
            
        adj_type = "adjust_in" if diff > 0 else "adjust_out"
        
        record_data = {
            "product_name": product_name,
            "product_type": prod.get("type", "其他"),
            "quantity": abs(diff),
            "type": adj_type,
            "reason": f"库存校准: 系统{current_stock}->实盘{actual_stock}. 原因: {reason_note}",
            "operator": operator,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        return self.dm.add_product_inventory_record(record_data)

    def get_inventory_history(self, start_date=None, end_date=None, product_type=None, search_term=None):
        """
        查询库存流水
        """
        records = self.dm.get_product_inventory_records()
        if not records:
            return pd.DataFrame()
            
        df = pd.DataFrame(records)
        
        # 确保必要字段存在
        required_cols = ["date", "product_type", "product_name", "reason", "id"]
        for col in required_cols:
             if col not in df.columns:
                 if col == "id":
                     df[col] = 0
                 else:
                     df[col] = ""

        # 填充缺失值
        df["date"] = df["date"].fillna(datetime.now().strftime("%Y-%m-%d"))
        df["product_type"] = df["product_type"].fillna("其他")
        df["product_name"] = df["product_name"].fillna("未知")
        df["reason"] = df["reason"].fillna("")
        
        # 转换日期
        df["date"] = pd.to_datetime(df["date"], errors='coerce').dt.date
        
        # ---------------------------------------------------------
        # 映射 product_type 为 自产/代工 (保持一致性)
        # ---------------------------------------------------------
        bom_map = self._get_production_mode_map()
        df["product_type"] = df["product_name"].apply(lambda x: self._determine_mode(x, bom_map))
        # ---------------------------------------------------------
        
        # 过滤
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
            
        if product_type and product_type != "全部":
            df = df[df["product_type"] == product_type]
            
        if search_term:
            term = search_term.lower()
            df = df[
                df["product_name"].str.lower().str.contains(term) | 
                df["reason"].str.lower().str.contains(term)
            ]
            
        # 排序
        df = df.sort_values(by=["date", "id"], ascending=[False, False])
        
        return df
