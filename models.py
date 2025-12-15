from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()  # 数据库实例

class User(db.Model, UserMixin):  # 用户表
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='guest')  # 'admin' or 'guest'

    def set_password(self, password):  # 安全哈希密码
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):  # 验证密码
        return check_password_hash(self.password_hash, password)

class Category(db.Model):  # 类别表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

class Dynasty(db.Model):  # 朝代表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

class Image(db.Model):  # 图片表
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(256), nullable=False)

class MotifAndPattern(db.Model):  # 图案标签表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)

class ObjectType(db.Model):  # 对象类型标签表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)

class FormAndStructure(db.Model):  # 形式结构标签表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)

class ArtifactBeijing(db.Model):  # 北京文物表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    number = db.Column(db.String(64))
    dynasty_id = db.Column(db.Integer, db.ForeignKey('dynasty.id'))
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    motif_id = db.Column(db.Integer, db.ForeignKey('motif_and_pattern.id'))
    object_type_id = db.Column(db.Integer, db.ForeignKey('object_type.id'))
    form_structure_id = db.Column(db.Integer, db.ForeignKey('form_and_structure.id'))
    category = db.relationship('Category', backref='beijing_artifacts')
    dynasty = db.relationship('Dynasty', backref='beijing_artifacts')
    image = db.relationship('Image', backref='beijing_artifacts')
    motif = db.relationship('MotifAndPattern', backref='beijing_artifacts')
    object_type = db.relationship('ObjectType', backref='beijing_artifacts')
    form_structure = db.relationship('FormAndStructure', backref='beijing_artifacts')

class ArtifactTaipei(db.Model):  # 台北文物表
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    dynasty_id = db.Column(db.Integer, db.ForeignKey('dynasty.id'))
    description = db.Column(db.Text)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))
    motif_id = db.Column(db.Integer, db.ForeignKey('motif_and_pattern.id'))
    object_type_id = db.Column(db.Integer, db.ForeignKey('object_type.id'))
    form_structure_id = db.Column(db.Integer, db.ForeignKey('form_and_structure.id'))
    category = db.relationship('Category', backref='taipei_artifacts')
    dynasty = db.relationship('Dynasty', backref='taipei_artifacts')
    image = db.relationship('Image', backref='taipei_artifacts')
    motif = db.relationship('MotifAndPattern', backref='taipei_artifacts')
    object_type = db.relationship('ObjectType', backref='taipei_artifacts')
    form_structure = db.relationship('FormAndStructure', backref='taipei_artifacts')

class Log(db.Model):  # 日志表
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50))  # 操作表名
    action = db.Column(db.String(50))  # 操作类型
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))