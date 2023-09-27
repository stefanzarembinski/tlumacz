import traceback
import threading
from random import randrange
import PySimpleGUI as sg # https://realpython.com/pysimplegui-python/
# pyinstaller tlumacz.py
# pyinstaller --onefile --distpath ./tlumaczexe tlumacz.py # --noconsole
# https://github.com/stefanzarembinski/tlumaczexe
# https://github.com/stefanzarembinski/tlumacz

# install git: https://git-scm.com/download/win
# git branch -a
# git pull origin main
# git pull

from core import *
import deepl_tools as dl
from offer_de import *
from offer_pl import *
from teacher import *
from gif import *
import database

THEMES = ['DarkGreen4', 'DarkAmber', 'HotDogStand', 'Python', 'DarkPurple5', 'GrayGrayGray']
sg.theme(THEMES[randrange(len(THEMES))])

TRANSLATE = 'translate'
TEACH = 'teach'
RUNNING = False
ERROR = None
WARNINGS = None

# gifs = [ring_blue, red_dots_ring, ring_black_dots, ring_gray_segments, ring_lines, blue_dots, bar_striped, line_boxes, line_bubbles]
GIF = blue_dots

args_json = ARGS_JSON
try:
    with open(CONFIG_JSON, 'r', encoding='utf-8') as f:
        args_json = json.load(f)
except:
    pass

def save_config(values):
    for param in ARGUMENTS:
        args_json[param] = values[param]
    args_json[OFFER_DE] = values[OFFER_DE]
    args_json[OFFER_PL] = values[OFFER_PL]
    args_json[TEACH_DE] = values[TEACH_DE]
    args_json[TEACH_PL] = values[TEACH_PL]

    with open(CONFIG_JSON, 'w', encoding='utf-8') as f:
        json.dump(args_json, f, indent=4)


def param_value(param):
    return args_json[param] if param in args_json else ''


teach = [
    [
        sg.Text('niemiecka oferta:'), 
        sg.InputText(
            param_value(TEACH_DE), key=TEACH_DE, size=(100, 1), 
            disabled=True, 
            disabled_readonly_background_color='white',
            disabled_readonly_text_color='black'), 
        sg.FileBrowse('Szukaj', key='Browse', file_types=DOCUMENT_PDF)
    ], 
    [
        sg.Text('polska oferta:'), 
        sg.InputText(
            param_value(TEACH_PL), key=TEACH_PL, size=(100, 1), 
            disabled=True, 
            disabled_readonly_background_color='white',
            disabled_readonly_text_color='black'), 
        sg.FileBrowse('Szukaj', key='Browse', file_types=DOCUMENT_MS_WORD)
    ],
    [
        sg.Checkbox('Debug', key='-DEBUG-', default=DEBUG, enable_events=True),
        sg.Button('REGEX', key='-REGEX-', enable_events=True),
        sg.Button('Translate Clipboard', key='-TRANSLATE_CLIPBOARD-', enable_events=True),
        sg.Text('PL', key='-TARGET_LANG-', size=(5, 1), enable_events=True),
    ],
    [sg.Button('UCZ SIĘ TERAZ', key='-DO_TEACH-')],
]


translate = [
    
    [   sg.Text('nazwa:', ), 
        sg.InputText(param_value(CLIENT_NAME), key=CLIENT_NAME)
    ],
    [   sg.Text('adres:'), 
        sg.InputText(param_value(CLIENT_ADDRESS), key=CLIENT_ADDRESS)
    ],
    [
        sg.Text('kod pocztowy:'), 
        sg.InputText(param_value(CLIENT_ZIP_CODE), key=CLIENT_ZIP_CODE)
    ],
    [
        sg.Text('imię i nazwisko:'), 
        sg.InputText(param_value(CLIENT_ADDRESSEE), key=CLIENT_ADDRESSEE)
    ],
    [
        sg.Text('miejsce instalacji:'), 
        sg.InputText(param_value(INSTALLATION_PLACE), key=INSTALLATION_PLACE)
    ],
    [
        sg.Text(OFFER_VALIDITY + ':'), 
        sg.InputText(param_value(OFFER_VALIDITY), key=OFFER_VALIDITY)
    ],
    [
        sg.Text('niemiecka oferta:'), 
        sg.InputText(
            param_value(OFFER_DE), key=OFFER_DE, size=(100, 1), 
            disabled=True, 
            disabled_readonly_background_color='white',
            disabled_readonly_text_color='black'), 
        sg.FileBrowse('Szukaj', key='Browse', file_types=DOCUMENT_PDF)
    ], 
    [
        sg.Text('polska oferta:'), 
        sg.InputText(
            param_value(OFFER_PL), key=OFFER_PL, size=(100, 1), 
            disabled=True, 
            disabled_readonly_background_color='white',
            disabled_readonly_text_color='black'), 
        sg.FileSaveAs(
            'Szukaj albo Nowy', key='Browse', file_types=DOCUMENT_MS_WORD, 
            default_extension=DOCUMENT_MS_WORD[1][1], 
            initial_folder=args_json[OFFERS_DIR]), 
    ], 
    [
        sg.Text('data:'), 
        sg.InputText(param_value(DATE), key=DATE)
    ],
    [sg.Text('rabat:'), sg.InputText(
        param_value(DISCOUNT), key=DISCOUNT, enable_events=True)],
    [sg.Button('TŁUMACZ TERAZ', key='-DO_TRANSLATE-')],
]


