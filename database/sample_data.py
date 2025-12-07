import pandas as pd

def get_dummy_athena_output():
    """
    Simulates the output from your friend's Athena query node
    This is what you'll receive as input
    """
    # Example 1: Category aggregation (good for pie/bar chart)
    data1 = {
        'columns': ['category', 'total_price'],
        'data': [
            ['Clothing', 157.89],
            ['Groceries', 21.46],
            ['Sports', 265.37],
            ['Electronics', 541.41]
        ],
        'dtypes': {'category': 'object', 'total_price': 'float64'}
    }
    
    # Example 2: Time series data (good for line chart)
    data2 = {
        'columns': ['date', 'sales', 'profit'],
        'data': [
            ['2024-01-01', 1200, 300],
            ['2024-01-02', 1500, 400],
            ['2024-01-03', 1100, 250],
            ['2024-01-04', 1800, 500],
            ['2024-01-05', 2000, 600],
            ['2024-01-06', 1700, 450],
            ['2024-01-07', 2200, 700]
        ],
        'dtypes': {'date': 'object', 'sales': 'int64', 'profit': 'int64'}
    }
    
    # Example 3: Scatter plot data (good for correlation)
    data3 = {
        'columns': ['price', 'rating', 'category'],
        'data': [
            [157.89, 4.08, 'Clothing'],
            [21.46, 3.87, 'Groceries'],
            [265.37, 3.46, 'Sports'],
            [541.41, 4.14, 'Electronics'],
            [89.99, 4.5, 'Clothing'],
            [45.50, 3.2, 'Groceries'],
            [199.99, 4.8, 'Sports'],
            [399.99, 3.9, 'Electronics'],
            [120.00, 4.2, 'Clothing'],
            [15.99, 3.5, 'Groceries']
        ],
        'dtypes': {'price': 'float64', 'rating': 'float64', 'category': 'object'}
    }
    
    # Example 4: Brand comparison (good for horizontal bar)
    data4 = {
        'columns': ['brand', 'avg_rating', 'product_count'],
        'data': [
            ['Astra', 4.08, 15],
            ['NeoTech', 3.87, 22],
            ['Acme', 3.46, 18],
            ['Nimbus', 4.14, 12],
            ['TechCorp', 4.25, 20],
            ['GlobalBrand', 3.95, 25],
            ['MegaStore', 3.72, 30],
            ['PrimeMart', 4.35, 10],
            ['ValuePlus', 3.55, 28],
            ['QualityGoods', 4.50, 8],
            ['BudgetBuy', 3.20, 35],
            ['LuxuryLine', 4.60, 6]
        ],
        'dtypes': {'brand': 'object', 'avg_rating': 'float64', 'product_count': 'int64'}
    }
    
    # Return one of these (you can switch for testing)
    return data1  # Change to data2, data3, or data4 to test different charts