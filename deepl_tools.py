"""
https://www.deepl.com/en/login
"""

import json
import re
from tkinter import Tk
import deepl as dl

TRANSLATOR = None
DISABLED = False

def get_translator():
    global TRANSLATOR
    if not TRANSLATOR:
        import core
        with open(core.CONFIG_JSON, 'r', encoding='utf-8') as f:
            import core
            AUTH_KEY = json.load(f)['deepl_auth_key']
            TRANSLATOR = dl.Translator(AUTH_KEY)
    return TRANSLATOR

def deepl(text):
    global DISABLED
    try:
        if DISABLED:
            return None
        text = get_translator().translate_text(text, source_lang="DE",  target_lang="PL").text
    except Exception as ex:
        if str(ex) == 'Quota for this billing period has been exceeded, message: Quota Exceeded':
            print('Deepl ERROR:\n' + 'Quota for this billing period has been exceeded.')
            DISABLED = True
        return None
    return text

TARGET_LANGS = {
    "ZH": "Chinese (simplified)",
    "PL": "Polish",
    "EN-GB": "English (British)",
    "EN-US": "English (American)",
    "ES": "Spanish",
    "RU": "Russian"
}

def get_next_target_lang(target_lang):
    tls = [*TARGET_LANGS]
    return tls[(tls.index(target_lang) + 1) % len(tls)]

def deplClipboardText(target_lang="PL"):
    try:
        root = Tk()
        root.withdraw()
        try:
            org = root.clipboard_get()
        except:
            return 'Nothing in clipboard to translate!', None
        org = re.sub(r'[^\w\s\x00-\x7F]', u'', org, flags=re.UNICODE)
        org = re.sub(r'\n+', '\n', org)
        org = re.sub(r' +', ' ', org)
        global DISABLED
        DISABLED = False
        retval = org, get_translator().translate_text(org, target_lang=target_lang).text
        root.clipboard_clear()
        root.clipboard_append(retval[1])
        root.update()
        root.destroy()
    except Exception as ex:
        # import pdb; pdb.set_trace()
        #   if str(ex) == 'DeepLException("Bad request, message: Value for 'target_lang' not supported.")'
        retval = org, 'deepl ERROR:\n' + str(ex)
    
    return retval