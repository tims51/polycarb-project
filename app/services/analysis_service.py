
"""
Analysis Service Module
Handles data analysis, DataFrame conversion, and AI preparation.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Union
from services.data_service import DataService

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for data analysis and AI preparation."""
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Recursively flatten nested dictionaries."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def get_data_as_dataframe(self, data_type: str = "concrete") -> pd.DataFrame:
        """
        Get data of specified type and convert to flattened DataFrame.
        
        Args:
            data_type: 'concrete', 'mortar', 'paste', 'product', 'synthesis'
        """
        data = []
        try:
            if data_type == "concrete":
                data = self.data_service.get_all_concrete_experiments()
            elif data_type == "mortar":
                data = self.data_service.get_all_mortar_experiments()
            elif data_type == "paste":
                data = self.data_service.get_all_paste_experiments()
            elif data_type == "product":
                data = self.data_service.get_all_products()
            elif data_type == "synthesis":
                data = self.data_service.get_all_synthesis_records()
            
            if not data:
                return pd.DataFrame()

            # Flatten nested structures
            flattened_data = [self._flatten_dict(record) for record in data]
            df = pd.DataFrame(flattened_data)
            
            # Convert numeric columns
            for col in df.columns:
                # Skip non-numeric columns based on name heuristics
                if any(x in col for x in ["name", "id", "date", "note", "description", "code"]):
                    continue
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass
                
            return df
            
        except Exception as e:
            logger.error(f"Error converting data to DataFrame: {e}")
            return pd.DataFrame()

    def get_correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix for numeric columns."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return pd.DataFrame()
        return numeric_df.corr()

    def clean_data(self, df: pd.DataFrame, strategy: str = "mean") -> pd.DataFrame:
        """Clean data by handling missing values."""
        df_clean = df.copy()
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        
        if strategy == "mean":
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(df_clean[numeric_cols].mean())
        elif strategy == "zero":
            df_clean[numeric_cols] = df_clean[numeric_cols].fillna(0)
        elif strategy == "drop":
            df_clean = df_clean.dropna()
            
        return df_clean

    def normalize_data(self, df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """Normalize data (Z-score)."""
        df_norm = df.copy()
        if columns is None:
            columns = df_norm.select_dtypes(include=[np.number]).columns.tolist()
            
        for col in columns:
            if col in df_norm.columns:
                if df_norm[col].std() != 0:
                    df_norm[col] = (df_norm[col] - df_norm[col].mean()) / df_norm[col].std()
                else:
                    df_norm[col] = 0
        return df_norm

    def prepare_ai_dataset(self, df: pd.DataFrame, target_col: str, feature_cols: Optional[List[str]] = None, split_ratio: float = 0.8) -> Union[Dict[str, Any], tuple]:
        """Prepare dataset for AI training."""
        if target_col not in df.columns:
            return None, f"Target column '{target_col}' not found"
        
        # Auto-select features if not provided
        if not feature_cols:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in numeric_cols if c != target_col]
        
        X = df[feature_cols].copy()
        y = df[target_col].copy()
        
        # Simple cleaning
        X = X.fillna(0)
        y = y.fillna(y.mean())
        
        # Split
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

    def generate_pytorch_code(self, feature_cols: List[str], target_col: str) -> str:
        """Generate PyTorch Dataset code snippet."""
        return f"""
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

    def generate_tensorflow_code(self, feature_cols: List[str], target_col: str) -> str:
        """Generate TensorFlow/Keras code snippet."""
        return f"""
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
