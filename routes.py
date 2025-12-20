from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy.orm import joinedload
from app import app
from models import (
    db, User, ArtifactBeijing, ArtifactTaipei, Log,
    Category, Dynasty, Image,
    MotifAndPattern, ObjectType, FormAndStructure
)
from forms import (
    RegisterForm, LoginForm, EditProfileForm, UserForm,
    ArtifactBeijingForm, ArtifactTaipeiForm, LabelForm, ImportForm
)
import pandas as pd
import os

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
# 北京故宫文物管理
# ==============================

@app.route('/artifacts_beijing')
@login_required
def artifacts_beijing():
    # 获取分页参数，默认为第1页，每页20条
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 获取搜索参数
    search_name = request.args.get('search_name', '').strip()
    search_category = request.args.get('search_category', '').strip()
    search_dynasty = request.args.get('search_dynasty', '').strip()
    
    # 使用eager loading优化查询，避免N+1问题
    query = ArtifactBeijing.query.options(
        joinedload(ArtifactBeijing.category),
        joinedload(ArtifactBeijing.dynasty),
        joinedload(ArtifactBeijing.image),
        joinedload(ArtifactBeijing.motif),
        joinedload(ArtifactBeijing.object_type),
        joinedload(ArtifactBeijing.form_structure)
    )
    
    # 应用搜索条件
    if search_name:
        query = query.filter(ArtifactBeijing.name.like(f'%{search_name}%'))
    if search_category:
        query = query.join(Category).filter(Category.name.like(f'%{search_category}%'))
    if search_dynasty:
        query = query.join(Dynasty).filter(Dynasty.name.like(f'%{search_dynasty}%'))
    
    # 分页查询
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # 获取所有类别和朝代用于搜索下拉框
    categories = Category.query.order_by(Category.name).all()
    dynasties = Dynasty.query.order_by(Dynasty.name).all()
    
    return render_template('artifacts_beijing.html', 
                         artifacts=pagination.items,
                         pagination=pagination,
                         categories=categories,
                         dynasties=dynasties,
                         search_name=search_name,
                         search_category=search_category,
                         search_dynasty=search_dynasty)

@app.route('/admin/add_artifact_beijing', methods=['GET', 'POST'])
@login_required
def add_artifact_beijing():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = ArtifactBeijingForm()
    if form.validate_on_submit():
        _create_or_get_associated_records(form) # 添加不存在的属性值到关联表里，防止关联表属性为空，报错
        # 在表格中查询结果
        category = Category.query.filter_by(name=form.category.data).first()
        dynasty = Dynasty.query.filter_by(name=form.dynasty.data).first()
        image = Image.query.filter_by(url=form.image_url.data).first() if form.image_url.data else None
        motif = MotifAndPattern.query.filter_by(name=form.motif.data).first() if form.motif.data else None
        obj_type = ObjectType.query.filter_by(name=form.object_type.data).first() if form.object_type.data else None
        form_struct = FormAndStructure.query.filter_by(name=form.form_structure.data).first() if form.form_structure.data else None
        # 创建文物实体
        artifact = ArtifactBeijing(
            name=form.name.data,
            category_id=category.id,
            number=form.number.data,
            dynasty_id=dynasty.id,
            image_id=image.id if image else None,
            motif_id=motif.id if motif else None,
            object_type_id=obj_type.id if obj_type else None,
            form_structure_id=form_struct.id if form_struct else None
        )
        # 提交文物到数据库里
        db.session.add(artifact)
        db.session.commit()
        _add_log('ArtifactBeijing', 'add')
        flash('北京文物添加成功', 'success')
        return redirect(url_for('artifacts_beijing'))
    return render_template('artifact_form.html', form=form, title='添加北京文物')

