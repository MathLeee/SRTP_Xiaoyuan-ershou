from app import app
from extensions import db, bcrypt
from models import User
from utils.crypto import generate_rsa_keys

def create_admin():
    with app.app_context():
        # 检查是否已存在admin用户
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print('管理员账户已存在')
            return
        
        # 生成RSA密钥对
        private_key_pem, public_key_pem = generate_rsa_keys()
        
        # 创建管理员账户
        hashed_password = bcrypt.generate_password_hash('142857').decode('utf-8')
        admin = User(
            username='admin',
            email='admin@srtp.com',
            password_hash=hashed_password,
            public_key=public_key_pem,
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        print('默认管理员账户创建成功：admin/142857')

if __name__ == '__main__':
    create_admin()