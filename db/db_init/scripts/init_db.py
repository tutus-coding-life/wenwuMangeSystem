# 执行建表SQL
import pymysql
import os
from config.mysql_config import MYSQL_CONFIG

def execute_create_tables():
    # 计算 sql 文件的绝对路径
    current_dir = os.path.dirname(__file__)
    sql_path = os.path.join(current_dir, "../sql/create_tables.sql")
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cur:
            # 读取整个 SQL 文件
            with open(sql_path, "r", encoding="utf8") as f:
                sql_content = f.read()
            
            # 按分号分割多条语句，并过滤空语句
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            # 逐条执行
            for statement in statements:
                cur.execute(statement)
        
        conn.commit()
        print("所有表结构创建成功！（共执行 {} 条 CREATE TABLE 语句）".format(len(statements)))
    
    except Exception as e:
        conn.rollback()
        print(f"建表失败：{e}")
        print("请检查 MySQL 用户权限、数据库是否存在，或 SQL 语法是否有误。")
    
    finally:
        conn.close()

if __name__ == "__main__":
    execute_create_tables()