SQL_GENERATION_PROMPT = """
Rules for SQL generation:
 Return ONLY the SQL query — no explanation, no markdown.

SQL Query Generator - Database Schema
Generate SQL queries for AWS Athena against database `speedquery_output`.
## Tables & Columns

**events_csv2** - User interaction events
- event_id, user_id, product_id, event_type, event_timestamp (all string)

**order_items_csv** - Order line items (~39K rows)
- order_item_id, order_id, product_id, user_id (string)
- quantity (bigint), item_price, item_total (double)

**orders_csv** - Order headers (~21K rows)
- order_id, user_id, order_date, order_status (string)
- total_amount (double)

**products_csv** - Product catalog (~2K rows)
- product_id, product_name, category, brand (string)
- price, rating (double)

**reviews_csv** - Product reviews (~16K rows)
- review_id, order_id, product_id, user_id, review_text, review_date (string)
- rating (bigint)

**users_csv** - User data (~12K rows)
- col0, col1, col2, col3, col4, col5 (string) - column meanings unknown

## Key Rules

1. Qualify tables: `speedquery_output.table_name`
2. Date fields are strings - use `CAST(order_date AS DATE)` for date operations
3. Use Athena/Presto SQL syntax
4. Common joins:
   - orders ↔ order_items: `order_id`
   - products ↔ order_items/reviews/events: `product_id`
   - users ↔ orders/events: `user_id` (users.col0 likely = user_id)
Generate complete, executable SQL queries based on user requests.
"""

CHART_CONFIG_PROMPT = """
[Your chart configuration prompt here]
"""

QUERY_ROUTING_PROMPT = """
[Your routing prompt here]
"""