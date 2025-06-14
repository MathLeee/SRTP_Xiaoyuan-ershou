from flask import current_app, url_for, request
from flask_mail import Message
from extensions import mail
from datetime import datetime
import socket
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

def send_reset_email(user, token):
    """
    发送密码重置邮件给用户
    
    Args:
        user: 用户对象
        token: 密码重置令牌
    """
    try:
        # 获取客户端信息（可选）
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '未知'))
        user_agent = request.environ.get('HTTP_USER_AGENT', '未知浏览器')
        
        # 生成重置链接
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        # 方法1：使用Flask-Mail
        try:
            msg = Message(
                '密码重置请求 - SRTP平台',
                sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                recipients=[user.email]
            )
            
            msg.body = f'''亲爱的 {user.username}，

您收到这封邮件是因为有人请求重置您在SRTP平台的账户密码。

请点击以下链接重置密码：
{reset_url}

重要提示：
- 此链接将在30分钟内失效
- 此链接只能使用一次
- 请不要将此链接分享给他人

如果您没有请求此邮件，请忽略它。

祝好，
SRTP平台团队
'''
            
            mail.send(msg)
            current_app.logger.info(f'密码重置邮件已发送给用户: {user.email}')
            return True
            
        except Exception as flask_mail_error:
            current_app.logger.warning(f'Flask-Mail发送失败，尝试原生SMTP: {str(flask_mail_error)}')
            
            # 方法2：使用原生SMTP作为备用方案
            return send_email_with_smtp(user, token, reset_url)
            
    except Exception as e:
        error_msg = f'邮件发送失败: {str(e)}'
        current_app.logger.error(error_msg)
        current_app.logger.error(f'收件人: {user.email}, 用户: {user.username}')
        return False

def send_email_with_smtp(user, token, reset_url):
    """
    使用原生SMTP发送邮件的备用方法
    """
    try:
        # 邮件配置
        smtp_server = current_app.config.get('MAIL_SERVER')
        smtp_port = current_app.config.get('MAIL_PORT')
        username = current_app.config.get('MAIL_USERNAME')
        password = current_app.config.get('MAIL_PASSWORD')
        
        # 创建邮件内容
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '密码重置请求 - SRTP平台'
        msg['From'] = username
        msg['To'] = user.email
        
        # 邮件正文
        text = f'''亲爱的 {user.username}，

您收到这封邮件是因为有人请求重置您在SRTP平台的账户密码。

请点击以下链接重置密码：
{reset_url}

重要提示：
- 此链接将在30分钟内失效
- 此链接只能使用一次
- 请不要将此链接分享给他人

如果您没有请求此邮件，请忽略它。

祝好，
SRTP平台团队
'''
        
        part = MIMEText(text, 'plain', 'utf-8')
        msg.attach(part)
        
        # 发送邮件
        context = ssl.create_default_context()
        
        if current_app.config.get('MAIL_USE_SSL'):
            # 使用SSL
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                server.login(username, password)
                server.sendmail(username, user.email, msg.as_string())
        else:
            # 使用TLS
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.sendmail(username, user.email, msg.as_string())
        
        current_app.logger.info(f'密码重置邮件已通过SMTP发送给用户: {user.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'SMTP邮件发送失败: {str(e)}')
        return False

def send_welcome_email(user):
    """
    发送欢迎邮件给新注册用户（可选功能）
    
    Args:
        user: 用户对象
    """
    try:
        msg = Message(
            '欢迎加入SRTP平台！',
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@srtp-platform.com'),
            recipients=[user.email]
        )
        
        msg.body = f'''亲爱的 {user.username}，

欢迎加入SRTP平台！

您的账户已成功创建。现在您可以：
- 发布和浏览二手商品
- 进行安全的交易
- 管理您的个人资料

请妥善保管您的私钥文件，它是进行数字签名的重要凭证。

如有任何问题，请随时联系我们。

祝您使用愉快！
SRTP平台团队
'''
        
        mail.send(msg)
        current_app.logger.info(f'欢迎邮件已发送给新用户: {user.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'欢迎邮件发送失败: {str(e)}')
        return False


def test_email_connection():
    """
    测试邮件服务器连接
    """
    try:
        smtp_server = current_app.config.get('MAIL_SERVER')
        smtp_port = current_app.config.get('MAIL_PORT')
        username = current_app.config.get('MAIL_USERNAME')
        password = current_app.config.get('MAIL_PASSWORD')
        
        context = ssl.create_default_context()
        
        if current_app.config.get('MAIL_USE_SSL'):
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                server.login(username, password)
                current_app.logger.info('邮件服务器连接测试成功 (SSL)')
                return True
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(username, password)
                current_app.logger.info('邮件服务器连接测试成功 (TLS)')
                return True
                
    except Exception as e:
        current_app.logger.error(f'邮件服务器连接测试失败: {str(e)}')
        return False