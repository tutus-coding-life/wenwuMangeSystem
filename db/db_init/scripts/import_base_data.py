# 导入基础数据
import pymysql
import hashlib
from config.mysql_config import MYSQL_CONFIG


def hash_password(password: str) -> str:
    """
    使用 SHA256 对密码进行哈希（与后续登录验证保持一致）
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_admin_user():
    """
    仅初始化一个管理员账号：
    username: admin
    password: admin123
    role: admin
    """
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cur:
            admin_username = "admin"
            admin_password = "admin123"  # 明文密码，实际存储哈希值
            admin_role = "admin"

            # 检查是否已存在该用户
            cur.execute("SELECT id FROM user WHERE username = %s", (admin_username,))
            if cur.fetchone():
                print(f"管理员账号 '{admin_username}' 已存在，无需重复创建。")
                return

            # 插入新管理员
            password_hash = hash_password(admin_password)
            cur.execute("""
                INSERT INTO user (username, password_hash, role)
                VALUES (%s, %s, %s)
            """, (admin_username, password_hash, admin_role))

        conn.commit()
        print("管理员账号初始化成功！")
        print("   用户名: admin")
        print("   密码: admin123")
        print("   角色: admin")
        print("   请登录后及时修改密码。")

    except Exception as e:
        conn.rollback()
        print(f"初始化管理员账号失败：{e}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_admin_user()