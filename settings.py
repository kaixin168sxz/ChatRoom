from datetime import datetime

EXISTS: str = 'Exists'
NO_EXISTS: str = 'NoExists'
OK: str = 'DB-200'
VERSION = 0.8

avatars = {}
default_avatar = ''
file_path = ''
file_url = ''
resize_tuple = (0.5, 0.5)
use_resize = True
replace_username = {}
allow_signup = True
blacklist = {}
unrestricted_page_routes = {'/signin', '/signup'}
allow_blackuser = {'/signin', '/signup', '/black_user'}
use_markdown = {'admin', 'debugger', 'kaixin', '螃蟹'}
admin_users = {'admin', 'debugger', 'kaixin', '螃蟹'}
use_html = {'admin', 'debugger', 'kaixin', '螃蟹'}
web_info = f'**苏ICP备2025180468号 | Copyright © 2025 宋昕哲 | v{VERSION}**'
output = True

PRINT = print

def print(*args) -> None:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text = f'Time: {now} -> '
    for arg in args:
        text += str(arg) + ' '
    if output:
        PRINT(text)
    with open('./chatroom.log', 'a+', encoding='utf-8') as f:
        f.write(text + '\n')