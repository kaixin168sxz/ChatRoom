from nicegui import ui

with ui.element('q-fab').props('icon=navigation color=green'):
    ui.element('q-fab-action').props('icon=train color=green-5') \
        .on('click', lambda: ui.notify('train'))
    ui.element('q-fab-action').props('icon=sailing color=green-5') \
        .on('click', lambda: ui.notify('boat'))
    ui.element('q-fab-action').props('icon=rocket color=green-5') \
        .on('click', lambda: ui.notify('rocket'))

ui.run()
