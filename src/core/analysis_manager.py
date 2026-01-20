
import pandas as pd
import numpy as np
from datetime import datetime

class AnalysisManager:
    """数据分析与AI准备管理器"""
    
    def __init__(self, data_manager):
        self.dm = data_manager

    def _flatten_dict(self, d, parent_key='', sep='_'):
        """递归展平嵌套字典"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def get_data_as_dataframe(self, data_type="concrete"):
        """获取指定类型的数据并转换为DataFrame（自动展平嵌套结构）"""
        data = []
        if data_type == "concrete":
            data = self.dm.get_all_concrete_experiments()
        elif data_type == "mortar":
            data = self.dm.get_all_mortar_experiments()
        elif data_type == "paste":
            data = self.dm.get_all_paste_experiments()
        elif data_type == "product":
            data = self.dm.get_all_products()
        elif data_type == "synthesis":
             # Synthesis records might be stored in 'synthesis_records' or 'performance_data.synthesis'
             # Based on data_manager.py, there is 'synthesis_records' key.
             # I need to check if there is a getter for it. 
             # Assuming dm.get_all_synthesis_records() exists or accessing raw data.
             # Safe fallback: access raw data if method missing
             if hasattr(self.dm, 'get_all_synthesis_records'):
                 data = self.dm.get_all_synthesis_records()
             else:
                 data = self.dm.load_data().get('synthesis_records', [])
        
        if not data:
            return pd.DataFrame()

        # 展平嵌套结构 (如 materials.cement -> materials_cement)
        flattened_data = [self._flatten_dict(record) for record in data]
        df = pd.DataFrame(flattened_data)
        
        # 尝试将所有列转换为数值型 (忽略错误)
        for col in df.columns:
            # 跳过明显的非数值列
            if "name" in col or "id" in col or "date" in col or "note" in col or "description" in col or "code" in col:
                continue
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
            
        return df

    def get_correlation_matrix(self, df):
        """计算数值列的相关性矩阵"""
        # 选择数值类型的列
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return pd.DataFrame()
        return numeric_df.corr()

    def clean_data(self, df, strategy="mean"):
        """数据清洗：处理缺失值"""
        df_clean = df.copy()
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        
        if strategy == "mean":
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(df_clean[numeric_cols].mean())
        elif strategy == "zero":
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(0)
        elif strategy == "drop":
            df_clean = df_clean.dropna()
            
        return df_clean

    def normalize_data(self, df, columns=None):
        """数据标准化 (Z-score normalization)"""
        df_norm = df.copy()
        if columns is None:
            columns = df_norm.select_dtypes(include=[np.number]).columns
            
        for col in columns:
            if df_norm[col].std() != 0:
                df_norm[col] = (df_norm[col] - df_norm[col].mean()) / df_norm[col].std()
            else:
                df_norm[col] = 0
        return df_norm

    def prepare_ai_dataset(self, df, target_col, feature_cols=None, split_ratio=0.8):
        """准备AI训练数据集 (无需sklearn依赖)"""
        if target_col not in df.columns:
            return None, f"目标列 '{target_col}' 不存在"
        
        # 自动选择特征列
        if not feature_cols:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in numeric_cols if c != target_col]
        
        # 提取特征和目标
        X = df[feature_cols].copy()
        y = df[target_col].copy()
        
        # 简单清洗
        X = X.fillna(0)
        y = y.fillna(y.mean())
        
        # 划分训练集和测试集
        # 为了可复现，先排序（如果有时间字段最好，这里简单打乱）
        # 这里使用简单随机划分
        mask = np.random.rand(len(df)) < split_ratio
        
        X_train = X[mask]
        X_test = X[~mask]
        y_train = y[mask]
        y_test = y[~mask]
        
        dataset_info = {
            "features": feature_cols,
            "target": target_col,
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }
        
        return {
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test,
            "info": dataset_info
        }

    def generate_pytorch_code(self, feature_cols, target_col):
        """生成PyTorch Dataset代码示例"""
        code = f"""
import torch
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np

class PolyCarbDataset(Dataset):
    def __init__(self, csv_file, is_train=True):
        self.df = pd.read_csv(csv_file)
        
        # Features: {feature_cols}
        self.features = self.df[{feature_cols}].values.astype(np.float32)
        
        # Target: {target_col}
        self.target = self.df['{target_col}'].values.astype(np.float32)
        
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        return self.features[idx], self.target[idx]

# Usage
# dataset = PolyCarbDataset('train_data.csv')
# loader = DataLoader(dataset, batch_size=32, shuffle=True)
"""
        return code

    def generate_tensorflow_code(self, feature_cols, target_col):
        """生成TensorFlow/Keras代码示例"""
        code = f"""
import tensorflow as tf
import pandas as pd

def load_dataset(csv_file):
    df = pd.read_csv(csv_file)
    
    features = {feature_cols}
    target = '{target_col}'
    
    X = df[features].values
    y = df[target].values
    
    return X, y

# Usage
# X_train, y_train = load_dataset('train_data.csv')
# model = tf.keras.Sequential([
#     tf.keras.layers.Dense(64, activation='relu', input_shape=(len(features),)),
#     tf.keras.layers.Dense(1)
# ])
# model.compile(optimizer='adam', loss='mse')
# model.fit(X_train, y_train, epochs=100)
"""
        return code
