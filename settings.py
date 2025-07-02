from datetime import datetime
import json
import string

PRINT = print
output = True

def print(*args) -> None:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = f'Time: {now} -> '
    for arg in args:
        text += str(arg) + ' '
    if output:
        PRINT(text)
    with open('./chatroom.log', 'a+', encoding='utf-8') as f:
        f.write(text + '\n')

class Config:
    def __init__(self, file: str, key: str):
        with open(file, 'r', encoding='utf-8') as f:
            self.json = json.load(f)
        self.config = self.json.get(key)
        self.config_type = type(self.config)
        self.log_head = f'config, file: {file}, key: {key}'
        if self.config_type is dict:
            self.keys = self.config.keys
        self.file = file
        self.key = key
        print(f'[{self.log_head}] Config initialized:', self.config)
    
    def sync(self):
        self.json[self.key] = self.config
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.json, f, ensure_ascii=False, indent=4)
    
    def __repr__(self):
        return str(self.config)

    def __str__(self):
        return str(self.config)

    def __getitem__(self, name):
        try:
            v = self.config[name]
        except KeyError:
            print(f'[{self.log_head}, getitem] KeyError: {name} not found in config')
            return None
        return v
    
    def pop(self, value):
        if self.config_type is not dict:
            print(f'[{self.log_head}, pop] TypeError: config is not a dict')
            return None
        try:
            config_ = self.config
            v = self.config.pop(value)
        except KeyError:
            self.config = config_   # 确保原子性（如果pop失败，恢复原来的config）
            print(f'[{self.log_head}, pop] KeyError: {value} not found in config')
            return None
        self.sync()
        return v
    
    def remove(self, value):
        if self.config_type is not list:
            print(f'[{self.log_head}, remove] TypeError: config is not a list')
            return None
        try:
            config_ = self.config
            self.config.remove(value)
        except KeyError:
            self.config = config_   # 确保原子性（如果remove失败，恢复原来的config）
            print(f'[{self.log_head}, remove] KeyError: {value} not found in config')
            return None
        self.sync()
        return True
    
    def append(self, value):
        ''' Append a value to the config like a list.'''
        if self.config_type is not list:
            print(f'[{self.log_head}, append] TypeError: config is not a list')
            return None
        self.config.append(value)
        self.sync()
        return True
    
    def add(self, value):
        ''' Add a value to the config like a set.'''
        if self.config_type is not list:    # 在json中没有元组，所以使用列表代替
            print(f'[{self.log_head}, add] TypeError: config is not a list')
            return None
        if value in self.config:    # 保证元组的唯一性
            print(f'[{self.log_head}, add] Value {value} already exists in config')
            return False
        self.append(value)
    
    def __setitem__(self, name, value):
        if self.config_type is not dict:
            print(f'[{self.log_head}, append] TypeError: config is not a dict')
            return None
        self.config[name] = value
        self.sync()
        return True

EXISTS: str = 'Exists'
NO_EXISTS: str = 'NoExists'
OK: str = 'DB-200'
VERSION = '1.0 beta2'

email_on = True
ai_on = True
cmd_on = True
ai_base_url = "https://api.deepseek.com"
ai_model = "deepseek-chat"
ai_sleep_time = 1
ai_reset_time = 600
random_dict = string.digits + string.ascii_lowercase + string.ascii_uppercase
avatars = {}
default_avatar = 'avatars/1.png'
avatars_path = 'avatars'
avatars_url = '/avatars'
file_path = 'files'
file_url = '/files'
database_path = 'Database'
database_url = '/db'
web_files_path = 'web_files'
web_files_url = '/web_files'
resize_tuple = (0.5, 0.5)
avatar_resize_tuple = (0.3, 0.3)
use_resize = True
replace_username = Config(f'{database_path}/users.json', 'replace')
allow_signup = True
blacklist = Config(f'{database_path}/users.json', 'blacklist')
unrestricted_page_routes = {'/signin', '/signup'}
allow_blackuser = {'/signin', '/signup', '/black_user'}
use_markdown = Config(f'{database_path}/users.json', 'markdown')
admin_users = Config(f'{database_path}/users.json', 'admin')
use_html = Config(f'{database_path}/users.json', 'html')
web_info = f'**苏ICP备2025180468号 | © 2025 宋昕哲 | v{VERSION}**'
# web_info = f'**v{VERSION}**'