@app.route('/admin/edit_artifact_beijing/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artifact_beijing(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    # 根据url的id 去数据库查询这件文物
    artifact = ArtifactBeijing.query.get_or_404(id)
    form = ArtifactBeijingForm(obj=artifact)
    if form.validate_on_submit():
        _create_or_get_associated_records(form)
        category = Category.query.filter_by(name=form.category.data).first()
        dynasty = Dynasty.query.filter_by(name=form.dynasty.data).first()
        image = Image.query.filter_by(url=form.image_url.data).first() if form.image_url.data else None
        motif = MotifAndPattern.query.filter_by(name=form.motif.data).first() if form.motif.data else None
        obj_type = ObjectType.query.filter_by(name=form.object_type.data).first() if form.object_type.data else None
        form_struct = FormAndStructure.query.filter_by(name=form.form_structure.data).first() if form.form_structure.data else None

        # 修改文物属性
        artifact.name = form.name.data
        artifact.category_id = category.id
        artifact.number = form.number.data
        artifact.dynasty_id = dynasty.id
        artifact.image_id = image.id if image else None
        artifact.motif_id = motif.id if motif else None
        artifact.object_type_id = obj_type.id if obj_type else None
        artifact.form_structure_id = form_struct.id if form_struct else None

        db.session.commit()
        _add_log('ArtifactBeijing', 'update')
        flash('北京文物修改成功', 'success')
        return redirect(url_for('artifacts_beijing'))
    return render_template('artifact_form.html', form=form, title='修改北京文物')

@app.route('/admin/delete_artifact_beijing/<int:id>', methods=['POST'])
@login_required
def delete_artifact_beijing(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    artifact = ArtifactBeijing.query.get_or_404(id)
    db.session.delete(artifact)
    db.session.commit()
    _add_log('ArtifactBeijing', 'delete')
    flash('北京文物删除成功', 'success')
    return redirect(url_for('artifacts_beijing'))

# ==============================
# 台北故宫文物管理
# ==============================

@app.route('/artifacts_taipei')
@login_required
def artifacts_taipei():
    # 获取分页参数，默认为第1页，每页20条
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # 获取搜索参数
    search_name = request.args.get('search_name', '').strip()
    search_category = request.args.get('search_category', '').strip()
    search_dynasty = request.args.get('search_dynasty', '').strip()
    
    # 使用eager loading优化查询，避免N+1问题
    query = ArtifactTaipei.query.options(
        joinedload(ArtifactTaipei.category),
        joinedload(ArtifactTaipei.dynasty),
        joinedload(ArtifactTaipei.image),
        joinedload(ArtifactTaipei.motif),
        joinedload(ArtifactTaipei.object_type),
        joinedload(ArtifactTaipei.form_structure)
    )
    
    # 应用搜索条件
    if search_name:
        query = query.filter(ArtifactTaipei.name.like(f'%{search_name}%'))
    if search_category:
        query = query.join(Category).filter(Category.name.like(f'%{search_category}%'))
    if search_dynasty:
        query = query.join(Dynasty).filter(Dynasty.name.like(f'%{search_dynasty}%'))
    
    # 分页查询
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # 获取所有类别和朝代用于搜索下拉框
    categories = Category.query.order_by(Category.name).all()
    dynasties = Dynasty.query.order_by(Dynasty.name).all()
    
    return render_template('artifacts_taipei.html', 
                         artifacts=pagination.items,
                         pagination=pagination,
                         categories=categories,
                         dynasties=dynasties,
                         search_name=search_name,
                         search_category=search_category,
                         search_dynasty=search_dynasty)

@app.route('/admin/add_artifact_taipei', methods=['GET', 'POST'])
@login_required
def add_artifact_taipei():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = ArtifactTaipeiForm()
    if form.validate_on_submit():
        _create_or_get_associated_records(form)
        category = Category.query.filter_by(name=form.category.data).first()
        dynasty = Dynasty.query.filter_by(name=form.dynasty.data).first()
        image = Image.query.filter_by(url=form.image_url.data).first() if form.image_url.data else None
        motif = MotifAndPattern.query.filter_by(name=form.motif.data).first() if form.motif.data else None
        obj_type = ObjectType.query.filter_by(name=form.object_type.data).first() if form.object_type.data else None
        form_struct = FormAndStructure.query.filter_by(name=form.form_structure.data).first() if form.form_structure.data else None

        artifact = ArtifactTaipei(
            name=form.name.data,
            category_id=category.id,
            dynasty_id=dynasty.id,
            description=form.description.data,
            image_id=image.id if image else None,
            motif_id=motif.id if motif else None,
            object_type_id=obj_type.id if obj_type else None,
            form_structure_id=form_struct.id if form_struct else None
        )
        db.session.add(artifact)
        db.session.commit()
        _add_log('ArtifactTaipei', 'add')
        flash('台北文物添加成功', 'success')
        return redirect(url_for('artifacts_taipei'))
    return render_template('artifact_form.html', form=form, title='添加台北文物')

@app.route('/admin/edit_artifact_taipei/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_artifact_taipei(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    artifact = ArtifactTaipei.query.get_or_404(id)
    form = ArtifactTaipeiForm(obj=artifact)
    if form.validate_on_submit():
        _create_or_get_associated_records(form)
        category = Category.query.filter_by(name=form.category.data).first()
        dynasty = Dynasty.query.filter_by(name=form.dynasty.data).first()
        image = Image.query.filter_by(url=form.image_url.data).first() if form.image_url.data else None
        motif = MotifAndPattern.query.filter_by(name=form.motif.data).first() if form.motif.data else None
        obj_type = ObjectType.query.filter_by(name=form.object_type.data).first() if form.object_type.data else None
        form_struct = FormAndStructure.query.filter_by(name=form.form_structure.data).first() if form.form_structure.data else None

        artifact.name = form.name.data
        artifact.category_id = category.id
        artifact.dynasty_id = dynasty.id
        artifact.description = form.description.data
        artifact.image_id = image.id if image else None
        artifact.motif_id = motif.id if motif else None
        artifact.object_type_id = obj_type.id if obj_type else None
        artifact.form_structure_id = form_struct.id if form_struct else None

        db.session.commit()
        _add_log('ArtifactTaipei', 'update')
        flash('台北文物修改成功', 'success')
        return redirect(url_for('artifacts_taipei'))
    return render_template('artifact_form.html', form=form, title='修改台北文物')

@app.route('/admin/delete_artifact_taipei/<int:id>', methods=['POST'])
@login_required
def delete_artifact_taipei(id):
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    artifact = ArtifactTaipei.query.get_or_404(id)
    db.session.delete(artifact)
    db.session.commit()
    _add_log('ArtifactTaipei', 'delete')
    flash('台北文物删除成功', 'success')
    return redirect(url_for('artifacts_taipei'))

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
        _add_log('User', 'add')
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
        _add_log('User', 'update')
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
    _add_log('User', 'delete')
    flash('用户删除成功', 'success')
    return redirect(url_for('users'))

# ==============================
# 图案标签管理（MotifAndPattern）
# ==============================

@app.route('/labels_motif')
@login_required
def labels_motif():
    labels = MotifAndPattern.query.all()
    return render_template('labels.html', items=labels, type='图案标签',
                           add_route='add_motif', edit_route='edit_motif', delete_route='delete_motif')

@app.route('/admin/add_motif', methods=['GET', 'POST'])
@login_required
def add_motif():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()
    if form.validate_on_submit():
        label = MotifAndPattern(name=form.name.data, description=form.description.data)
        db.session.add(label)
        db.session.commit()
        _add_log('MotifAndPattern', 'add')
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
        _add_log('MotifAndPattern', 'update')
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
    _add_log('MotifAndPattern', 'delete')
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
        label = ObjectType(name=form.name.data, description=form.description.data or '')
        db.session.add(label)
        db.session.commit()
        _add_log('ObjectType', 'add')
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
        label.description = form.description.data or ''
        db.session.commit()
        _add_log('ObjectType', 'update')
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
    _add_log('ObjectType', 'delete')
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
        label = FormAndStructure(name=form.name.data, description=form.description.data or '')
        db.session.add(label)
        db.session.commit()
        _add_log('FormAndStructure', 'add')
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
        label.description = form.description.data or ''
        db.session.commit()
        _add_log('FormAndStructure', 'update')
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
    _add_log('FormAndStructure', 'delete')
    flash('形式结构删除成功', 'success')
    return redirect(url_for('labels_form_structure'))

# ==============================
# 类别管理（category）
# ==============================

@app.route('/categories')
@login_required
def categories():
    items = Category.query.all()
    return render_template('categories.html', items=items, type='类别',
                           add_route='add_category', edit_route='edit_category', delete_route='delete_category')

@app.route('/admin/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    if current_user.role != 'admin':
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = LabelForm()  # 复用LabelForm，只用name字段
    if form.validate_on_submit():
        item = Category(name=form.name.data)
        db.session.add(item)
        db.session.commit()
        _add_log('Category', 'add')
        flash('类别添加成功', 'success')
        return redirect(url_for('categories'))
    return render_template('label_form.html', form=form, title='添加类别')

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
        _add_log('Category', 'update')
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
    _add_log('Category', 'delete')
    flash('类别删除成功', 'success')
    return redirect(url_for('categories'))

# ==============================
# 朝代管理（Dynasty）
# ==============================

@app.route('/dynasties')
@login_required
def dynasties():
    items = Dynasty.query.all()
    return render_template('dynasties.html', items=items, type='朝代',
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
        _add_log('Dynasty', 'add')
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
        _add_log('Dynasty', 'update')
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
    _add_log('Dynasty', 'delete')
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
        flash('无权限', 'error')
        return redirect(url_for('index'))
    form = ImportForm()
    if form.validate_on_submit():
        if form.type.data == 'beijing':
            file_path = 'data/beijing.xlsx'
            model = ArtifactBeijing
            extra_fields = {'number': 'Number'}
        else:
            file_path = 'data/taiwan.xlsx'
            model = ArtifactTaipei
            extra_fields = {'description': 'Description'}

        if not os.path.exists(file_path):
            flash(f'excel 文件不存在：{file_path}', 'error')
            return redirect(url_for('import_data'))

        df = pd.read_excel(file_path)
        count = 0
        for _, row in df.iterrows():
            # 处理类别
            category_name = row['Category'] if 'Category' in row else '未知类别'
            if pd.isna(category_name):
                category_name = '未知类别'
            category = Category.query.filter_by(name=category_name).first() or Category(name=category_name)

            # 处理朝代
            dynasty_name = row['Dynasty'] if 'Dynasty' in row else '未知朝代'
            if pd.isna(dynasty_name):
                dynasty_name = '未知朝代'
            dynasty = Dynasty.query.filter_by(name=dynasty_name).first() or Dynasty(name=dynasty_name)

            # 处理图片
            image_url = row['Image'] if 'Image' in row and pd.notna(row['Image']) else None
            image = Image(url=image_url) if image_url else None

            # 北京特有
            number = row['Number'] if 'Number' in row and pd.notna(row['Number']) else None

            # 台北特有
            description = row['Description'] if 'Description' in row and pd.notna(row['Description']) else None

            db.session.add_all([category, dynasty])
            if image:
                db.session.add(image)
            db.session.commit()

            if form.type.data == 'beijing':
                artifact = ArtifactBeijing(
                    name=row['Name'],
                    category_id=category.id,
                    number=number,
                    dynasty_id=dynasty.id,
                    image_id=image.id if image else None
                )
            else:
                artifact = ArtifactTaipei(
                    name=row['Name'],
                    category_id=category.id,
                    dynasty_id=dynasty.id,
                    description=description,
                    image_id=image.id if image else None
                )
            db.session.add(artifact)
            db.session.commit()
            count += 1

        flash(f'成功导入 {count} 条{ "北京" if form.type.data == "beijing" else "台北" }文物', 'success')
        _add_log('Import', f'csv_import_{form.type.data}')
        return redirect(url_for('index'))
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
        m = MotifAndPattern.query.filter_by(name=form.motif.data).first() or MotifAndPattern(name=form.motif.data, description='')
        db.session.add(m)
    if form.object_type.data:
        o = ObjectType.query.filter_by(name=form.object_type.data).first() or ObjectType(name=form.object_type.data, description='')
        db.session.add(o)
    if form.form_structure.data:
        f = FormAndStructure.query.filter_by(name=form.form_structure.data).first() or FormAndStructure(name=form.form_structure.data, description='')
        db.session.add(f)
    db.session.commit()

def _add_log(table_name, action):
    """统一添加操作日志"""
    log = Log(table_name=table_name, action=action, user_id=current_user.id)
    db.session.add(log)
    db.session.commit()