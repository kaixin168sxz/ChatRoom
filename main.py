import os
from copy import copy
from datetime import datetime
from email.mime.text import MIMEText
from time import time
from typing import List, Tuple
import aiosmtplib
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import Client, app, ui, events
from starlette.middleware.base import BaseHTTPMiddleware
from db import ChatRoomDB, md5_encrypt
from settings import *
from PIL import Image
import pillow_heif
from functools import partial

def heic_to_jpg(input_file, output_file):
    heif_file = pillow_heif.read_heif(input_file)
    image = Image.frombytes(
        heif_file.mode,
        heif_file.size,
        heif_file.data,
        "raw",
        heif_file.mode,
        heif_file.stride,
    )
    image.save(output_file, "png")

def resize(any_file: str, scale: tuple[int | float, int | float]) -> str:
    new_file = any_file
    try:
        png_file = os.path.dirname(any_file) + '/png.' + any_file.split('.')[-1]
        im = Image.open(any_file)
        im.save(png_file, 'png')
        im.close()
        os.remove(any_file)
        from_size = im.size
        to_size = (int(from_size[0] * scale[0]), int(from_size[1] * scale[1]))
        im = Image.open(png_file)
        image = im.resize(to_size)
        new_file = '.'.join(any_file.split('.')[: -1]) + '.png'
        image.save(new_file, 'png')
        os.remove(png_file)
    except IOError as e:
        print(f'处理（或缩放）图像失败: {e}，Time(Log) -> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    return new_file

async def sendemail(msg_to, subject, content):
    msg = MIMEText(content+'\n<p><a href="http://c.8v8v.net:66">在聊天室中打开</a></p>', 'html', 'utf-8')
    msg['From'] = from_addr
    msg['To'] = msg_to
    msg['Subject'] = subject

    try:
        smtp = aiosmtplib.SMTP()
        await smtp.connect(hostname='smtp.qq.com', port=465, use_tls=True)
        await smtp.login(from_addr, email_password)
        await smtp.send_message(msg)
        print(f'邮件已发送，Time(Log) -> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    except aiosmtplib.SMTPException as e:
        print(f'邮件发送失败: {e}，Time(Log) -> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

unrestricted_page_routes = {'/signin', '/signup'}
messages: List[Tuple[str, str, str, str]] = []
db = ChatRoomDB('./Database/chatroom.db')

avatars = {}
default_avatar = ''
file_path = ''
file_url = ''
resize_tuple = (0.5, 0.5)
use_resize = True
time_before = 0
version = 0.4

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
    ui.colors(primary='rgb(68,157,72)')
    ui.query('body').style(f'background-color: rgb(247,255,247)')

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
        ui.navigate.to('/')
    with ui.card().classes('absolute-center').style(f'background-color: rgb(235,255,235)').props('flat bordered'):
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
        if text[:6] == 'file::':
            with ui.chat_message(stamp=stamp, avatar=avatar, sent=name == user_id, name=user_id):
                url = file_url + text[6:].split('/')[-1]
                ui.label(f'附件({url})：')
                if text.split('.')[-1].lower() in ['png', 'jpg', 'jpeg', 'heic']:
                    ui.image(url).classes('w-56').props('loading="lazy"')
                ui.button('下载附件', on_click=partial(ui.download, url)).props('size=md push').classes('bg-green')

        elif text[:6] == 'mess::':
            ui.chat_message(text=text[6:], stamp=stamp, avatar=avatar, sent=name == user_id, name=user_id)

    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

@ui.page('/')
async def main():
    ui.add_css('''
        a:link, a:visited {
            color: inherit !important;
            text-decoration: none;
            font-weight: 500
        }
        .x-center {
            margin: auto;
            width: 50%;
        }
        ''')
    ui.colors(primary='rgb(68,157,72)')
    file = ''

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
        ui.navigate.to('/signin')

    def handle_upload(e: events.UploadEventArguments):
        nonlocal file, send_file
        file = os.path.join(file_path, str(time()) + '_' + e.name)
        with open(file, 'wb') as f:
            f.write(e.content.read())
        if file.split('.')[-1].lower() == 'heic':
            old_file = file
            file = '.'.join(file.split('.')[: -1]) + '.jpg'
            heic_to_jpg(old_file, file)
            os.remove(old_file)
        if use_resize:
            if file.split('.')[-1].lower() in ['png', 'jpg', 'jpeg', 'heic']:
                file = resize(file, resize_tuple)
        else:
            file = resize(file, (1, 1))
        ui.notify('附件已上传', position='top', type='info')
        send_file.set_visibility(True)

    async def send() -> None:
        nonlocal file
        global time_before
        dialog.close()
        if not os.path.exists(str(file)):
            text_value = text.value
            text.value = ''
            if not text_value.strip():
                ui.notify('内容不能为空', type='info', position='top')
                return
            text_value = 'mess::' + text_value
        else:
            text_value = 'file::' + file
        file = ''
        stamp = datetime.now().strftime('%X')
        messages.append((user_id, avatar, text_value, stamp))

        # 启用日志会使网站卡顿!
        # try:
        #     db.new_message(user_id, text_value)
        # except UnicodeEncodeError as e:
        #     print(f'编码错误({e}), Time(Log) -> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        chat_messages.refresh()
        time_now = time()
        if (time_now - time_before) > 75:
            time_before = copy(time_now)
            text_value_send = text_value[6:]
            if text_value[:6] == 'file::':
                text_value_send += '\n(请在浏览器中查看附件)'
            for i in db.get_all_emails():
                if i[1] != user_id:
                    await sendemail(i[-2], f'你收到了一条来自{user_id}的消息【聊天室】', text_value_send)

    with ui.dialog() as dialog, ui.column():
        ui.upload(on_upload=handle_upload, auto_upload=True, label='请选择附件', on_rejected=lambda: ui.notify('文件过大，拒绝上传'), max_files=1, max_file_size=80_000_000).classes('max-w-full')
        send_file = ui.button(icon='send', text='发送', on_click=send).props('size=md push').classes('bg-green x-center')
        send_file.set_visibility(False)

    user_id = app.storage.user.get('username')

    if user_id in avatars:
        avatar = avatars[user_id]
    elif default_avatar:
        avatar = default_avatar
    else:
        avatar = ''

    ui.query('body').style(f'background-color: rgb(247,255,247)')

    with ui.header(elevated=True).style('background-color: rgb(147,207,150)').classes('items-center p-1'):
        with ui.row().classes('w-full items-center gap-2'):
            with ui.card().style('background-color: rgb(111,191,115)').classes('p-1').props('flat bordered'):
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
        with ui.row().classes('w-full no-wrap items-center gap-2'):
            with ui.button(on_click=dialog.open).props('size=md push fab color=accent padding="sm"').classes('bg-green gap-0'):
                ui.icon('library_add').style('font-size: 1em')
            text = ui.input('请输入消息').on('keydown.enter', send).props('dense outlined input-class=mx-3').classes('flex-grow')
            ui.button(icon='send', on_click=send).props('size=md push').classes('bg-green')
        with ui.row().classes('w-full no-wrap'):
            ui.space()
            ui.markdown('[Copyright © 2025 宋昕哲(kaixin168sxz)](https://github.com/kaixin168sxz/ChatRoom)').classes('text-xs self-end mr-8 m-[-1em] text-green')

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
    ui.colors(primary='rgb(68,157,72)')

    def try_signup() -> None:
        if not username.value:
            ui.notify('用户名不能为空', type='warning', position='top')
        elif not password.value:
            ui.notify('密码不能为空', type='warning', position='top')
        elif email.value and email.value.count('@') != 1:
            ui.notify('邮件格式错误', type='warning', position='top')
        elif not email.value and email_switch.value:
            ui.notify('要使用邮箱通知，请输入邮箱', type='warning', position='top')
        else:
            if password.value == retry_password.value:
                try_db = db.sign_up(username.value, password.value, email.value, {True: 'EmailSend', False: 'EmailNoSend'}[email_switch.value])
                if try_db == EXISTS:
                    ui.notify('用户名已存在', type='warning', position='top')
                    return
                ui.notify('注册成功', type='info', position='top')
                ui.navigate.to('/signin')
            else:
                ui.notify('密码和确认密码不相同', type='warning', position='top')

    ui.query('body').style(f'background-color: rgb(247,255,247)')
    with ui.card().classes('absolute-center').style(f'background-color: rgb(235,255,235)').props('flat bordered'):
        ui.label('注册用户').classes('subtitle')
        username = ui.input('用户').classes('fill').props('dense outlined')
        password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined')
        retry_password = ui.input('再次确认密码', password=True).classes('inline-flex').props('dense outlined')
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

def update_ui_log(text):
    text.clear()
    with open('./chatroom.log', 'r', encoding='utf-8') as f:
        for i in f.read().splitlines()[-100: ]:
            text.push(i)

@ui.page('/dev')
def developer() -> None:
    ui.add_css('''
        .subtitle {
            font-size: 20px;
        }
        .x-center {
            margin: auto;
            width: 50%;
        }''')
    ui.colors(primary='rgb(68,157,72)')
    user_id = app.storage.user.get('username')
    if user_id not in ['admin', 'debugger', 'kaixin']:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')
        with ui.dialog() as dialog, ui.card():
            ui.label('权限不足，无法访问开发者控制台')
            ui.button('回到主页', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
    ui.query('body').style(f'background-color: rgb(247,255,247)')
    ui.label(f'Hi, {user_id}').classes('subtitle')
    ui.link('实时日志', dev_log).classes('text-green')
    ui.link('运行代码', dev_code).classes('text-green')

@ui.page('/log')
def dev_log() -> None:
    ui.add_css('''
        .subtitle {
            font-size: 20px;
        }
        .x-center {
            margin: auto;
            width: 50%;
        }
        .code-font {
            font-family: monospace;
        }''')
    ui.colors(primary='rgb(68,157,72)')
    user_id = app.storage.user.get('username')
    if user_id not in ['admin', 'debugger', 'kaixin']:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')
        with ui.dialog() as dialog, ui.card():
            ui.label('权限不足，无法访问开发者控制台')
            ui.button('回到主页', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
    ui.query('body').style(f'background-color: rgb(247,255,247)')
    ui.label('RealTimeLog(实时日志):')
    text = ui.log(max_lines=100).classes('w-full h-100 scroll-snap-type scroll-snap-align code-font')
    def download_log() -> None:
        ui.download('./chatroom.log')
    ui.button('下载日志文件', on_click=download_log).classes('bg-green').props('size=md push')
    def update_log() -> None:
        update_ui_log(text)
    ui.timer(1.0, update_log)

@ui.page('/code')
def dev_code() -> None:
    ui.add_css('''
        .subtitle {
            font-size: 20px;
        }
        .x-center {
            margin: auto;
            width: 50%;
        }
        .code-font {
            font-family: monospace;
        }''')
    ui.colors(primary='rgb(68,157,72)')
    user_id = app.storage.user.get('username')
    if user_id not in ['admin', 'debugger', 'kaixin']:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')
        with ui.dialog() as dialog, ui.card():
            ui.label('权限不足，无法访问开发者控制台')
            ui.button('回到主页', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
    ui.query('body').style(f'background-color: rgb(247,255,247)')

    def run_code() -> None:
        cmd = str(code.value)
        exec_data = globals()
        if 'def main(' not in cmd:
            exec_data['ret'] = 'Cannot find main code.'
        else:
            try:
                PRINT(str(cmd) + f'\n\nret = main()')
                exec(str(cmd) + f'\n\nret = main()', exec_data)
            except Exception as e:
                exec_data['ret'] = str(e)
        code_output.clear()
        code_output.push('output > \n')
        code_output.push(exec_data['ret'])

    ui.label('运行Python代码(exec):')
    ui.label('!危险操作!').classes('text-red subtitle')
    with ui.row():
        ui.markdown('按下***运行按钮***将会**自动执行`main`函数中的内容**，并输出`main函数`的返回值，**不会输出除`main的返回值`外的任何其他值（如`print`）**')
        ui.button('运行', on_click=run_code).classes('bg-green').props('size=md push')
    code = ui.textarea('Code').classes('w-full h-100 code-font').props('dense outlined')
    ui.label('输出')
    code_output = ui.log(max_lines=1000).classes('w-full h-100 code-font')
    code_output.push('output > \n')

def run() -> None:
    ui.run(port=66, storage_secret=storage_secret, language='zh-CN', title='ChatRoom聊天室')
