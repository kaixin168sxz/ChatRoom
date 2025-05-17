EXISTS: str = 'Exists'
NO_EXISTS: str = 'NoExists'
OK: str = 'DB-200'
VERSION = 0.48

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
use_markdown = {'admin', 'kaixin'}
web_info = f'**Copyright © 2025 宋昕哲 | v{VERSION}**'

PRINT = print

def print(*args) -> None:
    text = ''
    for arg in args:
        text += str(arg)
    PRINT(text)
    with open('./chatroom.log', 'a+', encoding='utf-8') as f:
        text_nocolor = ''
        text_list = text.split('\n')
        for text in text_list:
            if '\033' in text:
                tmp_text = ''
                tmp_list = text.split('\033')
                for tmp in tmp_list:
                    if 'm' in tmp:
                        tmp_text += 'm'.join(tmp.split('m')[1:])
                    else:
                        tmp_text += tmp
                text = tmp_text
            text_nocolor += text + '\n'

        f.write(text_nocolor + '\n')