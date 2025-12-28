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
pip install -r requirements.txt 
```
或使用清华源安装
 ```
# 激活虚拟环境后，执行这条命令（自动用清华源安装）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --default-timeout=1000
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
保持启动状态，然后打开浏览器访问http://localhost:5000/
(可能是http://127.0.0.1:5000)
