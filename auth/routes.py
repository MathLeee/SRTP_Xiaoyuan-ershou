from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt
from models import User
from auth.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm, AccountSettingsForm
from utils.crypto import generate_rsa_keys
from utils.mail_utils import send_reset_email  # 正确导入邮件工具
import io
from . import auth_bp  # 从 __init__.py 导入蓝图

# 移除这行：auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # 生成RSA密钥对
        private_key_pem, public_key_pem = generate_rsa_keys()  # 修改这里：函数名改为 generate_rsa_keys
        
        # 哈希密码
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # 创建新用户
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            public_key=public_key_pem
        )
        
        # 保存到数据库
        db.session.add(user)
        db.session.commit()
        
        # 将私钥存储在会话中，供下载
        session['private_key'] = private_key_pem
        session['username'] = user.username
        
        flash('注册成功！请下载并安全保存您的私钥。', 'success')
        return redirect(url_for('auth.download_private_key'))
    
    return render_template('auth/register.html', title='注册', form=form)

@auth_bp.route('/download_private_key')
def download_private_key():
    if 'private_key' not in session:
        flash('没有可下载的私钥。', 'error')
        return redirect(url_for('auth.register'))
    
    private_key = session['private_key']
    username = session.get('username', 'user')
    
    # 创建文件对象
    file_data = io.BytesIO(private_key.encode('utf-8'))
    
    # 清除会话中的私钥
    session.pop('private_key', None)
    session.pop('username', None)
    
    return send_file(
        file_data,
        as_attachment=True,
        download_name=f'{username}_private_key.pem',
        mimetype='application/x-pem-file'
    )

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))  # Changed from 'main.index' to 'index'
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('index'))  # Changed from 'main.index' to 'index'
            next_page = request.args.get('next')
            flash('登录成功！', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('登录失败，请检查邮箱和密码。', 'danger')
    
    return render_template('auth/login.html', title='登录', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # 生成重置令牌
            token = user.get_reset_token()
            
            # 发送重置邮件
            if send_reset_email(user, token):
                flash('密码重置邮件已发送，请检查您的邮箱。', 'info')
            else:
                flash('邮件发送失败，请稍后重试或联系管理员。', 'error')
        else:
            # 即使用户不存在，也显示相同消息以防止邮箱枚举攻击
            flash('如果该邮箱已注册，您将收到密码重置邮件。', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', title='忘记密码', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('无效或已过期的重置令牌。', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # 哈希新密码
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # 更新用户密码
        user.password_hash = hashed_password
        db.session.commit()
        
        flash('您的密码已更新！现在可以登录了。', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='重置密码', form=form)

@auth_bp.route('/account_settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    form = AccountSettingsForm()
    
    if form.validate_on_submit():
        # 更新用户信息
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # 如果用户输入了新密码，则更新密码
        if form.password.data:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            current_user.password_hash = hashed_password
        
        db.session.commit()
        flash('账户设置已更新！', 'success')
        return redirect(url_for('auth.account_settings'))
    
    # 预填充表单
    form.username.data = current_user.username
    form.email.data = current_user.email
    
    return render_template('auth/account_settings.html', title='账户设置', form=form)

# 删除重复的 send_reset_email 函数定义（第145-160行左右）