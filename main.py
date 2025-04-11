from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import Client, app, ui
from datetime import datetime
from typing import List, Tuple
from uuid import uuid4

unrestricted_page_routes = {'/login'}
messages: List[Tuple[str, str, str, str]] = []

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
        app.storage.user.update({'username': username.value, 'authenticated': True})
        ui.navigate.to(app.storage.user.get('referrer_path', '/'))
    with ui.card().classes('absolute-center').style(f'background-color: #edf7ff'):
        ui.label('欢迎来到聊天室').classes('subtitle')
        username = ui.input('用户').classes('fill').props('dense outlined')
        password = ui.input('密码', password=True).classes('inline-flex').props('dense outlined')
        with ui.button('登录', on_click=try_login).classes('x-center').props('rounded outline'):
            ui.tooltip('登录到聊天室').classes('bg-green')

@ui.refreshable
def chat_messages(own_id: str) -> None:
    for user_id, avatar, text, stamp in messages:
        ui.chat_message(text=text, stamp=stamp, avatar=avatar, sent=own_id == user_id, name=app.storage.user.get('username'))
    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

@ui.page('/')
async def main():
    if not app.storage.user.get('authenticated', False):
        return RedirectResponse('/login')

    def logout():
        app.storage.user.clear()
        ui.navigate.to(app.storage.user.get('referrer_path', '/'))

    ui.label(app.storage.user.get('username'))
    ui.button('注销', on_click=logout)

    def send() -> None:
        stamp = datetime.utcnow().strftime('%X')
        messages.append((user_id, avatar, text.value, stamp))
        text.value = ''
        chat_messages.refresh()

    user_id = str(uuid4())
    avatar = f'https://robohash.org/{user_id}?bgset=bg2'

    ui.add_css(r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}')
    with ui.footer().classes('bg-white'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            with ui.avatar().on('click', lambda: ui.navigate.to(main)):
                ui.image(avatar)
            text = ui.input(placeholder='message').on('keydown.enter', send) \
                .props('rounded outlined input-class=mx-3').classes('flex-grow')
        ui.markdown('simple chat app built with [NiceGUI](https://nicegui.io)') \
            .classes('text-xs self-end mr-8 m-[-1em] text-primary')

    await ui.context.client.connected()  # chat_messages(...) uses run_javascript which is only possible after connecting
    with ui.column().classes('w-full max-w-2xl mx-auto items-stretch'):
        chat_messages(user_id)

ui.run(port=66, storage_secret='THIS_NEEDS_TO_BE_CHANGED')