BTNS = {
    TEACH: sg.Button('UCZ SIĘ', key=TEACH), 
    TRANSLATE: sg.Button('TŁUMACZ', visible=False, key=TRANSLATE)

}


layout = [
    [
        sg.Button('ZAMKNIJ', key='Exit'),
        BTNS[TEACH],
        BTNS[TRANSLATE], 
    ],
    [
        sg.Column(teach, visible=False, key='layout_teach'), 
        sg.Column(translate, visible=True, key='layout_translate'),
        sg.Image(
            data=GIF, 
            enable_events=True, 
            # background_color='', 
            key='-RUNNING-', 
            right_click_menu=['UNUSED', 'Exit'],
            visible=False),
    ],
    [sg.Text(f'folder roboczy: {DIR}')],
]


class Teach(threading.Thread):
    def run(self,*args,**kwargs):
        global RUNNING
        global ERROR
        global WARNINGS

        def clean():
            window['-RUNNING-'].update(visible=False)
            global RUNNING
            RUNNING = False 

            window[f'layout_{TEACH}'].update(visible=True)
            window[TEACH_PL].update(value=param_value(TEACH_PL))
            window[TEACH_DE].update(value=param_value(TEACH_DE))
            BTNS[TRANSLATE].update(visible=True)
                       
        try:
            RUNNING = True
            ERROR = None
            WARNING_LIST.clear()

            window[f'layout_{TEACH}'].update(visible=False)
            BTNS[TRANSLATE].update(visible=False)

            window['-RUNNING-'].update(visible=True)
            Teacher(args_json).teach()
            clean()
            if WARNING_LIST:
                WARNINGS = ''.join(WARNING_LIST)
        except Exception as ex:
            ERROR = (ex, traceback.format_exc())
            clean()         


class Translate(threading.Thread):
    def run(self,*args,**kwargs):
        global RUNNING
        global ERROR

        def clean():
            window['-RUNNING-'].update(visible=False)
            global RUNNING
            RUNNING = False

            window[f'layout_{TRANSLATE}'].update(visible=True)
            window[OFFER_PL].update(value=param_value(OFFER_PL))
            window[OFFER_DE].update(value=param_value(OFFER_DE))
            BTNS[TEACH].update(visible=True)
        
        try:
            RUNNING = True
            ERROR = None

            window[f'layout_{TRANSLATE}'].update(visible=False)
            BTNS[TEACH].update(visible=False)
            
            window['-RUNNING-'].update(visible=True)
            offer = OfferDe(args_json=args_json)
            offer.parse()
            offer.write_offer_pl_groups()
            offer.save_pl()
            clean()
        except Exception as ex:
            ERROR = (ex, traceback.format_exc())
            clean()


window = sg.Window('Dla Wioletki', layout)
_layout = TRANSLATE  # The currently visible layout

if not (path.exists(REGEX_JSON)):
    ERROR = (Exception(f""",
File 
    "{REGEX_JSON}"
does not exist in the current directory which is
    "{DIR}".

Change the working directory, perhaps.
"""), None)

while True:   
    event, values = window.read(timeout=100)
    if event in (None, 'Exit'):
        break

    if event == DISCOUNT and len(values[DISCOUNT]) and values[DISCOUNT][-1] not in ('0123456789'):
        # delete last char from input
        window[DISCOUNT].update(values[DISCOUNT][:-1])

    if RUNNING:
        window['-RUNNING-'].update_animation(GIF, time_between_frames=200)

    if WARNINGS:
        sg.popup_scrolled(WARNINGS, title='Warnings')
        WARNINGS = None

    if ERROR:
        error_msg = str(str(ERROR[0])) if isinstance(ERROR[0], HealthyException) else ERROR[1]
        if error_msg is None:
            error_msg = str(str(ERROR[0]))

        sg.popup(error_msg, title='Error')
        if not isinstance(ERROR[0], HealthyException):
            break
        ERROR = None

    if event == '-DEBUG-':
        DEBUG = values['-DEBUG-']
        print(f'DEBUG is {DEBUG} now.')

    if event == '-REGEX-':
        try:
            sg.popup_scrolled(database.regex_in_database(), title='REGEX', size=(80, 10))
        except Exception as ex:
            sg.popup(traceback.format_exc(), title='Error')


    if event == '-TARGET_LANG-':
        window['-TARGET_LANG-'].update(
            dl.get_next_target_lang(window['-TARGET_LANG-'].DisplayText))

    if event == '-TRANSLATE_CLIPBOARD-':
        org, pl = dl.deplClipboardText(window['-TARGET_LANG-'].DisplayText)
        transl = f'''
### Clipboard text translated:
{pl}
''' if pl else ''
        msg = f'''
### Clipboard text:
{org}
{transl}
'''
        print(msg)
        sg.popup(msg, title='Translate Clipboard')
        
    if event == '-DO_TRANSLATE-':
        # import pdb; pdb.set_trace()
        save_config(values)
        Translate().start()
    
    if event == '-DO_TEACH-':
        save_config(values)
        Teach().start()
    
    if event in (TRANSLATE, TEACH):
        window[f'layout_{_layout}'].update(visible=False)
        BTNS[_layout].update(visible=True)
        _layout = event
        window[f'layout_{_layout}'].update(visible=True)
        BTNS[_layout].update(visible=False)


window.close()