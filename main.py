import os
from copy import copy
from datetime import datetime
from email.mime.text import MIMEText
import random
from time import time
from typing import List, Tuple
import aiosmtplib
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import Client, app, ui, events
from starlette.middleware.base import BaseHTTPMiddleware
from db import ChatRoomDB, md5_encrypt
from settings import *
from passwd import *
from PIL import Image
import pillow_heif
from openai import AsyncOpenAI

with open('./doc_cmd.md', 'r', encoding='utf-8') as f:
    cmd_help = f.read()

client = AsyncOpenAI(api_key=ai_api_key(), base_url=ai_base_url)
with open('./ai_system.txt', 'r', encoding='utf-8') as f:
    ai_system = f.read()
ai_messages = [{"role": "system", "content": ai_system},]
ai_time_before = 0

async def ask_ai(message: str, user_id: str):
    ai_messages.append({"role": "user", "content": message})
    response = await client.chat.completions.create(
        model=ai_model,
        messages=ai_messages,
        stream=False
    )
    content = response.choices[0].message.content
    print(f'[AI] {ai_model} response(from {user_id}):', content)
    ai_messages.append({"role": "assistant", "content": content})
    return content

async def ai_message(message: str, user_id: str):
    global messages, ai_messages, ai_time_before
    if time() - ai_time_before < ai_sleep_time:
        print('[AI] Message too fast, skipping...')
        return
    if time() - ai_time_before > ai_reset_time:
        print('[AI] Auto clean AI messages...')
        ai_messages = [{"role": "system", "content": ai_system},]
    ai_time_before = time()
    response = await ask_ai(message, user_id)
    messages.append(('', 'avatars/deepseek.png', 'mess::'+response, datetime.now().strftime('%H:%M:%S')))
    display_messages.refresh()
    return response

def heic_to_png(input_file, output_file):
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
        png_file = os.path.dirname(any_file) + '/png.' + any_file.split('/')[-1]
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
        print(f'[file] 处理（或缩放）图像失败: {e}')
    return new_file

async def sendemail(msg_to, subject, content):
    msg = MIMEText(content+'\n<p><a href="http://c.8v8v.net:66">在聊天室中打开</a></p>', 'html', 'utf-8')
    msg['From'] = from_addr()
    msg['To'] = msg_to
    msg['Subject'] = subject

    try:
        smtp = aiosmtplib.SMTP()
        await smtp.connect(hostname='smtp.qq.com', port=465, use_tls=True)
        await smtp.login(from_addr(), email_password())
        await smtp.send_message(msg)
        print(f'[email] 邮件已发送')
    except aiosmtplib.SMTPException as e:
        print(f'[email] 邮件发送失败: {e}')

messages: List[Tuple[str, str, str, str]] = []
db = ChatRoomDB('./Database/chatroom.db')
email_time_before = 0

with open('./about.md', 'r', encoding='utf-8') as f:
    about_text = f.read()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in unrestricted_page_routes:
                app.storage.user['referrer_path'] = request.url.path
                return RedirectResponse('/signin')
        else:
            if app.storage.user.get('username') in blacklist.keys() and request.url.path not in allow_blackuser:
                return RedirectResponse('/black_user')
        return await call_next(request)

app.add_middleware(AuthMiddleware)

@ui.page('/black_user')
def black_user():
    username = app.storage.user.get('username')
    if username in blacklist.keys():
        print('[user] BLACK_USER:', username)
        black_label = blacklist[username]
        ui.markdown(black_label if black_label else '# 滚!')
    else:
        return RedirectResponse('/')

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
        print(f'[user] user {user} logged in')
        app.storage.user.update({'username': user, 'authenticated': True})
        ui.navigate.to('/')
    with ui.card().classes('absolute-center').style(f'background-color: rgb(235,255,235)').props('flat bordered'):
        ui.label('欢迎').classes('subtitle')
        username = ui.input('用户').classes('fill').props('dense outlined')
        password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined').on('keydown.enter', try_signin)
        with ui.button('登录', on_click=try_signin).classes('x-center bg-green').props('size=md push'):
            ui.tooltip('Welcome').classes('bg-green').props('transition-show="scale" transition-hide="scale"')
        if allow_signup:
            with ui.row().classes('w-full items-center gap-2'):
                ui.space()
                ui.link('注册用户', signup).classes('text-xs text-green')
    with ui.footer().style(f'background-color: rgb(247,255,247)'), ui.row().classes('w-full no-wrap'):
        ui.space()
        ui.markdown(web_info).classes('text-xs text-green')

    return None

