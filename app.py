import os
from flask import Flask, render_template, request
from dotenv import load_dotenv  # 新增
from extensions import db, bcrypt, login_manager, mail, csrf, migrate  # 添加 migrate

# 加载环境变量
load_dotenv()  # 新增

# 创建Flask应用实例
app = Flask(__name__)

# Flask应用基本配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your_strong_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'srtp.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 邮件配置
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or 465)
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# 初始化Flask扩展
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
mail.init_app(app)
csrf.init_app(app)
migrate.init_app(app, db)  # 新增这一行

# 配置LoginManager
login_manager.login_view = 'auth.login'  # 指向auth蓝图的login路由
login_manager.login_message_category = 'info'

# Flask-Login用户加载器
@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login用户加载器回调函数
    
    Args:
        user_id (str): 会话中存储的用户ID
        
    Returns:
        User: 用户对象，如果用户不存在则返回None
    """
    from models import User
    return User.query.get(int(user_id))

# 注册蓝图
from auth import auth_bp
from items import items_bp
from transactions import transactions_bp
from messages import messages_bp
from admin import admin_bp  # 新增

app.register_blueprint(auth_bp)
app.register_blueprint(items_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(admin_bp)  # 新增

# Flask CLI命令：初始化数据库
@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    from models import User, Item, Transaction
    db.create_all()
    print("Initialized the database.")

# 基础路由（首页）
@app.route('/')
def index():
    """首页 - 展示商品列表"""
    from models import Item
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    
    # 查询所有未售出商品，按ID降序排列（作为时间排序的替代），并分页
    items = Item.query.filter_by(is_sold=False).order_by(Item.id.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    
    return render_template('index.html', 
                         title='首页', 
                         items=items)

# 运行应用
if __name__ == '__main__':
    app.run(debug=True)