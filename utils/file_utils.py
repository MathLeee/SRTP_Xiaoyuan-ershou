import os
import secrets
from PIL import Image
from flask import current_app

def save_item_picture(form_picture_data):
    """保存商品图片并返回文件名"""
    # 生成随机文件名
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture_data.filename)
    picture_fn = random_hex + f_ext
    
    # 确保上传目录存在
    output_dir = os.path.join(current_app.root_path, 'static/uploads')
    os.makedirs(output_dir, exist_ok=True)
    
    # 构造完整路径
    picture_path = os.path.join(output_dir, picture_fn)
    
    # 调整图片大小并保存
    output_size = (300, 300)
    i = Image.open(form_picture_data)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn