import hashlib

def md5_encrypt(data):
    md5 = hashlib.md5()
    md5.update(data.encode('utf-8'))
    return md5.hexdigest()

# 测试示例
# data = "你好"
# encrypted_data = md5_encrypt(data)
# print("加密前的数据：", data)
# print("加密后的数据：", encrypted_data)

data = "哈哈"
encrypted_data = md5_encrypt(data)
print("加密前的数据：", data)
print("加密后的数据：", encrypted_data)