def really_delete_message(num: int, dialog_div) -> None:
    with dialog_div:
        with ui.dialog() as dialog, ui.card().classes('justify-center items-center'):
                ui.label('真的要撤回这条消息吗？')
                ui.separator().classes('w-full')
                ui.label('撤回').classes('text-red').on('click', lambda: delete_message(num, dialog)).style('cursor: pointer;')
                ui.label('取消').on('click', dialog.close).style('cursor: pointer;')
    dialog.open()

def delete_message(num: int, dialog) -> None:
    global messages
    messages.pop(num)
    display_messages.refresh()
    if dialog:
        dialog.close()

@ui.refreshable
def display_messages(name, dialog_div) -> None:
    for i in range(len(messages)):
        user_id, avatar, text, stamp = messages[i]
        avatar_db = db.get_user_data(user_id)[-1]
        if avatar:
            pass
        elif user_id in avatars:
            avatar = avatars[user_id]
        elif avatar_db:
            avatar = avatar_db
        else:
            avatar = default_avatar

        if name not in [*admin_users, user_id]:
            # 如果消息开头为@并且用户没有被@，则不显示消息（只有被@才显示）
            if text[6] == '@':
                name_list = text[7:].split(':')[0]
                if ' ' in name_list:
                    name_list = name_list.split(' ')
                else:
                    name_list = [name_list, ]
                if name not in name_list:
                    continue
            if text[6] == '^':
                name_list = text[7:].split(':')[0]
                if ' ' in name_list:
                    name_list = name_list.split(' ')
                else:
                    name_list = [name_list, ]
                if name in name_list:
                    continue

        show_id = user_id
        if user_id in replace_username.keys():
            show_id = replace_username[user_id]
        show_side = ' margin-left: auto;' if name == user_id else ' margin-right: auto;'
        with ui.column().classes('gap-0').style('margin-top: 0; margin-bottom: 0;'+show_side):
            with ui.chat_message(stamp=stamp, avatar=avatar, sent=name == user_id, name=show_id):
                if text[:6] == 'file::':
                    url = file_url + '/' + text[6:].split('/')[-1]
                    ui.label(f'附件({url})：')
                    if text.split('.')[-1].lower() in ['png', 'jpg', 'jpeg']:
                        ui.image(url).classes('w-56').props('loading="lazy"')
                    elif text.split('.')[-1].lower() in ['mp3', 'wav']:
                        ui.audio(url).classes('w-56').props('loading="lazy"')
                    elif text.split('.')[-1].lower() in ['mp4', ]:
                        ui.video(url).classes('w-56').props('loading="lazy"')
                    ui.link('点击下载附件', url, new_tab=True).classes('text-blue')
                elif text[:6] == 'mess::':
                    if user_id in use_html and text[-11: ] == '\n</USEhtml>':
                        ui.html(text[6:])
                    elif user_id in use_markdown:
                        ui.markdown(text[6:])
                    else:
                        ui.label(text[6:])
            if name == user_id:
                ui.label('撤回').on('click', lambda num=i: really_delete_message(num, dialog_div)).props('size=xs')\
                    .style('cursor: pointer; color: rgb(100, 100, 100);')
            if not user_id:
                ui.label('由AI生成').classes('text-xs text-gray-500').style('margin-left: 3rem;')

    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

def clean_all_message(dialog):
    global messages
    dialog.close()
    messages = []
    display_messages.refresh()

