import json
from datetime import datetime

def construct_transaction_data_to_sign(item_id: int, item_title: str, item_price: float, buyer_id: int, seller_id: int, timestamp_utc_iso: str) -> str:
    """
    构造用于RSA签名的交易数据字符串
    
    参数:
        item_id: 商品ID
        item_title: 商品标题
        item_price: 商品价格
        buyer_id: 买家用户ID
        seller_id: 卖家用户ID
        timestamp_utc_iso: 交易发起时的UTC时间戳 (ISO 8601格式)
    
    返回:
        JSON格式的字符串，用于RSA签名
    """
    data_to_sign = {
        'item_id': item_id,
        'item_title': item_title,
        'item_price': float(item_price),  # 确保类型一致
        'buyer_id': buyer_id,
        'seller_id': seller_id,
        'timestamp_utc': timestamp_utc_iso
    }
    
    # 使用固定的键排序和紧凑格式确保一致性
    return json.dumps(data_to_sign, sort_keys=True, separators=(',', ':'))