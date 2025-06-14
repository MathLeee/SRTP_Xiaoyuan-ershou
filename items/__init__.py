from flask import Blueprint

# 创建商品蓝图
items_bp = Blueprint('items', __name__, template_folder='../templates/items')

# 导入路由（这会将路由注册到蓝图上）
from . import routes