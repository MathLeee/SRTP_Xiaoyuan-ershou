from flask import Blueprint

# 创建交易蓝图
transactions_bp = Blueprint('transactions', __name__, template_folder='../templates/transactions')

# 导入路由（这会将路由注册到蓝图上）
from . import routes