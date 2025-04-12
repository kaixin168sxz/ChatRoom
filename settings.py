EXISTS: str = 'Exists'
NO_EXISTS: str = 'NoExists'
OK: str = 'DB-200'

PRINT = print

def print(text: str) -> None:
    PRINT(text)
    with open('./chatroom.log', 'a+') as f:
        text_nocolor = ''
        text_list = text.split('\n')
        for text in text_list:
            if '\033' in text:
                tmp_text = ''
                tmp_list = text.split('\033')
                for tmp in tmp_list:
                    if 'm' in tmp:
                        tmp_text += ''.join(tmp.split('m')[1:])
                    else:
                        tmp_text += tmp
                text = tmp_text
            text_nocolor += text + '\n'

        f.write(text_nocolor + '\n')