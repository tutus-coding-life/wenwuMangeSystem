import pandas as pd
import pymysql
import os
from config.mysql_config import MYSQL_CONFIG

# 数据文件夹路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")

def get_or_create_id(cur, table: str, name_col: str, value):
    """
    查询名称对应的 ID，不存在则插入后返回新 ID
    """
    if not value or pd.isna(value):
        return None
    value = str(value).strip()
    if value == "" or value.lower() == "nan":
        return None

    # 查询是否存在
    cur.execute(f"SELECT id FROM {table} WHERE {name_col} = %s", (value,))
    row = cur.fetchone()
    if row:
        return row['id']

    # 不存在则插入
    cur.execute(f"INSERT INTO {table} ({name_col}) VALUES (%s)", (value,))
    cur.execute(f"SELECT id FROM {table} WHERE {name_col} = %s", (value,))
    return cur.fetchone()['id']


def insert_images(cur, artifact_id: int, artifact_type: str, image_urls, descriptions=None):
    """
    插入图片到 image 表（支持单图或多图列表）
    """
    if not image_urls:
        return

    # 统一转为列表
    urls = [image_urls] if isinstance(image_urls, str) else image_urls
    if descriptions and isinstance(descriptions, str):
        descs = [descriptions]
    elif descriptions:
        descs = list(descriptions)
    else:
        descs = []

    for i, url in enumerate(urls):
        url_str = str(url).strip()
        if not url_str or url_str.lower() == "nan" or pd.isna(url):
            continue
        desc = descs[i] if i < len(descs) else None
        is_primary = 1 if i == 0 else 0

        cur.execute("""
            INSERT INTO image (artifact_id, artifact_type, url, description, is_primary)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            url = VALUES(url), description = VALUES(description), is_primary = VALUES(is_primary)
        """, (artifact_id, artifact_type, url_str, desc, is_primary))


def import_all_excel():
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cur:
            print("=== 开始批量导入所有 Excel 数据 ===")

            # 每个文件的配置：文件名、目标表、文物类型、列映射
            files_config = [
                # 台北故宫
                {
                    "file": "taiwan.xlsx",
                    "table": "artifact_taipei",
                    "type": "taipei",
                    "mapping": {
                        "name_col": "Name",
                        "category_col": "Category",
                        "dynasty_col": "Dynasty",
                        "description_col": "Description",
                        "image_col": "Image"
                    }
                },
                # 北京故宫
                {
                    "file": "beijing.xlsx",
                    "table": "artifact_beijing",
                    "type": "beijing",
                    "mapping": {
                        "name_col": "Name",
                        "category_col": "Category",
                        "dynasty_col": "Dynasty",
                        "number_col": "Number",
                        "image_col": "Image"
                    }
                },
                # 湖南省博物馆数据（统一导入北京库）
                {
                    "file": "漆器.xlsx",
                    "table": "artifact_beijing",
                    "type": "beijing",
                    "mapping": {
                        "name_col": "Name",
                        "category_col": "Category",
                        "dynasty_col": "Dynasty",
                        "description_col": "Description",
                        "image_col": "Image"
                    }
                },
                {
                    "file": "玉石.xlsx",
                    "table": "artifact_beijing",
                    "type": "beijing",
                    "mapping": {
                        "name_col": "Name",
                        "category_col": "Category",
                        "dynasty_col": "Dynasty",
                        "description_col": "Description",
                        "image_col": "Image"
                    }
                },
                {
                    "file": "金属.xlsx",
                    "table": "artifact_beijing",
                    "type": "beijing",
                    "mapping": {
                        "name_col": "Name",
                        "category_col": "Category",
                        "dynasty_col": "Dynasty",
                        "description_col": "Description",
                        "image_col": "Image"
                    }
                },
                {
                    "file": "陶瓷.xlsx",
                    "table": "artifact_beijing",
                    "type": "beijing",
                    "mapping": {
                        "name_col": "Name",
                        "category_col": "Category",
                        "dynasty_col": "Dynasty",
                        "description_col": "Description",
                        "image_col": "Image"
                    }
                },
            ]

            total_artifacts = 0

            for cfg in files_config:
                file_path = os.path.join(DATA_DIR, cfg["file"])
                if not os.path.exists(file_path):
                    print(f"【警告】文件不存在，跳过：{cfg['file']}")
                    continue

                print(f"\n正在处理：{cfg['file']} → {cfg['table']} ({cfg['type']})")
                df = pd.read_excel(file_path)

                # 跳过空表
                if df.empty:
                    print("  文件为空，跳过")
                    continue

                print(f"  共读取 {len(df)} 行数据")

                mapping = cfg["mapping"]
                imported = 0

                for idx, row in df.iterrows():
                    # 文物名称（必填）
                    name = row.get(mapping["name_col"])
                    if pd.isna(name) or str(name).strip() == "":
                        continue

                    name = str(name).strip()

                    # 类别与朝代（自动创建）
                    category_name = row.get(mapping.get("category_col"))
                    dynasty_name = row.get(mapping.get("dynasty_col"))

                    category_id = get_or_create_id(cur, "category", "name", category_name)
                    dynasty_id = get_or_create_id(cur, "dynasty", "name", dynasty_name)

                    # 编号（仅北京有）
                    number = row.get(mapping.get("number_col")) if "number_col" in mapping else None
                    if pd.isna(number):
                        number = None
                    else:
                        number = str(number).strip()

                    # 描述
                    description = row.get(mapping.get("description_col")) if "description_col" in mapping else None
                    if pd.isna(description):
                        description = None

                    # 插入或更新文物记录
                    insert_sql = f"""
                        INSERT INTO {cfg['table']}
                        (name, category_id, dynasty_id, number, description)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        category_id = VALUES(category_id),
                        dynasty_id = VALUES(dynasty_id),
                        number = VALUES(number),
                        description = VALUES(description)
                    """
                    cur.execute(insert_sql, (name, category_id, dynasty_id, number, description))

                    # 获取 artifact_id
                    cur.execute(f"SELECT id FROM {cfg['table']} WHERE name = %s LIMIT 1", (name,))
                    artifact_id = cur.fetchone()['id']

                    # 插入图片
                    if "image_col" in mapping:
                        image_url = row.get(mapping["image_col"])
                        image_desc = description  # 使用描述作为图片说明（可优化）
                        insert_images(cur, artifact_id, cfg["type"], image_url, image_desc)

                    imported += 1
                    if (idx + 1) % 100 == 0:
                        print(f"    已处理 {idx + 1} 行...")

                conn.commit()
                print(f"  → 完成！本文件导入/更新 {imported} 件文物")
                total_artifacts += imported

            print(f"\n=== 所有文件导入完成！总计处理 {total_artifacts} 件文物 ===")
            print("   • 台北故宫文物 → artifact_taipei")
            print("   • 北京故宫 + 湖南省博物馆文物 → artifact_beijing")
            print("   • 所有图片已插入 image 表")
            print("   • 类别与朝代已自动补充到 category / dynasty 表")

    except Exception as e:
        conn.rollback()
        print(f"\n【错误】导入过程中发生异常：{e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    import_all_excel()