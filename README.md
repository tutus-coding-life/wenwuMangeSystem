# wenwuMangeSystem
数据库大作业
## 环境配置
mysql创建数据库
```
CREATE DATABASE artifact_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
创建激活虚拟环境：
```
python -m venv venv
venv\Scripts\activate
```
安装依赖：
```
pip install -r requirement.txt
```
设置flask环境变量
```
set FLASK_APP=app.py
set FLASK_ENV=development
```
.env文件修改
```DATABASE_URL=mysql://root:密码@localhost/artifact_db  # 替换密码```
## 初始化数据库
```
flask db init
flask db migrate
flask db upgrade
```
## 启动项目

```
flask run
```
