from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import request # 获取页码，支持分页显示
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='guest')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# ==================== 文物属性表（category,dynasty,等） ====================

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    

class Dynasty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    

class MotifAndPattern(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)

class ObjectType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    

class FormAndStructure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(256), nullable=False)

# ==================== 博物馆表 ====================
class Museum(db.Model):
    __tablename__ = 'museum'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    
    # 一对多：一个博物馆有多个文物
    artifacts = db.relationship('Artifact', backref='museum', lazy='dynamic')

    def __repr__(self):
        return f'<Museum {self.name}>'

# ==================== 主文物表 ====================

class Artifact(db.Model):
    __tablename__ = 'artifact'
    id = db.Column(db.Integer, primary_key=True)

    # 博物馆不能随意删除（有文物时禁止删除）
    museum_id = db.Column(
        db.Integer,
        db.ForeignKey('museum.id', ondelete='RESTRICT'),  # 禁止删除有文物的博物馆
        nullable=False
    )
    
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)            # 台北特有
    
   # 分类属性：删除对应记录后，自动设为 NULL（文物保留，但失去分类）
    category_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='SET NULL'))
    dynasty_id = db.Column(db.Integer, db.ForeignKey('dynasty.id', ondelete='SET NULL'))
    image_id = db.Column(db.Integer, db.ForeignKey('image.id', ondelete='SET NULL'))
    motif_id = db.Column(db.Integer, db.ForeignKey('motif_and_pattern.id', ondelete='SET NULL'))
    object_type_id = db.Column(db.Integer, db.ForeignKey('object_type.id', ondelete='SET NULL'))
    form_structure_id = db.Column(db.Integer, db.ForeignKey('form_and_structure.id', ondelete='SET NULL'))

    # 关系
    category = db.relationship('Category', backref='artifacts')
    dynasty = db.relationship('Dynasty', backref='artifacts')
    image = db.relationship('Image', backref='artifacts')
    motif = db.relationship('MotifAndPattern', backref='artifacts')
    object_type = db.relationship('ObjectType', backref='artifacts')
    form_structure = db.relationship('FormAndStructure', backref='artifacts')

    def __repr__(self):
        return f'<Artifact {self.name} ({self.museum.name if self.museum else "未知来源"})>'
    



# ==================== 操作日志表 ====================



class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    table_name = db.Column(db.String(50), nullable=False)       # 如 'Artifact', 'Category'
    record_id = db.Column(db.Integer, nullable=True)            # 对应表格的id，如category,id
    
    action = db.Column(db.String(255), nullable=False)           # 'create', 'update', 'delete'
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    # 用户被删除时RESTRICT（防止丢失操作人信息）
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False)
    user = db.relationship('User', backref='logs')

    def __repr__(self):
        return f'<Log {self.action} {self.table_name}#{self.record_id} by {self.user.username if self.user else "unknown"}>'