from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from models import db

app = Flask(__name__) # 创建flask应用实例
app.config.from_object(Config) #加载配置

db.init_app(app) # 绑定数据库
migrate = Migrate(app, db)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 未登录时重新路由到/login

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

from routes import *  # 导入路由

if __name__ == '__main__':
    app.run(debug=True)  # 调试模式，显示错误