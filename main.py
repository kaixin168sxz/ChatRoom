from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import Client, app, ui
from datetime import datetime
from typing import List, Tuple
from db import ChatRoomDB, md5_encrypt
from settings import *

unrestricted_page_routes = {'/login'}
messages: List[Tuple[str, str, str, str]] = []
db = ChatRoomDB('./Database/chatroom.db')

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path
                return RedirectResponse('/login')
        return await call_next(request)

app.add_middleware(AuthMiddleware)

@ui.page('/login')
def login():
    ui.add_css('''
        .subtitle {
            font-size: 20px;
        }
        .x-center {
            margin: auto;
            width: 50%;
        }''')
    ui.query('body').style(f'background-color: #ddeeff')
    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')
    def try_login():
        user = username.value
        passwd = password.value
        user_data = db.get_user_data(user)
        if user_data == NO_EXISTS:
            ui.notify('用户不存在', position='top', type='warning', color='red')
            return
        if user_data[2][16:-10] != md5_encrypt(passwd)[16:-10]:
            ui.notify('密码错误', position='top', type='warning', color='red')
            return
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        length_list = [len(i) + 19 for i in (user, now)]      # 19是信息前提示词的宽度("| User        ->   "...)
        length_list.append(len('+-----------------------------------'))
        length_list.append(len('| INFO: user signed in successfully:'))
        max_length = max(length_list)
        max_length += 1
        print('+-----------------------------------'                  + '-' * (max_length - length_list[2]) + '+\n' +
              '| \033[1;34mINFO\033[0m: user signed in successfully:' + ' ' * (max_length - length_list[3]) + '|\n' +
              f'| User        ->   {user}'                            + ' ' * (max_length - length_list[0]) + '|\n' +
              f'| Time(Log)   ->   {now}'                             + ' ' * (max_length - length_list[1]) + '|\n' +
              '+-----------------------------------'                  + '-' * (max_length - length_list[2]) + '+')
        app.storage.user.update({'username': user, 'authenticated': True})
        ui.navigate.to(app.storage.user.get('referrer_path', '/'))
    with ui.card().classes('absolute-center').style(f'background-color: #edf7ff').props('flat bordered'):
        ui.label('欢迎来到聊天室').classes('subtitle')
        username = ui.input('用户').classes('fill').props('dense outlined')
        password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined').on('keydown.enter', try_login)
        with ui.button('登录', on_click=try_login).classes('x-center bg-green').props('size=md push'):
            ui.tooltip('欢迎来到聊天室').classes('bg-green').props('transition-show="scale" transition-hide="scale"')

@ui.refreshable
def chat_messages(name) -> None:
    for user_id, avatar, text, stamp in messages:
        ui.chat_message(text=text, stamp=stamp, avatar=avatar, sent=name == user_id, name=user_id)
    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

@ui.page('/')
async def main():
    ui.add_css('''
        .subtitle {
            font-size: 20px;
        }
        a:link, a:visited {
            color: inherit !important; 
            text-decoration: none; 
            font-weight: 500
        }
        ''')

    if not app.storage.user.get('authenticated', False):
        return RedirectResponse('/login')

    def logout():
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        length_list = [len(i) + 19 for i in (user_id, now)]      # 19是信息前提示词的宽度("| User        ->   "...)
        length_list.append(len('+-----------------------------------'))
        length_list.append(len('| INFO: user logged out successfully:'))
        max_length = max(length_list)
        max_length += 1
        print('+-----------------------------------'                   + '-' * (max_length - length_list[2]) + '+\n' +
              '| \033[1;34mINFO\033[0m: user logged out successfully:' + ' ' * (max_length - length_list[3]) + '|\n' +
              f'| User        ->   {user_id}'                          + ' ' * (max_length - length_list[0]) + '|\n' +
              f'| Time(Log)   ->   {now}'                              + ' ' * (max_length - length_list[1]) + '|\n' +
              '+-----------------------------------'                   + '-' * (max_length - length_list[2]) + '+')

        app.storage.user.clear()
        ui.navigate.to(app.storage.user.get('referrer_path', '/'))

    def send() -> None:
        stamp = datetime.now().strftime('%X')
        messages.append((user_id, avatar, text.value, stamp))
        text.value = ''
        chat_messages.refresh()

    user_id = app.storage.user.get('username')
    avatar = 'http://192.168.0.108:666/9.72-Nicegui/2.jpg'

    with ui.header(elevated=True).style('background-color: #8bbcff').classes('items-center p-1'):
        with ui.row().classes('w-full items-center gap-2'):
            with ui.card().style('background-color: #579fff').classes('p-1').props('flat bordered'):
                with ui.row().classes('items-center gap-3'):
                    with ui.avatar(color='#B0B0B0', size='lg').on('click', lambda: ui.navigate.to(main)):
                        ui.image(avatar)
                    with ui.column().classes('items-center gap-0'):
                        ui.label(user_id[:9] + '...' if len(user_id) > 10 else user_id).classes('text-s text-white')
                        with ui.button(icon='logout', on_click=logout).props('size=sm push').classes('bg-green'):
                            ui.tooltip('注销').classes('bg-red').props('transition-show="scale" transition-hide="scale"')
            time_label = ui.label(text=str(datetime.now().strftime("%X"))).classes('text-lg absolute left-1/2 top-1/2 translate-x-[-50%] translate-y-[-50%]')
            ui.timer(1.0, lambda: time_label.set_text(str(datetime.now().strftime("%X"))))

    with ui.footer().classes('bg-white'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            text = ui.input('请输入消息').on('keydown.enter', send).props('dense outlined input-class=mx-3').classes('flex-grow')
        with ui.row().classes('w-full no-wrap'):
            ui.space()
            ui.markdown('[Copyright © 2025 kaixin168sxz](https://github.com/kaixin168sxz/ChatRoom)').classes('text-xs self-end mr-8 m-[-1em] text-primary')

    await ui.context.client.connected()  # chat_messages(...) uses run_javascript which is only possible after connecting

    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch'):
        chat_messages(user_id)

ui.run(port=66, storage_secret='THIS_NEEDS_TO_BE_CHANGED', language='zh-CN')