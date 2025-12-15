import os
from dotenv import load_dotenv

load_dotenv()  # 从.env加载变量

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')  # 用于session和表单安全
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')  # MySQL连接
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 优化性能