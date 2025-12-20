# backend/db_init/utils/common_sql.py
def get_pagination_sql(base_sql: str, page: int = 1, per_page: int = 20):
    """
    生成分页查询所需的 SQL 和参数

    Args:
        base_sql (str): 基础 SELECT 查询语句（不含 LIMIT/OFFSET，例如 "SELECT * FROM artifact_beijing WHERE ..."）
        page (int): 当前页码，默认 1
        per_page (int): 每页条数，默认 20

    Returns:
        tuple: (data_sql, count_sql, params)
            - data_sql: 带 LIMIT/OFFSET 的数据查询 SQL
            - count_sql: 统计总数的 SQL
            - params: (per_page, offset) 参数元组，用于参数化执行
    """
    # 参数安全处理
    page = max(1, int(page))          # 防止页码 <=0 或非整数
    per_page = max(1, min(int(per_page), 1000))  # 限制最大每页条数，避免滥用

    offset = (page - 1) * per_page

    data_sql = f"{base_sql.strip()} LIMIT %s OFFSET %s"
    count_sql = f"SELECT COUNT(*) AS total FROM ({base_sql.strip()}) AS sub"

    return data_sql, count_sql, (per_page, offset)