from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, Optional

class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('密码', validators=[DataRequired()])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class EditProfileForm(FlaskForm):
    password = PasswordField('新密码', validators=[DataRequired()])
    confirm_password = PasswordField('确认新密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('保存修改')

class UserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('密码', validators=[Optional()])
    role = SelectField('角色', choices=[('guest', '游客'), ('admin', '管理员')])
    submit = SubmitField('保存')

class ArtifactBeijingForm(FlaskForm):
    name = StringField('名称', validators=[DataRequired()])
    category = StringField('类别', validators=[DataRequired()])
    number = StringField('编号')
    dynasty = StringField('朝代', validators=[DataRequired()])
    image_url = StringField('图片URL')
    motif = StringField('图案', validators=[Optional()])
    object_type = StringField('对象类型', validators=[Optional()])
    form_structure = StringField('形式结构', validators=[Optional()])
    submit = SubmitField('保存')

class ArtifactTaipeiForm(FlaskForm):
    name = StringField('名称', validators=[DataRequired()])
    category = StringField('类别', validators=[DataRequired()])
    dynasty = StringField('朝代', validators=[DataRequired()])
    description = TextAreaField('描述')
    image_url = StringField('图片URL')
    motif = StringField('图案', validators=[Optional()])
    object_type = StringField('对象类型', validators=[Optional()])
    form_structure = StringField('形式结构', validators=[Optional()])
    submit = SubmitField('保存')

class LabelForm(FlaskForm):  # 标签/类别/朝代通用
    name = StringField('名称', validators=[DataRequired()])
    description = TextAreaField('描述', validators=[Optional()])
    submit = SubmitField('保存')

class ImportForm(FlaskForm):
    type = SelectField('类型', choices=[('beijing', '北京故宫'), ('taipei', '台北故宫')])
    submit = SubmitField('导入')  # 固定路径导入，为简单不上传文件