from flask_login import UserMixin
from datetime import datetime
from extensions import db
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    public_key = db.Column(db.Text, nullable=False)  # 存储PEM格式的公钥
    is_admin = db.Column(db.Boolean, nullable=False, default=False)  # 新增管理员字段
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系定义
    items = db.relationship('Item', backref='seller', lazy=True)
    transactions_as_buyer = db.relationship('Transaction', foreign_keys='Transaction.buyer_id', backref='buyer', lazy=True)
    transactions_as_seller = db.relationship('Transaction', foreign_keys='Transaction.seller_id', backref='seller_user', lazy=True)
    
    def get_reset_token(self, expires_sec=1800):  # 30分钟有效期
        """生成密码重置令牌"""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({
            'user_id': self.id,
            'email': self.email,  # 增加邮箱验证
            'timestamp': datetime.utcnow().timestamp()  # 增加时间戳
        })
    
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """验证密码重置令牌"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
            user = User.query.get(data['user_id'])
            # 验证邮箱是否匹配（防止令牌被恶意使用）
            if user and user.email == data.get('email'):
                return user
        except Exception:
            return None
        return None
    
    def __repr__(self):
        return f'<User {self.username}>'

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_sold = db.Column(db.Boolean, nullable=False, default=False)
    
    def __repr__(self):
        return f'<Item {self.title}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_data = db.Column(db.Text, nullable=False)  # 存储签名的交易数据
    buyer_signature = db.Column(db.Text, nullable=True)  # 买家签名
    seller_signature = db.Column(db.Text, nullable=True)  # 卖家签名
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, confirmed, cancelled
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系定义
    item = db.relationship('Item', backref='transactions')
    # 删除重复的关系定义，因为已在 User 模型中定义
    
    def __repr__(self):
        return f'<Transaction {self.id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)  # 关联商品，可选
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系定义
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    item = db.relationship('Item', backref='messages')
    
    def __repr__(self):
        return f'<Message {self.id}>'

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)  # 关联商品
    last_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系定义
    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])
    item = db.relationship('Item', backref='conversations')
    last_message = db.relationship('Message', foreign_keys=[last_message_id])
    
    def get_other_user(self, current_user_id):
        """获取对话中的另一个用户"""
        return self.user2 if self.user1_id == current_user_id else self.user1
    
    def __repr__(self):
        return f'<Conversation {self.id}>'

class PasswordResetLog(db.Model):
    __tablename__ = 'password_reset_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # 支持IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # requested, completed, failed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    user = db.relationship('User', backref='reset_logs')