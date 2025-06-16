# ChatRoom
简单地创建一个纯粹的聊天室

## 部署方式

### 密码文件

新建一个`passwd.py`，输入以下内容:

```python
def from_addr():
    return 'EMAIL_ADDR'
def email_password():
    return 'EMAIL_PASSWD'
def storage_secret():
    return 'ANY_PASSWD'

```

加密成pyd或so   (可选，建议使用)

### 安装依赖

使用uv管理

```zsh
uv sync
```

### 运行程序

```zsh
python3 run.py
```

或使用`nohup`（后台运行）：

```zsh
nohup python3 run.py &
```

### 测试运行

在浏览器中打开shell（终端）中输出的链接
建议先在本地测试再上传到服务器，当前版本bug**超多**
**发现bug的话，就上github提交一个`issue`吧**

### 开发人员

1. kaixin168sxz
2. XuWanxuan

## 文件介绍

- `chatroom.log`: 程序日志文件
- `Database/chatroom.db`: 程序数据库
  - `tables`
    - `message`: 储存聊天记录（已弃用）
    - `users`: 储存所有用户信息
- `db.py`: 数据库管理文件
- `passwd.py`: 储存密码
- `LICENSE`: MIT证书文件
- `main.py`: WebUI主文件
- `README.md`: 说明文件（你正在读的文件）
- `requirements.txt`: 程序依赖包列表（供`pip`使用）
- `run.py`: 入口文件
- `settings.py`: 设置文件
