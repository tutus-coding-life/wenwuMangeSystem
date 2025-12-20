from flask import render_template, redirect, url_for, flash, request,abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from app import app
from models import (
    db, User, Artifact, Museum, Log,
    Category, Dynasty, Image,
    MotifAndPattern, ObjectType, FormAndStructure,
    StorageRoom, ExhibitionHall, Location
)
from forms import (
    RegisterForm, LoginForm, EditProfileForm, UserForm,
    ArtifactForm,  LabelForm, ImportForm, LocationForm
)
import pandas as pd
import os

# 上下文处理，每一次渲染模板前自动把变量注入到所有模板的上下文里。
@app.context_processor
def inject_museums():
    return {'museums': Museum.query.order_by(Museum.name).all()}

# ==============================
# 基础路由
# ==============================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在', 'error')
            return redirect(url_for('register'))
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        user.role = 'guest'  # 默认游客
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('登录成功', 'success')
            return redirect(url_for('index'))
        flash('用户名或密码错误', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已注销', 'success')
    return redirect(url_for('index'))

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        db.session.commit()
        flash('密码修改成功', 'success')
        return redirect(url_for('index'))
    return render_template('edit_profile.html', form=form)

# ==============================
# 文物管理
# ==============================
@app.route('/artifacts/<int:museum_id>')
@login_required
def artifacts(museum_id):
    page = request.args.get('page', 1, type=int)
    
    # 获取筛选参数
    category_id = request.args.get('category', type=int)
    dynasty_id = request.args.get('dynasty', type=int)
    motif_id = request.args.get('motif', type=int)
    object_type_id = request.args.get('object_type', type=int)
    form_structure_id = request.args.get('form_structure', type=int)

    # 基础查询：该博物馆的所有文物
    query = Artifact.query.filter_by(museum_id=museum_id)

    # 应用筛选
    if category_id:
        query = query.filter(Artifact.category_id == category_id)
    if dynasty_id:
        query = query.filter(Artifact.dynasty_id == dynasty_id)
    if motif_id:
        query = query.filter(Artifact.motif_id == motif_id)
    if object_type_id:
        query = query.filter(Artifact.object_type_id == object_type_id)
    if form_structure_id:
        query = query.filter(Artifact.form_structure_id == form_structure_id)

    # 排序（推荐按名称）
    query = query.order_by(Artifact.name)

    pagination = query.paginate(page=page, per_page=21, error_out=False)

    # 获取筛选选项（仅显示该博物馆实际拥有的属性值）
    museum_artifacts = Artifact.query.filter_by(museum_id=museum_id).all()

    categories = sorted({a.category for a in museum_artifacts if a.category}, key=lambda x: x.name)
    dynasties = sorted({a.dynasty for a in museum_artifacts if a.dynasty}, key=lambda x: x.name)
    motifs = sorted({a.motif for a in museum_artifacts if a.motif}, key=lambda x: x.name)
    object_types = sorted({a.object_type for a in museum_artifacts if a.object_type}, key=lambda x: x.name)
    form_structures = sorted({a.form_structure for a in museum_artifacts if a.form_structure}, key=lambda x: x.name)

    museum = Museum.query.get_or_404(museum_id)

    return render_template(
        'artifacts.html',
        museum=museum,
        artifacts=pagination.items,
        pagination=pagination,
        categories=categories,
        dynasties=dynasties,
        motifs=motifs,
        object_types=object_types,
        form_structures=form_structures,
        # 当前筛选值，用于高亮选中
        selected_category=category_id,
        selected_dynasty=dynasty_id,
        selected_motif=motif_id,
        selected_object_type=object_type_id,
        selected_form_structure=form_structure_id
    )

@app.route('/artifact/add/<int:museum_id>', methods=['GET', 'POST'])
@login_required
def add_artifact(museum_id):
    if current_user.role != 'admin':
        flash('无权限访问', 'danger')
        return redirect(url_for('index'))

    museum = Museum.query.get_or_404(museum_id)

    form = ArtifactForm()

    if form.validate_on_submit():
        # 自动创建或获取关联记录
        _create_or_get_associated_records(form)

        category = Category.query.filter_by(name=form.category.data).first()
        dynasty = Dynasty.query.filter_by(name=form.dynasty.data).first()
        image = Image.query.filter_by(url=form.image_url.data).first() if form.image_url.data else None
        motif = MotifAndPattern.query.filter_by(name=form.motif.data).first() if form.motif.data else None
        obj_type = ObjectType.query.filter_by(name=form.object_type.data).first() if form.object_type.data else None
        form_struct = FormAndStructure.query.filter_by(name=form.form_structure.data).first() if form.form_structure.data else None

        # 处理位置：使用已有位置或新建位置
        chosen_location_id = None
        if getattr(form, 'location_mode', None) and form.location_mode.data == 'existing':
            # 使用已有位置
            if getattr(form, 'existing_location_id', None) and form.existing_location_id.data and form.existing_location_id.data != 0:
                chosen_location_id = form.existing_location_id.data
        else:
            # 新建位置：至少填写库房或展厅之一
            new_storage = getattr(form, 'new_storage_name', None) and form.new_storage_name.data and form.new_storage_name.data.strip()
            new_exhibition = getattr(form, 'new_exhibition_name', None) and form.new_exhibition_name.data and form.new_exhibition_name.data.strip()
            if new_storage or new_exhibition:
                sr_id = None
                eh_id = None
                if new_storage:
                    # 查找相同名称的库房，若不存在则新建
                    sr = StorageRoom.query.filter_by(position=new_storage.strip()).first()
                    if not sr:
                        sr = StorageRoom(position=new_storage.strip())
                        db.session.add(sr)
                        db.session.flush()
                    sr_id = sr.id
                if new_exhibition:
                    eh = ExhibitionHall.query.filter_by(position=new_exhibition.strip()).first()
                    if not eh:
                        eh = ExhibitionHall(position=new_exhibition.strip())
                        db.session.add(eh)
                        db.session.flush()
                    eh_id = eh.id
                # 创建 Location，type 根据填写情况设置
                loc_type = 'both' if sr_id and eh_id else ('storage' if sr_id else 'exhibition')
                loc = Location(storage_room_id=sr_id, exhibition_hall_id=eh_id, type=loc_type)
                db.session.add(loc)
                db.session.flush()
                chosen_location_id = loc.id

        # 创建通用 Artifact 实例
        artifact = Artifact(
            museum_id=museum_id,
            name=form.name.data,
            description=form.description.data or None,  # 台北特有字段，可为空
            category_id=category.id if category else None,
            dynasty_id=dynasty.id if dynasty else None,
            image_id=image.id if image else None,
            motif_id=motif.id if motif else None,
            object_type_id=obj_type.id if obj_type else None,
            form_structure_id=form_struct.id if form_struct else None,
            location_id=(chosen_location_id if chosen_location_id else None)
        )

        db.session.add(artifact)
        db.session.commit()

        flash(f'{museum.name} 文物添加成功', 'success')
        return redirect(url_for('artifacts', museum_id=museum_id))

    # GET 请求：显示表单
    return render_template(
        'artifact_form.html',
        form=form,
        title=f'添加 {museum.name} 文物',
        museum=museum
    )

@app.route('/artifact/edit/<int:museum_id>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artifact(museum_id, id):
    if current_user.role != 'admin':
        flash('无权限访问', 'danger')
        return redirect(url_for('index'))

    artifact = Artifact.query.get_or_404(id)
    if artifact.museum_id != museum_id:
        abort(403)  # 防止跨博物馆修改

    museum = Museum.query.get_or_404(museum_id)
    form = ArtifactForm(obj=artifact)  # 自动填充表单
    # 在 GET 请求时填充位置相关默认值
    if request.method == 'GET':
        if artifact.location:
            form.location_mode.data = 'existing'
            form.existing_location_id.data = artifact.location_id if artifact.location_id else 0
        else:
            form.location_mode.data = 'existing'
            form.existing_location_id.data = 0

    if form.validate_on_submit():
        _create_or_get_associated_records(form)

        category = Category.query.filter_by(name=form.category.data).first()
        dynasty = Dynasty.query.filter_by(name=form.dynasty.data).first()
        image = Image.query.filter_by(url=form.image_url.data).first() if form.image_url.data else None
        motif = MotifAndPattern.query.filter_by(name=form.motif.data).first() if form.motif.data else None
        obj_type = ObjectType.query.filter_by(name=form.object_type.data).first() if form.object_type.data else None
        form_struct = FormAndStructure.query.filter_by(name=form.form_structure.data).first() if form.form_structure.data else None

        # 处理位置（编辑时也支持选择已有或新建）
        chosen_location_id = None
        if getattr(form, 'location_mode', None) and form.location_mode.data == 'existing':
            if getattr(form, 'existing_location_id', None) and form.existing_location_id.data and form.existing_location_id.data != 0:
                chosen_location_id = form.existing_location_id.data
        else:
            new_storage = getattr(form, 'new_storage_name', None) and form.new_storage_name.data and form.new_storage_name.data.strip()
            new_exhibition = getattr(form, 'new_exhibition_name', None) and form.new_exhibition_name.data and form.new_exhibition_name.data.strip()
            if new_storage or new_exhibition:
                sr_id = None
                eh_id = None
                if new_storage:
                    sr = StorageRoom.query.filter_by(position=new_storage.strip()).first()
                    if not sr:
                        sr = StorageRoom(position=new_storage.strip())
                        db.session.add(sr)
                        db.session.flush()
                    sr_id = sr.id
                if new_exhibition:
                    eh = ExhibitionHall.query.filter_by(position=new_exhibition.strip()).first()
                    if not eh:
                        eh = ExhibitionHall(position=new_exhibition.strip())
                        db.session.add(eh)
                        db.session.flush()
                    eh_id = eh.id
                loc_type = 'both' if sr_id and eh_id else ('storage' if sr_id else 'exhibition')
                loc = Location(storage_room_id=sr_id, exhibition_hall_id=eh_id, type=loc_type)
                db.session.add(loc)
                db.session.flush()
                chosen_location_id = loc.id

        # 更新字段
        artifact.name = form.name.data
        artifact.description = form.description.data or None
        artifact.category_id = category.id if category else None
        artifact.dynasty_id = dynasty.id if dynasty else None
        artifact.image_id = image.id if image else None
        artifact.motif_id = motif.id if motif else None
        artifact.object_type_id = obj_type.id if obj_type else None
        artifact.form_structure_id = form_struct.id if form_struct else None
        artifact.location_id = (chosen_location_id if chosen_location_id else None)

        db.session.commit()

        flash(f'{museum.name} 文物修改成功', 'success')
        return redirect(url_for('artifacts', museum_id=museum_id))

    return render_template(
        'artifact_form.html',
        form=form,
        title=f'修改 {museum.name} 文物',
        museum=museum
    )

@app.route('/artifact/delete/<int:museum_id>/<int:id>', methods=['POST'])
@login_required
def delete_artifact(museum_id, id):
    if current_user.role != 'admin':
        flash('无权限', 'danger')
        return redirect(url_for('index'))

    artifact = Artifact.query.get_or_404(id)
    if artifact.museum_id != museum_id:
        abort(403)

    db.session.delete(artifact)
    db.session.commit()


    flash('文物删除成功', 'success')
    return redirect(url_for('artifacts', museum_id=museum_id))


# ==============================
# 用户管理
# ==============================

@app.route('/admin/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    users_list = User.query.all()
    return render_template('users.html', users=users_list)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = UserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在', 'error')
            return redirect(url_for('add_user'))
        user = User(username=form.username.data, role=form.role.data)
        if form.password.data:
            user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('用户添加成功', 'success')
        return redirect(url_for('users'))
    return render_template('user_form.html', form=form, title='添加用户')

@app.route('/admin/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first() and form.username.data != user.username:
            flash('用户名已存在', 'error')
            return redirect(url_for('edit_user', id=id))
        user.username = form.username.data
        user.role = form.role.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('用户修改成功', 'success')
        return redirect(url_for('users'))
    return render_template('user_form.html', form=form, title='修改用户')

@app.route('/admin/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    if id == current_user.id:
        flash('不能删除自己', 'error')
        return redirect(url_for('users'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('用户删除成功', 'success')
    return redirect(url_for('users'))

# ==============================
# 图案标签管理（MotifAndPattern）
# ==============================

@app.route('/labels_motif')
@login_required
def labels_motif():
    labels = MotifAndPattern.query.all()
    return render_template('labels.html', items=labels, type='MotifAndPattern',
                           add_route='add_motif', edit_route='edit_motif', delete_route='delete_motif')

@app.route('/admin/add_motif', methods=['GET', 'POST'])
@login_required
def add_motif():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()
    if form.validate_on_submit():
        label = MotifAndPattern(name=form.name.data)
        db.session.add(label)
        db.session.commit()
        flash('图案标签添加成功', 'success')
        return redirect(url_for('labels_motif'))
    return render_template('label_form.html', form=form, title='添加图案标签')

@app.route('/admin/edit_motif/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_motif(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    label = MotifAndPattern.query.get_or_404(id)
    form = LabelForm(obj=label)
    if form.validate_on_submit():
        label.name = form.name.data
        label.description = form.description.data
        db.session.commit()
        flash('图案标签修改成功', 'success')
        return redirect(url_for('labels_motif'))
    return render_template('label_form.html', form=form, title='修改图案标签')

@app.route('/admin/delete_motif/<int:id>', methods=['POST'])
@login_required
def delete_motif(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    label = MotifAndPattern.query.get_or_404(id)
    db.session.delete(label)
    db.session.commit()
    flash('图案标签删除成功', 'success')
    return redirect(url_for('labels_motif'))

# ==============================
# 对象类型管理（ObjectType）
# ==============================

@app.route('/labels_object_type')
@login_required
def labels_object_type():
    labels = ObjectType.query.all()
    return render_template('labels.html', items=labels, type='对象类型',
                           add_route='add_object_type', edit_route='edit_object_type', delete_route='delete_object_type')

@app.route('/admin/add_object_type', methods=['GET', 'POST'])
@login_required
def add_object_type():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()
    if form.validate_on_submit():
        label = ObjectType(name=form.name.data)
        db.session.add(label)
        db.session.commit()
        flash('对象类型添加成功', 'success')
        return redirect(url_for('labels_object_type'))
    return render_template('label_form.html', form=form, title='添加对象类型')

@app.route('/admin/edit_object_type/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_object_type(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    label = ObjectType.query.get_or_404(id)
    form = LabelForm(obj=label)
    if form.validate_on_submit():
        label.name = form.name.data
        db.session.commit()
        flash('对象类型修改成功', 'success')
        return redirect(url_for('labels_object_type'))
    return render_template('label_form.html', form=form, title='修改对象类型')

@app.route('/admin/delete_object_type/<int:id>', methods=['POST'])
@login_required
def delete_object_type(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    label = ObjectType.query.get_or_404(id)
    db.session.delete(label)
    db.session.commit()
    flash('对象类型删除成功', 'success')
    return redirect(url_for('labels_object_type'))

# ==============================
# 形式结构管理（FormAndStructure）
# ==============================

@app.route('/labels_form_structure')
@login_required
def labels_form_structure():
    labels = FormAndStructure.query.all()
    return render_template('labels.html', items=labels, type='形式结构',
                           add_route='add_form_structure', edit_route='edit_form_structure', delete_route='delete_form_structure')

@app.route('/admin/add_form_structure', methods=['GET', 'POST'])
@login_required
def add_form_structure():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()
    if form.validate_on_submit():
        label = FormAndStructure(name=form.name.data)
        db.session.add(label)
        db.session.commit()
        flash('形式结构添加成功', 'success')
        return redirect(url_for('labels_form_structure'))
    return render_template('label_form.html', form=form, title='添加形式结构')

@app.route('/admin/edit_form_structure/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_form_structure(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    label = FormAndStructure.query.get_or_404(id)
    form = LabelForm(obj=label)
    if form.validate_on_submit():
        label.name = form.name.data
        db.session.commit()
        flash('形式结构修改成功', 'success')
        return redirect(url_for('labels_form_structure'))
    return render_template('label_form.html', form=form, title='修改形式结构')

@app.route('/admin/delete_form_structure/<int:id>', methods=['POST'])
@login_required
def delete_form_structure(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    label = FormAndStructure.query.get_or_404(id)
    db.session.delete(label)
    db.session.commit()
    flash('形式结构删除成功', 'success')
    return redirect(url_for('labels_form_structure'))

# ==============================
# 类别管理（category）
# ==============================

@app.route('/categories')
@login_required
def categories():
    items = Category.query.all()
    return render_template('labels.html', items=items, type='Category',
                           add_route='add_category', edit_route='edit_category', delete_route='delete_category')

@app.route('/admin/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()  
    if form.validate_on_submit():
        item = Category(name=form.name.data)
        db.session.add(item)
        db.session.commit()
        flash('类别添加成功', 'success')
        return redirect(url_for('categories'))
    return render_template('label_form.html', form=form, title='添加类别')


# ==============================
# 展厅管理 (ExhibitionHall)
# ==============================

@app.route('/storage_rooms')
@login_required
def storage_rooms():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    items = StorageRoom.query.order_by(StorageRoom.id).all()
    return render_template('labels.html', items=items, type='库房',
                           add_route='add_storage_room', edit_route='edit_storage_room', delete_route='delete_storage_room')


@app.route('/admin/add_storage_room', methods=['GET', 'POST'])
@login_required
def add_storage_room():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()
    if form.validate_on_submit():
        item = StorageRoom(position=form.name.data)
        db.session.add(item)
        db.session.commit()
        flash('库房添加成功', 'success')
        return redirect(url_for('storage_rooms'))
    return render_template('label_form.html', form=form, title='添加库房')


@app.route('/admin/edit_storage_room/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_storage_room(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = StorageRoom.query.get_or_404(id)
    form = LabelForm()
    if request.method == 'GET':
        form.name.data = item.position
    if form.validate_on_submit():
        item.position = form.name.data
        db.session.commit()
        flash('库房修改成功', 'success')
        return redirect(url_for('storage_rooms'))
    return render_template('label_form.html', form=form, title='修改库房')


@app.route('/admin/delete_storage_room/<int:id>', methods=['POST'])
@login_required
def delete_storage_room(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = StorageRoom.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('库房删除成功', 'success')
    return redirect(url_for('storage_rooms'))


# ==============================
# 展厅管理 (ExhibitionHall)
# ==============================

@app.route('/exhibition_halls')
@login_required
def exhibition_halls():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    items = ExhibitionHall.query.order_by(ExhibitionHall.id).all()
    return render_template('labels.html', items=items, type='展厅',
                           add_route='add_exhibition_hall', edit_route='edit_exhibition_hall', delete_route='delete_exhibition_hall')


@app.route('/admin/add_exhibition_hall', methods=['GET', 'POST'])
@login_required
def add_exhibition_hall():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()
    if form.validate_on_submit():
        item = ExhibitionHall(position=form.name.data)
        db.session.add(item)
        db.session.commit()
        flash('展厅添加成功', 'success')
        return redirect(url_for('exhibition_halls'))
    return render_template('label_form.html', form=form, title='添加展厅')


@app.route('/admin/edit_exhibition_hall/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_exhibition_hall(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = ExhibitionHall.query.get_or_404(id)
    form = LabelForm()
    if request.method == 'GET':
        form.name.data = item.position
    if form.validate_on_submit():
        item.position = form.name.data
        db.session.commit()
        flash('展厅修改成功', 'success')
        return redirect(url_for('exhibition_halls'))
    return render_template('label_form.html', form=form, title='修改展厅')


@app.route('/admin/delete_exhibition_hall/<int:id>', methods=['POST'])
@login_required
def delete_exhibition_hall(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = ExhibitionHall.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('展厅删除成功', 'success')
    return redirect(url_for('exhibition_halls'))


# ==============================
# 位置管理 (Location)
# ==============================

@app.route('/locations')
@login_required
def locations():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    items = Location.query.order_by(Location.id).all()
    return render_template('locations.html', items=items)


@app.route('/admin/add_location', methods=['GET', 'POST'])
@login_required
def add_location():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LocationForm()
    if form.validate_on_submit():
        loc = Location(
            storage_room_id=(form.storage_room_id.data if form.storage_room_id.data and form.storage_room_id.data != 0 else None),
            exhibition_hall_id=(form.exhibition_hall_id.data if form.exhibition_hall_id.data and form.exhibition_hall_id.data != 0 else None),
            type=form.type.data
        )
        db.session.add(loc)
        db.session.commit()
        flash('位置添加成功', 'success')
        return redirect(url_for('locations'))
    return render_template('location_form.html', form=form, title='添加位置')


@app.route('/admin/edit_location/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_location(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    loc = Location.query.get_or_404(id)
    form = LocationForm()
    if request.method == 'GET':
        form.type.data = loc.type
        form.storage_room_id.data = loc.storage_room_id if loc.storage_room_id else 0
        form.exhibition_hall_id.data = loc.exhibition_hall_id if loc.exhibition_hall_id else 0
    if form.validate_on_submit():
        loc.storage_room_id = (form.storage_room_id.data if form.storage_room_id.data and form.storage_room_id.data != 0 else None)
        loc.exhibition_hall_id = (form.exhibition_hall_id.data if form.exhibition_hall_id.data and form.exhibition_hall_id.data != 0 else None)
        loc.type = form.type.data
        db.session.commit()
        flash('位置修改成功', 'success')
        return redirect(url_for('locations'))
    return render_template('location_form.html', form=form, title='修改位置')


@app.route('/admin/delete_location/<int:id>', methods=['POST'])
@login_required
def delete_location(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    loc = Location.query.get_or_404(id)
    db.session.delete(loc)
    db.session.commit()
    flash('位置删除成功', 'success')
    return redirect(url_for('locations'))

@app.route('/admin/edit_category/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = Category.query.get_or_404(id)
    form = LabelForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data
        db.session.commit()
        flash('类别修改成功', 'success')
        return redirect(url_for('categories'))
    return render_template('label_form.html', form=form, title='修改类别')

@app.route('/admin/delete_category/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = Category.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('类别删除成功', 'success')
    return redirect(url_for('categories'))

# ==============================
# 朝代管理（Dynasty）
# ==============================

@app.route('/dynasties')
@login_required
def dynasties():
    labels = Dynasty.query.all()
    return render_template('labels.html', items=labels, type='朝代',
                           add_route='add_dynasty', edit_route='edit_dynasty', delete_route='delete_dynasty')

@app.route('/admin/add_dynasty', methods=['GET', 'POST'])
@login_required
def add_dynasty():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()  # 复用 LabelForm，只用 name 字段
    if form.validate_on_submit():
        item = Dynasty(name=form.name.data)
        db.session.add(item)
        db.session.commit()
        flash('朝代添加成功', 'success')
        return redirect(url_for('dynasties'))
    return render_template('label_form.html', form=form, title='添加朝代')

@app.route('/admin/edit_dynasty/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_dynasty(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = Dynasty.query.get_or_404(id)
    form = LabelForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data
        db.session.commit()
        flash('朝代修改成功', 'success')
        return redirect(url_for('dynasties'))
    return render_template('label_form.html', form=form, title='修改朝代')

@app.route('/admin/delete_dynasty/<int:id>', methods=['POST'])
@login_required
def delete_dynasty(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    item = Dynasty.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('朝代删除成功', 'success')
    return redirect(url_for('dynasties'))

# ==============================
# 操作日志
# ==============================

@app.route('/admin/logs')
@login_required
def logs():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    logs_list = Log.query.order_by(Log.timestamp.desc()).all()
    return render_template('logs.html', logs=logs_list)

# ==============================
# CSV 导入
# ==============================

@app.route('/admin/import', methods=['GET', 'POST'])
@login_required
def import_data():
    if current_user.role != 'admin':
        flash('无权限访问', 'danger')
        return redirect(url_for('index'))

    form = ImportForm()

    if form.validate_on_submit():
        if form.museum_id.data == -1:
            # 新建博物馆
            museum_name = form.new_museum_name.data.strip()
            museum = Museum(name=museum_name)
            db.session.add(museum)
            db.session.flush()  # 获取 museum.id
            flash(f'创建新博物馆：{museum_name} (ID: {museum.id})', 'info')
            db.session.commit()
        else:
            # 使用已有博物馆
            museum = Museum.query.get_or_404(form.museum_id.data)

        # ============ 处理文件 ============
        if form.file.data:
            filename = secure_filename(form.file.data.filename)
            if not filename:
                flash('无效的文件名', 'error')
                return redirect(request.url)
            file_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            form.file.data.save(file_path)
        else:
            # 默认文件映射（可自行扩展）
            default_files = {
                '故宫博物院': 'data/beijing_museum.xlsx',
                '台北故宫博物院': 'data/taipei_museum.xlsx',
                '大英博物馆':'data/uk_museum.xlsx',
                '湖南省博物馆': 'data/hunan_museum.xlsx',
            }
            file_path = default_files.get(museum.name)
            if not file_path or not os.path.exists(file_path):
                flash(f'未找到 {museum.name} 的默认文件，请手动上传', 'warning')
                return redirect(request.url)

        # ============ 读取并导入数据 ============
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            flash(f'读取文件失败：{str(e)}', 'error')
            return redirect(request.url)

        count = 0
        for _, row in df.iterrows():
            try:
                # ========== 处理关联字段（自动创建或复用）==========

                category_name = row.get('Category', '未知类别')
                if pd.isna(category_name):
                    category_name = '未知类别'
                category = Category.query.filter_by(name=category_name).first() or Category(name=category_name)

                dynasty_name = row.get('Dynasty', '未知朝代')
                if pd.isna(dynasty_name):
                    dynasty_name = '未知朝代'
                dynasty = Dynasty.query.filter_by(name=dynasty_name).first() or Dynasty(name=dynasty_name)

                image_url = row.get('Image') if pd.notna(row.get('Image')) else None
                image = Image.query.filter_by(url=image_url).first() or (Image(url=image_url) if image_url else None)

                motif_name = row.get('MotifAndPattern') if pd.notna(row.get('MotifAndPattern')) else None
                motif = MotifAndPattern.query.filter_by(name=motif_name).first() or (MotifAndPattern(name=motif_name) if motif_name else None)

                obj_type_name = row.get('ObjectType') if pd.notna(row.get('ObjectType')) else None
                obj_type = ObjectType.query.filter_by(name=obj_type_name).first() or (ObjectType(name=obj_type_name) if obj_type_name else None)

                form_struct_name = row.get('FormAndStructure') if pd.notna(row.get('FormAndStructure')) else None
                form_struct = FormAndStructure.query.filter_by(name=form_struct_name).first() or (FormAndStructure(name=form_struct_name) if form_struct_name else None)

                # ========== 特殊字段 ==========
                description = row.get('Description') if pd.notna(row.get('Description')) else None

                # ========== 添加到会话 ==========
                db.session.add_all([category, dynasty])
                if image: db.session.add(image)
                if motif: db.session.add(motif)
                if obj_type: db.session.add(obj_type)
                if form_struct: db.session.add(form_struct)

                # ========== 创建 Artifact ==========
                artifact = Artifact(
                    museum_id=museum.id,
                    name=row['Name'],
                    description=description,
                    category_id=category.id,
                    dynasty_id=dynasty.id,
                    image_id=image.id if image else None,
                    motif_id=motif.id if motif else None,
                    object_type_id=obj_type.id if obj_type else None,
                    form_structure_id=form_struct.id if form_struct else None
                )

                db.session.add(artifact)
                count += 1
                if(count%50==0): db.session.commit()

            except Exception as e:
                db.session.rollback()
                flash(f'导入第 {count+1} 行失败：{str(e)}', 'warning')
                continue

        db.session.commit()
        flash(f'成功为【{museum.name}】导入 {count} 条文物', 'success')
        return redirect(url_for('artifacts', museum_id=museum.id))

    return render_template('import.html', form=form)

# ==============================
# 辅助函数
# ==============================

def _create_or_get_associated_records(form):
    """自动创建或获取关联记录（类别、朝代、图片、标签等）"""
    if form.category.data:
        cat = Category.query.filter_by(name=form.category.data).first() or Category(name=form.category.data)
        db.session.add(cat)
    if form.dynasty.data:
        dyn = Dynasty.query.filter_by(name=form.dynasty.data).first() or Dynasty(name=form.dynasty.data)
        db.session.add(dyn)
    if form.image_url.data:
        img = Image.query.filter_by(url=form.image_url.data).first() or Image(url=form.image_url.data)
        db.session.add(img)
    if form.motif.data:
        m = MotifAndPattern.query.filter_by(name=form.motif.data).first() or MotifAndPattern(name=form.motif.data)
        db.session.add(m)
    if form.object_type.data:
        o = ObjectType.query.filter_by(name=form.object_type.data).first() or ObjectType(name=form.object_type.data)
        db.session.add(o)
    if form.form_structure.data:
        f = FormAndStructure.query.filter_by(name=form.form_structure.data).first() or FormAndStructure(name=form.form_structure.data)
        db.session.add(f)
    db.session.commit()

from sqlalchemy.event import listens_for
from flask_login import current_user
from datetime import datetime

# ==============================
# 添加操作日志
# ==============================

@listens_for(db.session, 'before_flush')
def before_flush(session, flush_context, instances):
    models = {Artifact, Museum, Category, Dynasty, Image, 
                      MotifAndPattern, ObjectType, FormAndStructure, User}

    for instance in session.new:  
        if type(instance) in models:
            _auto_log(
                table_name=type(instance).__name__,
                record_id=instance.id,
                action='create'
            )

    for instance in session.dirty:  # 修改
        if type(instance) in models and session.is_modified(instance):
            _auto_log(
                table_name=type(instance).__name__,
                record_id=instance.id,
                action='update'
            )

    for instance in session.deleted:  # 删除
        if type(instance) in models:
            _auto_log(
                table_name=type(instance).__name__,
                record_id=instance.id,
                action='delete'
            )

def _auto_log(table_name: str, record_id: int, action: str):

    user_id = current_user.id if current_user.is_authenticated else None

    log = Log(
        table_name=table_name,
        record_id=record_id,
        action=action[:255], 
        user_id=user_id,
        timestamp=datetime.utcnow()
    )
    db.session.add(log)