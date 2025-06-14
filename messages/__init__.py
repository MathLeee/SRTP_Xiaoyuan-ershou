from flask import Blueprint

# 创建消息蓝图
messages_bp = Blueprint('messages', __name__, template_folder='../templates/messages')

# 导入路由（这会将路由注册到蓝图上）
from . import routes