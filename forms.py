from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, Optional
from models import Museum, Location, StorageRoom, ExhibitionHall

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
    # 位置选择模式：已有 or 新建
    location_mode = SelectField('位置方式', choices=[('existing', '使用已有位置'), ('new', '新建位置')], validators=[DataRequired()])
    existing_location_id = SelectField('已有位置', coerce=int, validators=[Optional()])
    # 新建位置时可填写库房名和/或展厅名（至少填写一项）
    new_storage_name = StringField('库房名称', validators=[Optional(), Length(max=256)])
    new_exhibition_name = StringField('展厅名称', validators=[Optional(), Length(max=256)])
    description = TextAreaField('描述')
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(ArtifactForm, self).__init__(*args, **kwargs)
        # 加载已有位置选项：先显示未选择
        choices = [(0, '请选择已有位置')]
        locations = Location.query.order_by(Location.id).all()
        for loc in locations:
            label = ''
            if loc.type == 'storage' and loc.storage_room:
                label = f'库房: {loc.storage_room.position}'
            elif loc.type == 'exhibition' and loc.exhibition_hall:
                label = f'展厅: {loc.exhibition_hall.position}'
            elif loc.type == 'both':
                parts = []
                if loc.storage_room: parts.append(f'库房:{loc.storage_room.position}')
                if loc.exhibition_hall: parts.append(f'展厅:{loc.exhibition_hall.position}')
                label = ' / '.join(parts) if parts else f'位置 {loc.id}'
            else:
                label = f'位置 {loc.id}'
            choices.append((loc.id, label))
        self.existing_location_id.choices = choices

class LabelForm(FlaskForm):  
    name = StringField('名称', validators=[DataRequired()])
    submit = SubmitField('保存')


class LocationForm(FlaskForm):
    storage_room_id = SelectField('库房', coerce=int, validators=[Optional()])
    exhibition_hall_id = SelectField('展厅', coerce=int, validators=[Optional()])
    type = SelectField('类型', choices=[('', '请选择'), ('storage', '库房'), ('exhibition', '展厅')], validators=[DataRequired()])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(LocationForm, self).__init__(*args, **kwargs)
        # 填充库房选项
        sr_choices = [(0, '不指定')]
        for sr in StorageRoom.query.order_by(StorageRoom.id).all():
            sr_choices.append((sr.id, sr.position))
        self.storage_room_id.choices = sr_choices

        # 填充展厅选项
        eh_choices = [(0, '不指定')]
        for eh in ExhibitionHall.query.order_by(ExhibitionHall.id).all():
            eh_choices.append((eh.id, eh.position))
        self.exhibition_hall_id.choices = eh_choices

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