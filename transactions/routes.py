from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import json
from datetime import datetime
from sqlalchemy import or_
from extensions import db
from models import Item, User, Transaction
from utils.crypto import verify_signature
from utils.transaction_utils import construct_transaction_data_to_sign
from . import transactions_bp  # 从 __init__.py 导入蓝图

# 移除这行：transactions_bp = Blueprint('transactions', __name__, template_folder='../templates/transactions')

@transactions_bp.route('/initiate/<int:item_id>', methods=['GET', 'POST'])
@login_required
def initiate_transaction(item_id):
    item = Item.query.get_or_404(item_id)
    
    # 验证商品状态和所有权
    if item.seller == current_user:
        flash('您不能购买自己的商品。', 'warning')
        return redirect(url_for('items.item_detail', item_id=item.id))
    
    if item.is_sold:
        flash('该商品已售出，不可购买。', 'warning')
        return redirect(url_for('items.item_detail', item_id=item.id))
    
    if request.method == 'GET':
        # 处理GET请求 - 显示确认页面
        timestamp_str = datetime.utcnow().isoformat()
        data_to_sign_preview = construct_transaction_data_to_sign(
            item.id, item.title, item.price, 
            current_user.id, item.seller.id, timestamp_str
        )
        
        return render_template('initiate_transaction.html', 
                             item=item, 
                             data_to_sign_preview=data_to_sign_preview,
                             timestamp_str=timestamp_str,
                             buyer_public_key=current_user.public_key)
    
    elif request.method == 'POST':
        # 处理POST请求 - 核心交易逻辑
        try:
            # 从请求中获取签名数据
            if request.is_json:
                payload = request.get_json()
            else:
                signed_data_json = request.form.get('signed_data')
                if not signed_data_json:
                    return jsonify({'status': 'error', 'message': '缺少签名数据！'}), 400
                payload = json.loads(signed_data_json)
            
            original_data_str = payload.get('original_data_str')
            buyer_signature_b64 = payload.get('buyer_signature_b64')
            
            if not original_data_str or not buyer_signature_b64:
                return jsonify({'status': 'error', 'message': '签名数据不完整！'}), 400
            
            # 验证签名
            is_valid_signature = verify_signature(
                current_user.public_key, 
                buyer_signature_b64, 
                original_data_str.encode('utf-8')
            )
            
            if not is_valid_signature:
                return jsonify({'status': 'error', 'message': '签名验证失败！'}), 400
            
            # 创建交易记录
            transaction = Transaction(
                item_id=item.id,
                buyer_id=current_user.id,
                seller_id=item.seller.id,
                transaction_data=original_data_str,  # 修改字段名
                buyer_signature=buyer_signature_b64,
                status='initiated'
            )
            
            # 更新商品状态
            item.status = 'pending'
            
            # 提交到数据库
            db.session.add(transaction)
            db.session.commit()
            
            flash('交易已发起！等待卖家确认。', 'success')
            
            if request.is_json:
                return jsonify({
                    'status': 'success', 
                    'message': '交易已发起！',
                    'redirect_url': url_for('transactions.view_my_transactions')
                })
            else:
                return redirect(url_for('transactions.view_my_transactions'))
                
        except json.JSONDecodeError:
            return jsonify({'status': 'error', 'message': '无效的JSON数据！'}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'交易发起失败：{str(e)}'}), 500

@transactions_bp.route('/transaction/<int:transaction_id>/confirm_by_seller', methods=['POST'])
@login_required
def confirm_by_seller(transaction_id):
    """卖家确认交易"""
    # 查询交易
    transaction = Transaction.query.get_or_404(transaction_id)
    # 查询关联商品
    item = Item.query.get_or_404(transaction.item_id)
    
    # 权限检查 - 只有卖家能确认
    if item.seller != current_user:
        abort(403)
    
    # 状态检查 - 只能确认已发起的交易
    if transaction.status != 'initiated':
        flash('该交易无法被确认。', 'warning')
        return redirect(url_for('transactions.view_my_transactions'))
    
    # 更新交易状态
    transaction.status = 'confirmed_by_seller'
    transaction.updated_at = datetime.utcnow()
    
    # 更新商品状态 - 修复：使用正确的字段名
    item.is_sold = True  # 改为 is_sold = True
    item.updated_at = datetime.utcnow()
    
    # 提交到数据库
    db.session.commit()
    
    flash(f'交易 {transaction.id} 已确认，商品 {item.title} 已售出。', 'success')
    return redirect(url_for('transactions.view_my_transactions'))

@transactions_bp.route('/transaction/<int:transaction_id>/cancel_by_buyer', methods=['POST'])
@login_required
def cancel_by_buyer(transaction_id):
    """买家取消交易"""
    # 查询交易
    transaction = Transaction.query.get_or_404(transaction_id)
    # 查询关联商品
    item = Item.query.get_or_404(transaction.item_id)
    
    # 权限检查 - 只有买家能取消自己的交易
    if transaction.buyer_id != current_user.id:
        abort(403)
    
    # 状态检查 - 只能取消已发起的交易
    if transaction.status != 'initiated':
        flash('该交易无法被取消 (可能已被卖家确认或已取消)。', 'warning')
        return redirect(url_for('transactions.view_my_transactions'))
    
    # 更新交易状态
    transaction.status = 'cancelled_by_buyer'
    transaction.updated_at = datetime.utcnow()
    
    # 更新商品状态 - 重新上架
    item.status = 'available'
    item.updated_at = datetime.utcnow()
    
    # 提交到数据库
    db.session.commit()
    
    flash(f'交易 {transaction.id} 已被您取消。', 'success')
    return redirect(url_for('transactions.view_my_transactions'))

@transactions_bp.route('/transaction/<int:transaction_id>/cancel_by_seller', methods=['POST'])
@login_required
def cancel_by_seller(transaction_id):
    """卖家取消交易"""
    # 查询交易
    transaction = Transaction.query.get_or_404(transaction_id)
    # 查询关联商品
    item = Item.query.get_or_404(transaction.item_id)
    
    # 权限检查 - 只有卖家能取消与自己商品相关的交易
    if item.seller != current_user:
        abort(403)
    
    # 状态检查 - 只能取消已发起的交易
    if transaction.status != 'initiated':
        flash('该交易无法被取消 (可能已被您确认或已被买家取消)。', 'warning')
        return redirect(url_for('transactions.view_my_transactions'))
    
    # 更新交易状态
    transaction.status = 'cancelled_by_seller'
    transaction.updated_at = datetime.utcnow()
    
    # 更新商品状态 - 重新上架
    item.status = 'available'
    item.updated_at = datetime.utcnow()
    
    # 提交到数据库
    db.session.commit()
    
    flash(f'交易 {transaction.id} 已被您取消，商品 {item.title} 已重新上架。', 'success')
    return redirect(url_for('transactions.view_my_transactions'))

@transactions_bp.route('/my_transactions')
@login_required
def view_my_transactions():
    """查看我的交易记录"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    
    # 查询当前用户相关的交易（作为买家或卖家）
    user_transactions = Transaction.query.join(
        Item, Transaction.item_id == Item.id
    ).filter(
        or_(Transaction.buyer_id == current_user.id, 
            Transaction.seller_id == current_user.id)
    ).order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('my_transactions.html', 
                         title='我的交易', 
                         transactions=user_transactions)