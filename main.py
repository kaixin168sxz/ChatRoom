from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import Client, app, ui
from datetime import datetime
from typing import List, Tuple
from db import ChatRoomDB, md5_encrypt
from settings import *

unrestricted_page_routes = {'/signin', '/signup'}
messages: List[Tuple[str, str, str, str]] = []
db = ChatRoomDB('./Database/chatroom.db')

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path
                return RedirectResponse('/signin')
        return await call_next(request)

app.add_middleware(AuthMiddleware)

@ui.page('/signin')
def signin():
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
    def try_signin():
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
        password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined').on('keydown.enter', try_signin)
        with ui.button('登录', on_click=try_signin).classes('x-center bg-green').props('size=md push'):
            ui.tooltip('欢迎来到聊天室').classes('bg-green').props('transition-show="scale" transition-hide="scale"')
        with ui.row().classes('w-full items-center gap-2'):
            ui.space()
            ui.link('注册用户', signup).classes('text-xs text-green')

@ui.refreshable
def chat_messages(name) -> None:
    for user_id, avatar, text, stamp in messages:
        ui.chat_message(text=text, stamp=stamp, avatar=avatar, sent=name == user_id, name=user_id)
    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

@ui.page('/')
async def main():
    ui.add_css('''
        a:link, a:visited {
            color: inherit !important; 
            text-decoration: none; 
            font-weight: 500
        }
        ''')

    if not app.storage.user.get('authenticated', False):
        return RedirectResponse('/signin')

    chat_messages.refresh()

    def logout():
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        length_list = [len(i) + 19 for i in (user_id, now)]      # 19是信息前提示词的宽度("| User        ->   "...)
        length_list.append(len('+-----------------------------------'))
        length_list.append(len('| INFO: user signed out successfully:'))
        max_length = max(length_list)
        max_length += 1
        print( '+-----------------------------------'                   + '-' * (max_length - length_list[2]) + '+\n' +
               '| \033[1;34mINFO\033[0m: user signed out successfully:' + ' ' * (max_length - length_list[3]) + '|\n' +
              f'| User        ->   {user_id}'                           + ' ' * (max_length - length_list[0]) + '|\n' +
              f'| Time(Log)   ->   {now}'                               + ' ' * (max_length - length_list[1]) + '|\n' +
               '+-----------------------------------'                   + '-' * (max_length - length_list[2]) + '+')

        app.storage.user.clear()
        ui.navigate.to(app.storage.user.get('referrer_path', '/signin'))

    def send() -> None:
        if not text.value.strip():
            ui.notify('内容不能为空', type='info', position='top')
            return
        stamp = datetime.now().strftime('%X')
        messages.append((user_id, avatar, text.value, stamp))
        db.new_message(user_id, text.value)
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
            ui.button(icon='send', text='发送', on_click=send).props('size=md push').classes('bg-green')
        with ui.row().classes('w-full no-wrap'):
            ui.space()
            ui.markdown('[Copyright © 2025 kaixin168sxz](https://github.com/kaixin168sxz/ChatRoom)').classes('text-xs self-end mr-8 m-[-1em] text-primary')

    await ui.context.client.connected()  # chat_messages(...) uses run_javascript which is only possible after connecting

    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch'):
        chat_messages(user_id)

@ui.page('/signup')
def signup() -> None:
    ui.add_css('''
        .subtitle {
            font-size: 20px;
        }
        .x-center {
            margin: auto;
            width: 50%;
        }''')
    def try_signup() -> None:
        if email.value and email.value.count('@') != 1:
            ui.notify('邮件格式错误', type='warning', position='top')
            return
        if not email.value and email_switch.value:
            ui.notify('要使用邮箱通知，请输入邮箱', type='warning', position='top')
        try_db = db.sign_up(username.value, password.value, email.value, {True: 'EmailSend', False: 'EmailNoSend'}[email_switch.value])
        if try_db == EXISTS:
            ui.notify('用户名已存在', type='warning', position='top')
            return
        ui.notify('注册成功', type='info', position='top')
        ui.navigate.to(app.storage.user.get('referrer_path', '/signin'))

    ui.query('body').style(f'background-color: #ddeeff')
    with ui.card().classes('absolute-center').style(f'background-color: #edf7ff').props('flat bordered'):
        ui.label('注册用户').classes('subtitle')
        username = ui.input('用户').classes('fill').props('dense outlined')
        password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined')
        def update_switch_val():
            if email.value:
                email_switch.set_value(True)
            else:
                email_switch.set_value(False)
        email = ui.input('邮箱（可选）', on_change=update_switch_val).classes('inline-flex').props('dense outlined').on('keydown.enter', try_signup)
        email_switch = ui.switch('邮箱通知').props('icon="mail" color="green"').bind_visibility_from(email, 'value')
        with ui.button('注册', on_click=try_signup).classes('x-center bg-green').props('size=md push'):
            ui.tooltip('立即注册用户').classes('bg-green').props('transition-show="scale" transition-hide="scale"')
        with ui.row().classes('w-full items-center gap-2'):
            ui.space()
            ui.link('登录用户', signin).classes('text-xs text-green')

ui.run(port=66, storage_secret='THIS_NEEDS_TO_BE_CHANGED', language='zh-CN')