def clean_messages(div):
    with div:
        with ui.dialog() as dialog, ui.card().classes('justify-center items-center'):
            ui.label('真的要清空所有消息吗(全局)？')
            ui.separator().classes('w-full')
            ui.label('清空').classes('text-red').on('click', lambda: clean_all_message(dialog)).style('cursor: pointer;')
            ui.label('取消').on('click', dialog.close).style('cursor: pointer;')
    dialog.open()

@ui.page('/')
async def main():
    ui.add_css('''
        .x-center {
            margin: auto;
            width: 50%;
        }
        ''')
    ui.colors(primary='rgb(68,157,72)')
    file = ''
    avatar_file = ''
    user_id = app.storage.user.get('username')

    avatar_db = db.get_user_data(user_id)[-1]
    if user_id in avatars:
        avatar = avatars[user_id]
    elif avatar_db:
        avatar = avatar_db
    else:
        avatar = default_avatar

    if not app.storage.user.get('authenticated', False):
        return RedirectResponse('/signin')

    display_messages.refresh()

    def logout():
        print(f'[user] user {user_id} logged out')
        app.storage.user.clear()
        ui.navigate.to('/signin')

    def handle_upload(e: events.UploadEventArguments):
        nonlocal file, send_file
        time_id = str(time()) + '_' + datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '_'
        file = os.path.join(file_path, time_id + ''.join(random.sample(random_dict, 50)) + '.' + e.name.split('.')[-1])
        with open(file, 'wb') as f:
            f.write(e.content.read())
        if file.split('.')[-1].lower() == 'heic':
            old_file = file
            file = '.'.join(file.split('.')[: -1]) + '.png'
            heic_to_png(old_file, file)
            os.remove(old_file)
        if use_resize:
            if file.split('.')[-1].lower() in ['png', 'jpg', 'jpeg']:
                file = resize(file, resize_tuple)
        else:
            file = resize(file, (1, 1))
        ui.notify('附件已上传', position='top', type='info', color='green')
    
    def handle_upload_avatar(e: events.UploadEventArguments):
        nonlocal change_avatar, avatar_file
        if e.name.split('.')[-1].lower() not in ['png', 'jpg', 'jpeg', 'heic']:
            ui.notify('文件格式错误', type='warning', position='top')
            return 
        time_id = str(time()) + '_' + datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '_'
        avatar_file = os.path.join(avatars_path, time_id + ''.join(random.sample(random_dict, 50)) + '.' + e.name.split('.')[-1])
        with open(avatar_file, 'wb') as f:
            f.write(e.content.read())
        if avatar_file.split('.')[-1].lower() == 'heic':
            old_file = avatar_file
            avatar_file = '.'.join(avatar_file.split('.')[:-1]) + '.png'
            heic_to_png(old_file, avatar_file)
            os.remove(old_file)
        if avatar_file.split('.')[-1].lower() in ['png', 'jpg', 'jpeg']:
            avatar_file = resize(avatar_file, avatar_resize_tuple)
        ui.notify('头像已上传', position='top', type='info', color='green')

    async def send() -> None:
        nonlocal file
        global email_time_before, ai_messages
        dialog.close()
        if not file:
            text_value = text.value
            text_value = mess_head.value + text_value + mess_tail.value
            text.value = ''
            if not text_value.strip().replace('</USEhtml>', '').replace('\n', ''):
                ui.notify('内容不能为空', type='info', position='top', color='green')
                return
            text_value = 'mess::' + text_value
        else:
            if not os.path.exists(str(file)):
                ui.notify('文件不存在', type='warning', position='top')
            else:
                text_value = 'file::' + file
        if text_value[:11] == 'mess::CMD::' and cmd_on and user_id in admin_users:
            if text_value[11:] == 'AI::RESET':
                output = '[CMD, AI] Reset AI by hand'
                print(output)
                messages.append(('cmd', '', f'mess::@{user_id}:{output}', datetime.now().strftime('%H:%M:%S')))
                display_messages.refresh()
                ai_messages = [{"role": "system", "content": ai_system},]
                ui.notify('AI已重置', type='info', position='top', color='green')
                return 
            elif text_value[11:] == 'HELP':
                print('[CMD] Help requested')
                messages.append(('cmd', '', f'mess::@{user_id}:{cmd_help}', datetime.now().strftime('%H:%M:%S')))
                display_messages.refresh()
                return
            elif text_value[11:17] == 'SETVAR':
                if '=' not in text_value[19:]:
                    error = '[CMD] SETVAR command: missing "=" sign'
                    messages.append(('cmd', '', f'mess::@{user_id}:{error}', datetime.now().strftime('%H:%M:%S')))
                    display_messages.refresh()
                    print(error)
                    return
                var_name = text_value[19:].split('=')[0].strip()
                var_value = text_value[19:].split('=')[1].strip()
                try:
                    exec(f'{var_name} = {var_value}', globals())
                    output = f'[CMD] Set variable {var_name} to {var_value}'
                    messages.append(('cmd', '', f'mess::@{user_id}:{output}', datetime.now().strftime('%H:%M:%S')))
                    display_messages.refresh()
                    print(output)
                except Exception as e:
                    error = f'[CMD] Error setting variable {var_name}: {e}'
                    messages.append(('cmd', '', f'mess::@{user_id}:{error}', datetime.now().strftime('%H:%M:%S')))
                    display_messages.refresh()
                    print(error)
                return
            elif text_value[11:17] == 'GETVAR':
                var_name = text_value[19:].strip()
                ret = ''
                try:
                    ret = eval(var_name, globals())
                    output = f'[CMD] Get variable {var_name} value: {ret}'
                    messages.append(('cmd', '', f'mess::@{user_id}:{output}', datetime.now().strftime('%H:%M:%S')))
                    display_messages.refresh()
                    print(output)
                except Exception as e:
                    error = f'[CMD] Error getting variable {var_name}: {e}'
                    messages.append(('cmd', '', f'mess::@{user_id}:{error}', datetime.now().strftime('%H:%M:%S')))
                    display_messages.refresh()
                    print(error)
                return
        file = ''
        stamp = datetime.now().strftime('%X')
        messages.append((user_id, '', text_value, stamp))
        print(f'[message] new message from {user_id}: "{text_value}"')
        display_messages.refresh()

        text_value_send = text_value[6:]
        email_time_now = time()
        if (email_time_now - email_time_before) > 75 and email_on:
            email_time_before = copy(email_time_now)
            if text_value[:6] == 'file::':
                text_value_send += '\n(请在浏览器中查看附件)'
            if 'admin' != user_id:
                await sendemail('kaixin168kx@163.com', f'你收到了一条来自{user_id}的消息【聊天室】', text_value_send)
        if ai_on and text_value[:11] != 'mess::CMD::' and text_value[:6] != 'file::':
            print(f'[AI] {user_id} is sending message to AI: {text_value_send}')
            await ai_message(text_value_send, user_id)

    def change_username():
        global replace_username, admin_users
        old_user = app.storage.user.get('username')
        new_user = new_name_input.value
        print(f'[user] {old_user} is trying to change username to {new_user}')
        if not new_user.strip():
            print(f'[user] new name {new_user} is empty')
            ui.notify('用户名不能为空', type='warning', position='top')
            return
        elif len(new_user) > 10:
            print(f'[user] new name {new_user} is too long')
            ui.notify('用户名不能超过10个字符', type='warning', position='top')
            return
        if db.change_username(old_user, new_user) is NO_EXISTS:
            app.storage.user['username'] = new_user
            if old_user in replace_username.keys():
                # 更新替换用户名字典, pop()方法用于删除字典中指定的键，并返回该键对应的值
                replace_username[new_user] = replace_username.pop(old_user)
            if old_user in admin_users:
                admin_users.remove(old_user)
                admin_users.add(new_user)
            ui.notify('用户名修改成功', type='info', position='top', color='green')
            change_name_dialog.close()
            ui.navigate.to('/')
        else:
            ui.notify('用户名已存在', type='warning', position='top')

    def change_useravatar():
        nonlocal avatar_file
        if not os.path.exists(avatar_file):
            ui.notify('未找到文件', type='warning', position='top')
            return
        db.change_useravatar(user_id, avatar_file)
        avatar_file = ''
        ui.notify('已修改头像')
        ui.navigate.to('/')
    
    with ui.dialog() as dialog, ui.column().classes('p-2'):
        # ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=.png').classes('max-w-full')
        ui.upload(on_upload=handle_upload, auto_upload=True, label='请选择附件', on_rejected=lambda: ui.notify('文件过大，拒绝上传'), max_files=1, max_file_size=60_000_000).classes('max-w-full')
        send_file = ui.button(icon='send', text='发送', on_click=send).props('size=md push').classes('bg-green x-center')

    with ui.dialog() as change_name_dialog, ui.card():
        new_name_input = ui.input('新的用户名', placeholder='请输入新的用户名').props('dense outlined').classes('w-full').on('keydown.enter', change_username)
        ui.button('修改', on_click=change_username).classes('bg-green x-center').props('size=md push')
    
    with ui.dialog() as change_avatar_dialog, ui.column().classes('p-2'):
        ui.upload(on_upload=handle_upload_avatar, auto_upload=True, label='请选择新的头像', on_rejected=lambda: ui.notify('文件过大，拒绝上传'), max_files=1, max_file_size=15_000_000).classes('max-w-full').props('accept=.png,.jpg,.jpeg,.heic')
        change_avatar = ui.button('修改', on_click=change_useravatar).classes('bg-green x-center').props('size=md push')

    ui.query('body').style(f'background-color: rgb(247,255,247)')
    with ui.left_drawer().style('background-color: rgb(233, 247, 239)') as left_drawer:
        with ui.card().style('background-color: rgb(147,207,150)').classes('p-1 w-full').props('flat bordered'):
            with ui.row().classes('items-center gap-3'):
                with ui.avatar(color="#B0B0B0", size='lg').on('click', lambda: ui.navigate.to(main)):
                    ui.image(avatar)
                with ui.column().classes('gap-0 p-0'):
                    ui.label(user_id[:9] + '...' if len(user_id) > 20 else user_id).classes('text-white').style('font-weight: bold;')
                    ui.label('管理员' if user_id in admin_users else '普通用户').classes('text-gray-200').style('font-size: 0.8em; font-weight: light;')
        ui.separator()
        with ui.scroll_area().classes('w-full h-full').props('content-style="padding: 0; gap: 0" content-active-style="padding: 0; gap: 0"'):
            with ui.column().classes('w-full items-stretch'):
                with ui.column().classes('w-full items-stretch gap-0'):
                    ui.label('快速操作:').classes('text-sm text-gray-600')
                    with ui.column().classes('gap-1 p-0 w-full items-stretch'):
                        ui.markdown('**可以用这个功能来快速屏蔽或指定用户**').classes('text-xs text-gray-600 p-0 gap-0')
                        mess_head = ui.textarea(label='消息前缀', placeholder='使用回车换行').props('dense outlined input-class=mx-3 autogrow')
                        # if user_id != '巴儿':
                        #     mess_head.set_value('^巴儿:')
                        mess_tail = ui.textarea(label='消息后缀', placeholder='使用回车换行').props('dense outlined input-class=mx-3 autogrow')
                ui.separator()
                with ui.column().classes('w-full items-stretch gap-0'):
                    ui.markdown('**长按或右击保存二维码，通过扫码添加站长微信**').classes('text-xs text-gray-600')
                    ui.image('/web_files/wechat.png')
                if user_id in admin_users:
                    ui.separator()
                    ui.label('开发者(谨慎使用):').classes('text-sm text-gray-600')
                    ui.button('开发者控制台', on_click=lambda: ui.navigate.to('/dev'), icon='developer_mode').classes('w-full').props('size=md flat')
                    ui.button('清空聊天记录', on_click=lambda: clean_messages(dialog_div), icon='chat').classes('w-full').props('size=md flat')
                    ui.button('查看实时日志', on_click=lambda: ui.navigate.to('/log'), icon='history').classes('w-full').props('size=md flat')
                    ui.button('网页运行代码', on_click=lambda: ui.navigate.to('/code'), icon='code').classes('w-full').props('size=md flat')
                ui.separator()
                ui.label('用户操作:').classes('text-sm text-gray-600')
                ui.button('修改账号名称', on_click=change_name_dialog.open, icon='edit').classes('w-full').props('size=md flat')
                ui.button('修改账号头像', on_click=change_avatar_dialog.open, icon='image').classes('w-full').props('size=md flat')
                ui.button('退出当前账号', on_click=logout, icon='logout').classes('w-full').props('size=md flat')
                ui.button('关于本聊天室', on_click=lambda: ui.navigate.to(about), icon='info').classes('w-full').props('size=md flat')

    with ui.header().style('background-color: rgb(147,207,150)').classes('items-center p-3'):
        with ui.row().classes('w-full items-center gap-2'):
            ui.button(text='请点击我', on_click=left_drawer.toggle).props('flat size=md').classes('text-white').style('font-weight: bold;')
            time_label = ui.label(text=str(datetime.now().strftime("%X"))).classes('text-lg absolute left-1/2 top-1/2 translate-x-[-50%] translate-y-[-50%]')
            ui.timer(1.0, lambda: time_label.set_text(str(datetime.now().strftime("%X"))))

    with ui.footer().classes('bg-white p-0').style('margin-top: 0; margin-bottom: 0;'):
        with ui.column().classes('w-full max-w-3xl mx-auto my-6 gap-1 p-3').style('margin-top: 0; margin-bottom: 0;'):
            with ui.row().classes('w-full no-wrap items-center gap-2 p-0'):
                with ui.button(on_click=dialog.open).props('size=md push fab color=accent padding="sm"')\
                    .classes('bg-green gap-0'):
                    ui.icon('library_add').style('font-size: 1em')
                text = ui.textarea(label='请输入消息').props('dense outlined input-class=mx-3 autogrow')\
                    .classes('flex-grow').on('keydown.shift.enter', send)
                ui.button(icon='send', on_click=send).props('size=md push').classes('bg-green')
            with ui.row().classes('w-full no-wrap p-0'):
                ui.space()
                ui.markdown(web_info).classes('text-xs text-green')

    await ui.context.client.connected()  # chat_messages(...) uses run_javascript which is only possible after connecting

    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch') as dialog_div:
        display_messages(user_id, dialog_div)

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
    if not allow_signup:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')

        with ui.dialog() as dialog, ui.card():
            ui.label('注册页面已关闭，请联系管理员：kaixin168kx@163.com')
            ui.button('返回', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
        # ui.navigate.to('/signin')
    else:
        def try_signup() -> None:
            if '燕湖' not in verify.value:
                print('school vierify error:', verify.value)
                with ui.dialog() as dialog, ui.card().classes('p-2'):
                    ui.markdown('学校验证错误，请填写**毕业证**上的**小学校名**')
                    ui.button('好的', on_click=dialog.close).classes('w-full bg-green').props('size=md push')
                dialog.open()
                return
            elif not username.value:
                print('[user] name {username.value}is empty')
                ui.notify('用户名不能为空', type='warning', position='top')
            elif not password.value:
                print('[user] password is empty')
                ui.notify('密码不能为空', type='warning', position='top')
            elif len(username.value) > 10:
                print(f'[user] name {username.value} is too long')
                ui.notify('用户名不能超过10个字符', type='warning', position='top')
                return
            # elif email.value and email.value.count('@') != 1:
            #     ui.notify('邮件格式错误', type='warning', position='top')
            # elif not email.value and email_switch.value:
            #     ui.notify('要使用邮箱通知，请输入邮箱', type='warning', position='top')
            else:
                if password.value == retry_password.value:
                    try_db = db.sign_up(username.value, password.value, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '')
                    if try_db == EXISTS:
                        print('[user] username exists:', username.value)
                        ui.notify('用户名已存在', type='warning', position='top')
                        return
                    ui.notify('注册成功', type='info', position='top', color='green')
                    ui.navigate.to('/signin')
                else:
                    ui.notify('密码和确认密码不相同', type='warning', position='top')

        ui.query('body').style(f'background-color: rgb(247,255,247)')
        with ui.card().classes('absolute-center').style(f'background-color: rgb(235,255,235)').props('flat bordered'):
            ui.label('注册用户').classes('subtitle')
            username = ui.input('用户').classes('fill').props('dense outlined')
            password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined')
            retry_password = ui.input('再次确认密码', password=True).classes('inline-flex').props('dense outlined')
            # def update_switch_val():
            #     if email.value:
            #         email_switch.set_value(True)
            #     else:
            #         email_switch.set_value(False)
            # email = ui.input('邮箱（可选）', on_change=update_switch_val).classes('inline-flex').props('dense outlined').on('keydown.enter', try_signup)
            # email_switch = ui.switch('邮箱通知').props('icon="mail" color="green"').bind_visibility_from(email, 'value')
            ui.label('身份验证').classes('text-md text-gray-600')
            verify = ui.input('填写小学校名').classes('inline-flex').props('dense outlined').on('keydown.enter', try_signup)
            with ui.button('注册', on_click=try_signup).classes('x-center bg-green').props('size=md push'):
                ui.tooltip('立即注册用户').classes('bg-green').props('transition-show="scale" transition-hide="scale"')
            with ui.row().classes('w-full items-center gap-2'):
                ui.space()
                ui.link('登录用户', signin).classes('text-xs text-green')
        with ui.footer().style(f'background-color: rgb(247,255,247)'), ui.row().classes('w-full no-wrap'):
            ui.space()
            ui.markdown(web_info).classes('text-xs text-green')
        return None

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
        }
        .code-font {
            font-family: monospace;
        }''')
    ui.colors(primary='rgb(68,157,72)')
    user_id = app.storage.user.get('username')
    if user_id not in admin_users:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')
        with ui.dialog() as dialog, ui.card():
            ui.label('权限不足，无法访问开发者控制台')
            ui.button('回到主页', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
    else:
        def change_var():
            try:
                exec(f'''global {var.value}
{var.value} = {val.value}''', globals())
                err.set_text(f'output> {var.value} = {val.value}')
            except BaseException as e:
                err.set_text('output> [ERR: ' + str(e) + ']')
        def get_var():
            try:
                val0.set_text(str(eval(var0.value)))
            except BaseException as e:
                val0.set_text('[ERR: ' + str(e) + ']')
        def update_webinfo():
            global web_info
            web_info = f'**苏ICP备2025180468号 | Copyright © 2025 宋昕哲 | v{VERSION}**'
        def change_obj_var():
            try:
                var_data = globals()
                exec(f'''global {var_obj.value}
