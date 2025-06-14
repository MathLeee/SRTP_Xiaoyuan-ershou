from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
import os
from extensions import db
from models import Item
from forms import ItemForm
from utils.file_utils import save_item_picture
from . import items_bp  # 从 __init__.py 导入蓝图

# 移除这行：items_bp = Blueprint('items', __name__, template_folder='../templates/items')

@items_bp.route('/browse')
def browse_items():
    """浏览所有可用商品"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    
    # 查询所有可用商品，按发布时间降序排列，并分页
    items = Item.query.filter_by(is_sold=False).order_by(Item.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('browse.html', 
                         title='浏览商品', 
                         items=items)

@items_bp.route('/item/<int:item_id>')
def item_detail(item_id):
    """商品详情页面"""
    # 根据ID查询商品，如果不存在则返回404
    item = Item.query.get_or_404(item_id)
    
    return render_template('item_detail.html', 
                         title=item.title, 
                         item=item)

@items_bp.route('/my_items')
@login_required
def my_items():
    """我的商品页面"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    
    # 查询当前用户发布的所有商品，按发布时间降序排列，并分页
    user_items = Item.query.filter_by(seller=current_user).order_by(Item.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('my_items.html', 
                         title='我的商品', 
                         items=user_items)

@items_bp.route('/item/new', methods=['GET', 'POST'])
@login_required
def post_item():
    """发布新商品"""
    form = ItemForm()
    
    if form.validate_on_submit():
        # 处理图片上传
        picture_filename = None
        if form.image_file.data:
            picture_filename = save_item_picture(form.image_file.data)
        
        # 创建商品对象
        item = Item(
            title=form.title.data,
            description=form.description.data,
            price=form.price.data,
            image_filename=picture_filename,
            seller=current_user
        )
        
        # 保存到数据库
        db.session.add(item)
        db.session.commit()
        
        flash('商品已成功发布！', 'success')
        return redirect(url_for('items.item_detail', item_id=item.id))
    
    return render_template('post_item.html', 
                         title='发布新商品', 
                         form=form, 
                         legend='发布新商品')

@items_bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """编辑商品"""
    # 查询商品
    item = Item.query.get_or_404(item_id)
    
    # 权限检查：只有商品所有者才能编辑
    if item.seller != current_user:
        abort(403)
    
    form = ItemForm()
    
    if form.validate_on_submit():
        # 处理图片上传
        if form.image_file.data:
            picture_filename = save_item_picture(form.image_file.data)
            # 可以考虑删除旧图片
            if item.image_filename:
                old_image_path = os.path.join(current_app.root_path, 'static/uploads', item.image_filename)
                try:
                    os.remove(old_image_path)
                except OSError as e:
                    print(f"Error deleting old image {old_image_path}: {e}")
            item.image_filename = picture_filename
        
        # 更新商品信息
        item.title = form.title.data
        item.description = form.description.data
        item.price = form.price.data
        
        # 提交更改
        db.session.commit()
        
        flash('商品信息已更新！', 'success')
        return redirect(url_for('items.item_detail', item_id=item.id))
    
    # GET请求：预填充表单
    elif request.method == 'GET':
        form.title.data = item.title
        form.description.data = item.description
        form.price.data = item.price
    
    return render_template('post_item.html', 
                         title='编辑商品', 
                         form=form, 
                         legend=f'编辑商品: {item.title}',
                         item=item)

@items_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    """删除商品"""
    # 查询商品
    item = Item.query.get_or_404(item_id)
    
    # 权限检查：只有商品所有者才能删除
    if item.seller != current_user:
        abort(403)
    
    # 删除关联的图片文件
    if item.image_filename:
        image_path = os.path.join(current_app.root_path, 'static/uploads', item.image_filename)
        try:
            os.remove(image_path)
        except OSError as e:
            print(f"Error deleting image {image_path}: {e}")
    
    # 从数据库删除商品
    db.session.delete(item)
    db.session.commit()
    
    flash('商品已成功删除！', 'success')
    return redirect(url_for('items.my_items'))