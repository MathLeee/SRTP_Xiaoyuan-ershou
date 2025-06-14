from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import or_, and_
from extensions import db
from models import Message, Conversation, Item, User
from forms import MessageForm
from . import messages_bp  # 从 __init__.py 导入蓝图

# 移除蓝图定义行（如果存在的话）

@messages_bp.route('/conversations')
@login_required
def conversations():
    """显示用户的所有对话列表"""
    # 获取当前用户的所有对话
    user_conversations = Conversation.query.filter(
        or_(Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    # 获取每个对话的未读消息数
    conversations_data = []
    for conv in user_conversations:
        other_user = conv.get_other_user(current_user.id)
        unread_count = Message.query.filter(
            Message.sender_id == other_user.id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        ).count()
        
        conversations_data.append({
            'conversation': conv,
            'other_user': other_user,
            'unread_count': unread_count
        })
    
    return render_template('messages/conversations.html', 
                         title='我的消息', 
                         conversations=conversations_data)

@messages_bp.route('/conversation/<int:user_id>')
@messages_bp.route('/conversation/<int:user_id>/<int:item_id>')
@login_required
def conversation(user_id, item_id=None):
    """显示与特定用户的对话"""
    other_user = User.query.get_or_404(user_id)
    item = Item.query.get(item_id) if item_id else None
    
    # 查找或创建对话
    conversation = Conversation.query.filter(
        or_(
            and_(Conversation.user1_id == current_user.id, Conversation.user2_id == user_id),
            and_(Conversation.user1_id == user_id, Conversation.user2_id == current_user.id)
        )
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user1_id=min(current_user.id, user_id),
            user2_id=max(current_user.id, user_id),
            item_id=item_id
        )
        db.session.add(conversation)
        db.session.commit()
    
    # 获取对话中的所有消息
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    
    # 标记接收到的消息为已读
    Message.query.filter(
        Message.sender_id == user_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    
    return render_template('messages/conversation.html',
                 title=f'与 {other_user.username} 的对话',
                 other_user=other_user,
                     item=item,
                     messages=messages,
                     conversation=conversation)

@messages_bp.route('/send_message', methods=['POST'])
@login_required
def send_message():
    """发送消息"""
    receiver_id = request.form.get('receiver_id', type=int)
    content = request.form.get('content', '').strip()
    item_id = request.form.get('item_id', type=int)
    
    if not receiver_id or not content:
        flash('消息内容不能为空', 'error')
        return redirect(request.referrer or url_for('messages.conversations'))
    
    if receiver_id == current_user.id:
        flash('不能给自己发送消息', 'error')
        return redirect(request.referrer or url_for('messages.conversations'))
    
    # 创建消息
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        item_id=item_id,
        content=content
    )
    db.session.add(message)
    
    # 更新或创建对话
    conversation = Conversation.query.filter(
        or_(
            and_(Conversation.user1_id == current_user.id, Conversation.user2_id == receiver_id),
            and_(Conversation.user1_id == receiver_id, Conversation.user2_id == current_user.id)
        )
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user1_id=min(current_user.id, receiver_id),
            user2_id=max(current_user.id, receiver_id),
            item_id=item_id
        )
        db.session.add(conversation)
    
    db.session.flush()  # 获取message.id
    conversation.last_message_id = message.id
    conversation.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('消息发送成功', 'success')
    return redirect(url_for('messages.conversation', user_id=receiver_id, item_id=item_id))

@messages_bp.route('/api/unread_count')
@login_required
def unread_count():
    """获取未读消息数量（API接口）"""
    count = Message.query.filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).count()
    return jsonify({'unread_count': count})