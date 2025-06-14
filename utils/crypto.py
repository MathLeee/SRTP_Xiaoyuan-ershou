from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
import base64

def generate_rsa_keys():
    """
    生成RSA密钥对并返回PEM格式的私钥和公钥字符串。
    
    Returns:
        tuple: (private_key_pem, public_key_pem) - 私钥和公钥的PEM格式字符串
    """
    # 生成私钥（2048位，公钥指数65537）
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # 序列化私钥为PEM格式（无加密）
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # 获取公钥
    public_key = private_key.public_key()
    
    # 序列化公钥为PEM格式
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # 返回解码后的字符串格式
    return (private_pem.decode('utf-8'), public_pem.decode('utf-8'))

def sign_data(private_key_pem: str, data_to_sign: bytes) -> str:
    """
    使用RSA私钥对数据进行数字签名。
    
    Args:
        private_key_pem (str): PEM格式的RSA私钥字符串
        data_to_sign (bytes): 需要签名的原始字节数据
    
    Returns:
        str: Base64编码的签名字符串
    """
    # 加载私钥
    private_key = load_pem_private_key(private_key_pem.encode('utf-8'), password=None)
    
    # 执行签名（使用PSS填充和SHA256哈希）
    signature = private_key.sign(
        data_to_sign,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    # Base64编码签名
    b64_signature = base64.b64encode(signature).decode('utf-8')
    
    return b64_signature

def verify_signature(public_key_pem: str, b64_signature: str, original_data: bytes) -> bool:
    """
    使用RSA公钥验证数字签名的有效性。
    
    Args:
        public_key_pem (str): PEM格式的RSA公钥字符串
        b64_signature (str): Base64编码的签名字符串
        original_data (bytes): 用于验证签名的原始字节数据
    
    Returns:
        bool: 签名验证结果，True表示验证成功，False表示验证失败
    """
    try:
        # 加载公钥
        public_key = load_pem_public_key(public_key_pem.encode('utf-8'))
        
        # Base64解码签名
        signature_bytes = base64.b64decode(b64_signature)
        
        # 执行验证（使用PSS填充和SHA256哈希）
        public_key.verify(
            signature_bytes,
            original_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # 如果没有抛出异常，验证成功
        return True
        
    except InvalidSignature:
        # 签名无效
        return False
    except (ValueError, Exception):
        # 其他错误（如Base64解码错误、公钥格式错误等）
        return False

if __name__ == "__main__":
    # 测试函数
    print("=== 测试RSA密钥生成 ===")
    private_key, public_key = generate_rsa_keys()
    print("Private Key:")
    print(private_key)
    print("\nPublic Key:")
    print(public_key)
    
    print("\n=== 测试RSA数据签名 ===")
    # 测试数据签名
    test_data = b"Hello, this is a test message for RSA signing!"
    signature = sign_data(private_key, test_data)
    print(f"Original data: {test_data.decode('utf-8')}")
    print(f"Signature (Base64): {signature}")
    
    print("\n=== 测试RSA签名验证 ===")
    # 测试签名验证
    is_valid = verify_signature(public_key, signature, test_data)
    print(f"Signature verification result: {is_valid}")
    
    # 测试无效签名
    fake_signature = "invalid_signature_base64"
    is_invalid = verify_signature(public_key, fake_signature, test_data)
    print(f"Invalid signature verification result: {is_invalid}")
    
    # 测试篡改数据
    tampered_data = b"Hello, this is a TAMPERED message for RSA signing!"
    is_tampered = verify_signature(public_key, signature, tampered_data)
    print(f"Tampered data verification result: {is_tampered}")