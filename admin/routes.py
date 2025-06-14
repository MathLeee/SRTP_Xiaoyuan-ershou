from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models import User, Item, Transaction, Conversation, Message
from . import admin_bp
from sqlalchemy import func
from datetime import datetime, timedelta

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('需要管理员权限才能访问此页面。', 'error')
            return redirect(url_for('index'))  # 修改这里，从 'main.index' 改为 'index'
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """管理员仪表板"""
    # 统计数据
    total_users = User.query.count()
    total_items = Item.query.count()
    total_transactions = Transaction.query.count()
    total_messages = Message.query.count()
    
    # 最近7天的用户注册数
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= seven_days_ago).count()
    
    # 最近发布的商品
    recent_items = Item.query.order_by(Item.created_at.desc()).limit(5).all()
    
    # 最近的交易
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_items=total_items,
                         total_transactions=total_transactions,
                         total_messages=total_messages,
                         new_users_week=new_users_week,
                         recent_items=recent_items,
                         recent_transactions=recent_transactions)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """用户管理"""
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """切换用户管理员状态"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能修改自己的管理员状态'})
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = '管理员' if user.is_admin else '普通用户'
    return jsonify({'success': True, 'message': f'用户 {user.username} 已设置为{status}'})

@admin_bp.route('/items')
@login_required
@admin_required
def manage_items():
    """商品管理"""
    page = request.args.get('page', 1, type=int)
    items = Item.query.order_by(Item.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/items.html', items=items)

@admin_bp.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_item(item_id):
    """删除商品"""
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': f'商品 "{item.title}" 已删除'})

@admin_bp.route('/transactions')
@login_required
@admin_required
def manage_transactions():
    """交易管理"""
    page = request.args.get('page', 1, type=int)
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/transactions.html', transactions=transactions)

@admin_bp.route('/messages')
@login_required
@admin_required
def manage_messages():
    """消息管理"""
    page = request.args.get('page', 1, type=int)
    conversations = Conversation.query.order_by(Conversation.updated_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    # 计算总消息数
    total_messages = Message.query.count()
    
    return render_template('admin/messages.html', 
                         conversations=conversations, 
                         total_messages=total_messages)

@admin_bp.route('/conversations/<int:conversation_id>/details')
@login_required
@admin_required
def get_conversation_details(conversation_id):
    """获取对话详情"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # 获取该对话的所有消息
    messages = Message.query.filter(
        ((Message.sender_id == conversation.user1_id) & (Message.receiver_id == conversation.user2_id)) |
        ((Message.sender_id == conversation.user2_id) & (Message.receiver_id == conversation.user1_id))
    ).filter(
        Message.item_id == conversation.item_id
    ).order_by(Message.created_at.asc()).all()
    
    # 构建响应数据
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'sender_name': message.sender.username,
            'sender_id': message.sender_id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_read': message.is_read
        })
    
    conversation_data = {
        'id': conversation.id,
        'user1': {
            'id': conversation.user1_id,
            'username': conversation.user1.username
        },
        'user2': {
            'id': conversation.user2_id,
            'username': conversation.user2.username
        },
        'item': {
            'id': conversation.item.id if conversation.item else None,
            'title': conversation.item.title if conversation.item else '商品已删除',
            'price': float(conversation.item.price) if conversation.item else 0
        } if conversation.item else None,
        'created_at': conversation.created_at.strftime('%Y-%m-%d %H:%M'),
        'updated_at': conversation.updated_at.strftime('%Y-%m-%d %H:%M'),
        'messages': messages_data,
        'message_count': len(messages_data)
    }
    
    return jsonify({
        'success': True,
        'conversation': conversation_data
    })

@admin_bp.route('/conversations/<int:conversation_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_conversation(conversation_id):
    """删除对话"""
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # 删除相关的消息
    Message.query.filter(
        ((Message.sender_id == conversation.user1_id) & (Message.receiver_id == conversation.user2_id)) |
        ((Message.sender_id == conversation.user2_id) & (Message.receiver_id == conversation.user1_id))
    ).filter(
        Message.item_id == conversation.item_id
    ).delete()
    
    # 删除对话
    db.session.delete(conversation)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'对话 #{conversation_id} 已删除'
    })

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """删除用户"""
    user = User.query.get_or_404(user_id)
    
    # 防止删除自己
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己的账户'})
    
    # 防止删除其他管理员（可选的安全措施）
    if user.is_admin:
        return jsonify({'success': False, 'message': '不能删除管理员账户'})
    
    try:
        # 删除用户相关的数据
        # 1. 删除用户发布的商品
        for item in user.items:
            # 删除商品相关的交易记录
            Transaction.query.filter_by(item_id=item.id).delete()
            # 删除商品图片文件（如果有）
            if item.image_filename:
                import os
                image_path = os.path.join(current_app.root_path, 'static/uploads', item.image_filename)
                try:
                    os.remove(image_path)
                except OSError:
                    pass  # 文件不存在或无法删除，继续执行
            db.session.delete(item)
        
        # 2. 删除用户作为买家的交易记录
        Transaction.query.filter_by(buyer_id=user.id).delete()
        
        # 3. 删除用户的消息记录
        Message.query.filter(
            (Message.sender_id == user.id) | (Message.receiver_id == user.id)
        ).delete()
        
        # 4. 删除用户参与的对话
        Conversation.query.filter(
            (Conversation.user1_id == user.id) | (Conversation.user2_id == user.id)
        ).delete()
        
        # 5. 最后删除用户
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'用户 "{username}" 及其相关数据已删除'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除用户时发生错误: {str(e)}'})