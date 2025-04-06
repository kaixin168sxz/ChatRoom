from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import Client, app, ui

unrestricted_page_routes = {'/login'}

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

@ui.page('/')
async def main():
    if not app.storage.user.get('authenticated', False):
        return RedirectResponse('/login')
    ui.label(app.storage.user.get('username'))
    def logout():
        app.storage.user.clear()
        ui.navigate.to(app.storage.user.get('referrer_path', '/'))
    ui.button('注销', on_click=logout)

ui.run(port=66, storage_secret='THIS_NEEDS_TO_BE_CHANGED')