ret = {var_obj.value}.{val_obj.value}''', var_data)
                err_obj.set_text(f'output> {var_data["ret"]}')
            except BaseException as e:
                err_obj.set_text('output> [ERR: ' + str(e) + ']')
        ui.query('body').style(f'background-color: rgb(247,255,247)')
        ui.label(f'Hi, {user_id}').classes('subtitle')
        with ui.card().classes('w-full'), ui.row().classes('w-full') as dialog_div:
            ui.link('实时日志', dev_log).classes('text-green')
            ui.link('运行代码', dev_code).classes('text-green')
            ui.link('关于', about).classes('text-green')
            ui.link('主页', main).classes('text-green')
        ui.button('清空聊天记录', on_click=lambda: clean_messages(dialog_div)).classes('bg-green').props('size=md push')
        ui.button('更新webinfo', on_click=update_webinfo).classes('bg-green').props('size=md push')
        with ui.card():
            ui.label('修改变量：')
            with ui.row().classes('w-full'):
                ui.label('将变量  ').classes('code-font')
                var = ui.input('var').props('dense outlined').classes('code-font')
                ui.label('  设为  ').classes('code-font')
                val = ui.input('val').props('dense outlined').classes('code-font')
                ui.button('修改', on_click=change_var).classes('bg-green').props('size=md push')
            err = ui.label('output> ').classes('code-font')
        with ui.card():
            ui.label('查看变量：')
            with ui.row().classes('w-full'):
                ui.label('变量  ').classes('code-font')
                var0 = ui.input('var').props('dense outlined').classes('code-font')
                ui.label('  的值是  ').classes('code-font')
                val0 = ui.label('[val]').classes('code-font')
                ui.button('查看', on_click=get_var).classes('bg-green').props('size=md push')
        with ui.card():
            ui.label('修改Object对象：')
            with ui.row().classes('w-full'):
                ui.label('对Object  ').classes('code-font')
                var_obj = ui.input('var').props('dense outlined').classes('code-font')
                ui.label('  执行操作  ').classes('code-font')
                val_obj = ui.input('val').props('dense outlined').classes('code-font')
                ui.button('执行', on_click=change_obj_var).classes('bg-green').props('size=md push')
            err_obj = ui.label('output> ').classes('code-font')
        with ui.card().classes('w-full'):
            ui.markdown('变量(`globals()`):')
            ui.code(str(globals())).classes('w-full')

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
    if user_id not in admin_users:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')
        with ui.dialog() as dialog, ui.card():
            ui.label('权限不足，无法访问开发者控制台')
            ui.button('回到主页', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
    else:
        ui.query('body').style(f'background-color: rgb(247,255,247)')
        ui.link('主页', main).classes('text-green')
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
    if user_id not in admin_users:
        def return_to_main_page() -> None:
            dialog.close()
            ui.navigate.to('/')
        with ui.dialog() as dialog, ui.card():
            ui.label('权限不足，无法访问开发者控制台')
            ui.button('回到主页', on_click=return_to_main_page).classes('x-center bg-green').props('size=md push')
        dialog.open()
    else:
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

        ui.link('主页', main).classes('text-green')
        ui.label('运行Python代码(exec)或使用更新补丁:')
        ui.label('!危险操作!').classes('text-red subtitle')
        with ui.row():
            ui.markdown('按下***运行按钮***将会**自动执行`main`函数中的内容**，并输出`main函数`的返回值，**不会输出除`main的返回值`外的任何其他值（如`print`）**')
            ui.button('运行', on_click=run_code).classes('bg-green').props('size=md push')
        code = ui.codemirror('', language='Python', theme='githubLightStyle').classes('w-full h-100 code-font')
        ui.label('输出')
        code_output = ui.log(max_lines=1000).classes('w-full h-100 code-font')
        code_output.push('output > \n')

@ui.page('/about')
def about() -> None:
    ui.query('body').style(f'background-color: rgb(247,255,247)')
    ui.link('主页', main).classes('text-green')
    ui.markdown(about_text).style('word-wrap:break-word;word-break:normal; ')

@ui.page('/dir/{dir}')
def show_files_in_files(dir: str) -> None:
    if not os.path.exists(dir):
        ui.markdown(f'**目录 `{dir}` 不存在!**').classes('text-red')
        return
    with ui.column().classes('w-full gap-0 p-0'):
        for i in os.listdir(dir):
            ui.markdown(f'[/{dir}/{i}](/{dir}/{i})').classes('p-0 gap-0')

def run(**kwargs) -> None:
    app.add_static_files(file_url, file_path)
    app.add_static_files(avatars_url, avatars_path)
    app.add_static_files(database_url, database_path)
    app.add_static_files(web_files_url, web_files_path)
    ui.run(**kwargs)
