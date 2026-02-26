import pandas as pd
from typing import Dict, List, Any

def dict_to_dataframe(data_dict: Dict[str, Any]) -> pd.DataFrame:
    
    # if not data_dict or not data_dict.get('columns') or not data_dict.get('data'):
    #     return pd.DataFrame()
    
    df = pd.DataFrame(data_dict['data'], columns=data_dict['columns'])
    
    return df