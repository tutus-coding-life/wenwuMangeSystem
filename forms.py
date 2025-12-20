from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, Optional
from models import Museum

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

class ArtifactForm(FlaskForm):
    name = StringField('名称', validators=[DataRequired()])
    category = StringField('类别', validators=[DataRequired()])
    dynasty = StringField('朝代', validators=[DataRequired()])
    image_url = StringField('图片URL')
    motif = StringField('图案', validators=[Optional()])
    object_type = StringField('对象类型', validators=[Optional()])
    form_structure = StringField('形式结构', validators=[Optional()])
    description = TextAreaField('描述')
    submit = SubmitField('保存')

class LabelForm(FlaskForm):  
    name = StringField('名称', validators=[DataRequired()])
    submit = SubmitField('保存')

class ImportForm(FlaskForm):
    museum_id = SelectField(
        '选择博物馆',
        coerce=int,
        validators=[DataRequired()]
    )
    new_museum_name = StringField('新博物馆名称', validators=[Optional()])

    file = FileField('上传 Excel 文件（可选）', validators=[Optional()])
    submit = SubmitField('开始导入')

    def __init__(self, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        museums = Museum.query.order_by(Museum.name).all()
        choices = [(m.id, f"{m.name}") for m in museums]
        choices.insert(0, (-1, '新建博物馆'))
        self.museum_id.choices = choices

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if self.museum_id.data == -1:
            if not self.new_museum_name.data or not self.new_museum_name.data.strip():
                self.new_museum_name.errors.append('请输入新博物馆名称')
                return False
            existing = Museum.query.filter_by(name=self.new_museum_name.data.strip()).first()
            if existing:
                self.new_museum_name.errors.append('该博物馆名称已存在')
                return False
        return True