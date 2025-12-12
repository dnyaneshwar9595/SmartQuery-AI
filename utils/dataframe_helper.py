import pandas as pd
from typing import Dict, List, Any

def dict_to_dataframe(data_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert dictionary back to DataFrame
    
    Args:
        data_dict: Dictionary with columns and data
        
    Returns:
        pandas DataFrame
    """
    if not data_dict or not data_dict.get('columns') or not data_dict.get('data'):
        return pd.DataFrame()
    
    df = pd.DataFrame(data_dict['data'], columns=data_dict['columns'])
    
    # Optionally restore dtypes if needed
    if 'dtypes' in data_dict:
        for col, dtype in data_dict['dtypes'].items():
            try:
                if dtype.startswith('float'):
                    df[col] = df[col].astype(float)
                elif dtype.startswith('int'):
                    df[col] = df[col].astype(int)
            except:
                pass  # Keep original dtype if conversion fails
    
    return df