from flask import Blueprint

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')

# 导入路由（这会将路由注册到蓝图上）
from . import routes