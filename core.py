import os
import os.path as path
import json
import re
import pickle
import tkinter as tk
from tkinter import filedialog
import sqlite3
import deepl_tools as dlt

DIR = os.getcwd()
CONFIG_JSON = path.join(DIR, 'args.json')
REGEX_JSON = path.join(DIR, 'regex.json')
GROUPS_JSON = path.join(DIR, 'groups.json')
ARTICLES_JSON = path.join(DIR, 'articles.json')

OFFERS_DIR = 'oferty'
OFFER_DE = 'offer_de'
OFFER_PL = 'offer_pl'
TEACH_DE = 'teach_de'
TEACH_PL = 'teach_pl'
TEMPLATE_DOC = path.join(DIR, 'template.docx')
TEMP_DOC = path.join(DIR, 'oferta.docx')

DB = path.join(DIR, 'tlumacz.db')
ANGEBOT_NR = 'angebot_nr'
GROUP_INDEX = 'id'
GROUP_NAME = 'name'
DE = 'de'
PL = 'pl'
PARAMS = 'parametry'
ID = 'indeks'
HASH = 'name_hash'
ID_DESCR = 'opis'
ID_PARAMS = 'parametry'
ARTICLE = 'article'
DEBUG = False
JUST_TRANSLATED = 'just translated'
MEHRPRIES = r'Mehrpreis (für)?'

ARTICLES = 'czesci'
ARTICLES_INDEX = 'articles_index'
GROUPS = 'grupy'
WORDS = 'slowa'
ARGS_JSON = {
    "nazwa klienta": "Bart Sp. z o.o.",
    "adres klienta": "Sulnowo 53 g",
    "kod pocztowy klienta": "86-100 \u015awiecie",
    "imi\u0119 nazwisko klienta": "Pan Bartosz Dziepak",
    "miejsce instalacji": "Bart w \u015awieciu \u2013 Sulnowie",
    "data": "29.03.2022",
    "termin wa\u017cno\u015bci oferty": "30. kwietnia 2022",
    "rabat": "23000",
    "offer_de": "",
    "teach_pl": "",
    "offer_pl": "",
    "oferty": ""
}
CANNOT_PARSE = 'TŁUMACZ NIE ROZUMIE!'
WARNING_LIST = []

def solidHash(text:str):
  text = re.sub(r'[\s]*', '', text)
  hash=0
  for ch in text:
    hash = ( hash*281  ^ ord(ch)*997) & 0xFFFFFFFF
  return hash

def commonchars(a, b):
    a = [*re.sub(r'[\s]*', '', a)]
    b = [*re.sub(r'[\s]*', '', b)]
    common = []
    for _a in a:
        if _a in b:
            b.remove(_a)
            common.append(_a)
    return len(common)

def debug(*args):
    if DEBUG:
        print(*args)


class Group:
    def __init__(self):
        self.index = None
        self.name = None
        self.comment = None
        self.articles = []


class Descr:
    def __init__(self, de=None, pl=None):
        self.de = de
        self.pl = pl or de


class Param:
    def __init__(self, value, de=None, pl=None):
        self.value = value
        self.de = de
        self.pl = pl or de


class Article:
    def __init__(
            self, article_id, de=None, pl=None, 
            count=None, price=None, cost=None):
        """
        Translating while reading an original offer: Arguments `article_id` and `de` are both 
        defined. If the `article_id` argument is in the database, get the corresponding 
        `_Article` object and compare its `de` component with the `de` argument; update 
        the database if they differ.

        Otherwise, create a new database entry with both `de` and `pl` article
        names set to the `de` argument.

        Learning: Arguments `article_id` and `pl` are both defined. While reading a translated 
        offer, if the `article_id` argument is in the database, get the corresponding `_Article` 
        object. If the attribute `pl` of the object differs from the `pl` argument, update the 
        database.

        Otherwise, create a new database entry with both `de` and `pl` object attributes
        set to the `pl` argument.
        """
        article_id = article_id.strip()
        if de:
            de = re.sub('\?+$', '', de)
            de = de.strip()
        if pl:
            pl = pl.strip()
        
        self.article_db = _Article(article_id, de, pl)
        self.price = price
        self.cost = cost
        self.count = count
        self.is_optional = False

    def set_descr(self, de=None, pl=None):
        """
        Translating while reading an original offer: Arguments `article` and `de` are 
        both defined. Compare `self.article.descr.de`attribute with the `de` argument; update 
        the database if they differ. 

        Learning: Arguments `article_id` and `pl` are both defined. Compare 
        `self.article.descr.pl` attribute with the `pl` argument; update the database if they 
        differ. 
        """
        assert not ((de is None) and (pl is None))
        self.article_db.set_descr(de, pl)

        return self

    def set_param(self, value, de=None, pl=None):
        """
        Translating while reading an original offer: Argument `de` is defined. Compare 
        `self.article.params[value].de`attribute with the `de` argument; update the database if 
        they differ. 

        Learning: Argument `pl` is defined. Compare `self.article.params[value].pl` attribute 
        with the `pl` argument; update the database if they differ. 
        """
        assert not ((de is None) and (pl is None))
        self.article_db.set_param(value, de, pl)


class FixedGroups:
    instance = None
    def get():
        if FixedGroups.instance is None:
            FixedGroups.instance = FixedGroups()
        return FixedGroups.instance
    
    def __init__(self):
        with open(GROUPS_JSON, 'r', encoding='utf-8') as f:
            self.groups_json = json.load(f)


class Regex:
    instance = None
    def get():
        if Regex.instance is None:
            Regex.instance = Regex()
        return Regex.instance
    
    def __init__(self):
        self.regex_json = None
        self._is_regex = False
        self.reload()

    def reload(self):
        with open(REGEX_JSON, 'r', encoding='utf-8') as f:
            self.regex_json = json.load(f)

    def dump(self):        
        with open(REGEX_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.regex_json, f, indent=4, sort_keys=True)

    def regex_name(self, article_id, article_name_de):
        if article_id in self.regex_json:
            groups = re.match(self.regex_json[article_id][0], article_name_de).groups()                         
            return self.regex_json[article_id][1].format(*groups)
        return article_name_de
    
    def is_regex(self, article_id):
        if article_id in self.regex_json:
            return self.regex_json[article_id]
        return False

class _Article:
    """
    """
    def __init__(self, article_id, de=None, pl=None):
        article_id = article_id.strip()
        if pl:
            pl = pl.strip()
        if de:
            de = de.strip()
        assert de or pl

        self.is_regex = False
        self.descr = None
        self.params = None
        self.article_id = article_id
        self.is_translated = False
        # self.pl = pl or de
        _article = None

        con = sqlite3.connect(DB)
        cur = con.cursor()

        if de:
            # if article_id == '0000361800':
            #     import pdb; pdb.set_trace()
            self.is_regex = Regex.get().is_regex(article_id)
            if self.is_regex:
                self.de = de
                self.pl = Regex.get().regex_name(article_id, de)
                self.is_translated = True
                _article = True

            if not _article:
                cur.execute(f"SELECT * FROM {ARTICLES} WHERE {ID}='{article_id}' AND {HASH}={solidHash(de)}")
                _article = cur.fetchone()
                if _article:
                    self.__dict__.update(pickle.loads(_article[2]).__dict__)
            
            if not _article:
                self.pl = pl or de
                self.de = de
                self.is_translated = bool(pl)
                if not de == CANNOT_PARSE:
                    # import pdb; pdb.set_trace()
                    cur.execute(
                        f"INSERT INTO {ARTICLES} VALUES (?, ?, ?)",
                        (self.article_id, solidHash(self.de), pickle.dumps(self)))
                else:
                    _article = True
        else: # Call from the teatcher. 'pl' is set if 'de' is not. 
            cur.execute(f"SELECT * FROM {ARTICLES} WHERE {ID}='{article_id}'")
            _articles = cur.fetchall()

            if not _articles:                        
                self.is_regex = Regex.get().is_regex(self.article_id)
                if self.is_regex:
                    self.pl = self.is_regex[1]
                    self.de = self.is_regex[0]
                    self.is_translated = True
                    _article = True                    
                else:
                    '''
                    Unknown to the databade article found in a translated offer. Misspelled article ID? 
                    '''
                    warning = f'''
    Element o nazwie "{pl}", w polskiej przetłumaczonej ofercie, nie ma odpowiednika w oryginalnej ofercie.
    Indeks tego elementu jest "{article_id}". Może jest błędnie przepisany?
    '''
                    WARNING_LIST.append(warning)
                    print(warning)
                    self.de = CANNOT_PARSE
                    self.pl = pl
                    _article = True    
                
            if not _article: 
                for _art in _articles:
                    if pickle.loads(_art[2]).pl == pl:
                        _article = _art
                        self.__dict__.update(pickle.loads(_article[2]).__dict__)
                        self.pl = pl
                        break

            if not _article:
                maxmatch = 0
                maxindex = 0
                for i in range(len(_articles)):
                    _de = pickle.loads(_articles[i][2]).de
                    match = commonchars(pl, _de)
                    if match > maxmatch:
                        maxmatch = match
                        maxindex = i                 
                _article = _articles[maxindex]
                self.__dict__.update(pickle.loads(_article[2]).__dict__)
                self.is_translated = JUST_TRANSLATED
                self.pl = pl
        con.commit()
        con.close()

        if pl and not self.is_regex and not self.de == CANNOT_PARSE:
            self.update()
            if self.is_translated:
                if (self.pl != pl):
                    if self.pl == self.de:
                        self.pl = pl
                        self.update()
                    else:
                        yn = 'y'
                        print(f'''
Changing polish name -
previous:
{self.de}: {self.pl}
new:
{self.de}: {pl}
''')                    
                        yn = input(f'"y" ENTER to change, empty ENTER to skip: ')
                        if yn == 'y':
                            self.pl = pl
                            self.update()
            else:
                self.is_translated = True
                self.update()
                self.is_translated = JUST_TRANSLATED

    def update(self):
        if self.is_regex:
            return self
        
        is_translated = self.is_translated
        self.is_translated = bool(self.is_translated)
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            f"UPDATE {ARTICLES} SET {ARTICLE}=? WHERE {ID}=? AND {HASH}=?",
            (pickle.dumps(self), self.article_id, solidHash(self.de)))
        con.commit()
        con.close()
        self.is_translated = is_translated
        return self

    def set_descr(self, de, pl):
        assert not ((de is None) and (pl is None))
        if not self.descr and not de and not pl:
            return
        if self.is_regex:
            return

        if de:
            de = de.strip()
        if pl:
            pl = pl.strip()

        if not self.descr:
            if pl is None and not self.is_translated: pl = de
            if de is None: de = pl
            if de or pl:
                self.descr = Descr(de, pl)
                self.update()
        
        if self.descr and (de is not None) and (self.descr.de != de):
            self.descr.de = de
            self.update()
        if self.descr and (pl is not None) and (self.descr.pl != pl):
            self.descr.pl = pl
            self.update()
        

    def set_param(self, value, de=None, pl=None):
        """
        Translating while reading an original offer: Argument `de` is defined. Compare 
        `self.article.params[value].de`attribute with the `de` argument; update the database if 
        they differ. 

        Learning: Argument `pl` is defined. Compare `self.article.params[value].pl` attribute 
        with the `pl` argument; update the database if they differ. 
        """
        assert not ((de is None) and (pl is None))

        if de:
            de = de.strip()
        if pl:
            pl = pl.strip()

        value = value.strip()
        if self.params is None:
            self.params = {}        

        if not value in self.params:
            if pl is None: pl = de 
            if de is None: de = pl
            self.params[value] = Param(value, de, pl)
            self.update()
        else:
            param = self.params[value]
            if de and not param.de == de:
                param.de = de
                self.update()
            if pl and not param.pl == pl:
                param.pl = pl
                self.update()

    def __str__(self):
        str = f'{self.article_id}: {self.pl} ({self.de})'
        if self.descr:
            str += '\n'
            str += f'\n{self.descr.pl}\n\n{self.descr.de}'
        if self.params:
            str += '\n'
            for value, param in self.params.items():
                str += f'\n{value}: {param.pl} ({param.de})'
        return str


class HealthyException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


def open_offer_file(offer_file, title, filetypes, process=None, args_json=None, new=False):
    # import pdb; pdb.set_trace()
    verify = args_json is None
    _offer_file = None
    processed = None

    if args_json is None:
        with open(CONFIG_JSON, 'r', encoding='utf-8') as f:
            args_json = json.load(f)
    
    if offer_file in args_json:
        if path.exists(args_json[offer_file]) or new:
            _offer_file = args_json[offer_file]

    if verify:
        _input = input(
        f'''\noferta: {args_json[offer_file]} ? 
ENTER - OK, jakakolwiek litera albo spacja + ENTER - dialog wyboru: ''')
        if _input:
            root = tk.Tk()
            root.withdraw()
            _offer_file = filedialog.asksaveasfilename(
                initialfile=TEMP_DOC, title=title, 
                filetypes=filetypes) if new else filedialog.askopenfilename(
                title=title, filetypes=filetypes)
        
        args_json[offer_file] = _offer_file
        
    if not _offer_file:
        msg = f'Nie ma pliku "{args_json[offer_file]}".'
        raise HealthyException(msg)

    print('oferta: ' + _offer_file)
    args_json[offer_file] = _offer_file
    with open(CONFIG_JSON, 'w', encoding='utf-8') as f:
        json.dump(args_json, f, indent=4)     

    if process:
        try:
            processed = process(_offer_file)
            return processed
        except Exception as ex:
            msg = f'''Nie mogę odczytać pliku "{_offer_file}". Uszkodzony?
Opis błędu: {ex}'''
            raise HealthyException(msg)
    
    return _offer_file         


def db_group(angebot_nr, group_index, group_name, translate=True):
    if group_name:
        group_name = group_name.strip()

    if group_name in FixedGroups.get().groups_json:
        return FixedGroups.get().groups_json[group_name]

    con = sqlite3.connect(DB)
    cur = con.cursor()
    
    cur.execute(f"SELECT * FROM {GROUPS} WHERE {ANGEBOT_NR}='{angebot_nr}' AND {GROUP_INDEX}='{group_index}'")
    group = cur.fetchone()
    retval = None

    def use_deepl(group_name):
        group_name = dlt.deepl(group_name)
        if group_name:
            cur.execute(f"UPDATE {GROUPS} SET {GROUP_NAME}='{group_name}' WHERE {ANGEBOT_NR}='{angebot_nr}' AND {GROUP_INDEX}='{group_index}'")
        return group_name     
    # import pdb; pdb.set_trace()
    if group:
        if translate: 
            # Translate mode: stored group name {group[2]} may be translated already, or not.
            retval = group[2]
        else:
            # Teaching mode: if {group_name} differs(?) from {group[2]}, updete it.
            if group_name != group[2]:
                cur.execute(f"UPDATE {GROUPS} SET {GROUP_NAME}='{group_name}' WHERE {ANGEBOT_NR}='{angebot_nr}' AND {GROUP_INDEX}='{group_index}'")
                retval = group_name
    else:
        if translate: 
            # Translate mode: {group_name} is DE;
            group_name_ = use_deepl(group_name)
            group_name = f'{group_name_} ({group_name})' if group_name_ else group_name
            cur.execute(f"INSERT INTO {GROUPS} VALUES ('{angebot_nr}', '{group_index}', '{group_name}')")
            retval = group_name
        else:
            # Teaching mode: {group_name} may be translated or not.
            cur.execute(f"INSERT INTO {GROUPS} VALUES ('{angebot_nr}', '{group_index}', '{group_name}')")

    con.commit()
    con.close()

    return retval


def clear_table_row(row):
    for cell in row:
        for par in cell.paragraphs:
            p = par._element
            p.getparent().remove(p)
            par._p = par._element = None


def init():
    
    con = sqlite3.connect(DB)
    cur = con.cursor()
    # cur.execute(f'DROP TABLE {ARTICLES}')
    # cur.execute(f'DROP TABLE {GROUPS}')
    # cur.execute(f'DROP TABLE {WORDS}')

    cur.execute(
        f'CREATE TABLE IF NOT EXISTS {ARTICLES}({ID}, {HASH}, {ARTICLE}, UNIQUE({ID}, {HASH}))')
    cur.execute(f'CREATE INDEX IF NOT EXISTS {ARTICLES_INDEX} on {ARTICLES} ({ID}, {HASH})')
    cur.execute(
        f'CREATE TABLE IF NOT EXISTS {GROUPS}({ANGEBOT_NR}, {GROUP_INDEX}, {GROUP_NAME})')
    # import pdb; pdb.set_trace()
    con.commit()
    con.close()


def test():
    article_id = '25459x'
    article_pl = 'Wentylator ZK 40/350/ 22,0'
    article_de = 'Ventilator ZK 40/350/ 22,0-4 RD/LG ??'
    article_de_hash = solidHash(article_de)
    article_descr_pl = '''
wentylator szarpiący przystosowany do odsysu odpadów tektury falistej i papieru. Stabilna, spawana obudowa, gruntowana i lakierowana.
Na szynach mocujących zainstalowany jest silnik indukcyjny wentylatora. Napęd przenoszony jest na łożyskowany wał napędowy przez pasek klinowy i koło pasowe połączone tulejami zaciskowymi. Specjalne stalowe koło wirnikowe wyważone statycznie i dynamicznie zamocowane jest na wale napędowym przez tuleję zaciskową.
Dostawa obejmuje króćce wlotowe i wylotowe z kołnierzami.
Ze względu na zagrożenie wybuchem wentylator nie jest przystosowany do transportu materiałów pylistych < 500 µm o stężeniu > 20 g/m3.
    '''
    article_descr_de = '''
Absaugventilator, Baureihe "ZK", einseitig saugend,
mit Keilriemenantrieb, für den Einsatz außerhalb
explosionsgefährdeter Bereiche, ausgelegt zum
Absaugen Papier- und Wellpappenabfällen.
    '''
    article_params = {
        '350 mm':
            Param('350 mm', 'Saug-/Druckstutzen',
                  'Króćce na wlocie i wylocie'),
        '22 kW, B3, IP 55, 1500/min, 400/690 V, 50 Hz':
            Param('22 kW, B3, IP 55, 1500/min, 400/690 V, 50 Hz', 'Motor', 'Silnik')
    }
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f"DELETE FROM {ARTICLES} WHERE {ID}='{article_id}' AND {HASH}={article_de_hash}")
    con.commit()
    con.close()

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f"DELETE FROM {ARTICLES} WHERE {ID}='{article_id}' AND {HASH}={article_de_hash}")
    con.commit()
    con.close()
    
    import pdb; pdb.set_trace()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f"SELECT * FROM {ARTICLES}")
    xx = cur.fetchall()
    print(len(xx))


    cur.execute(
            f"UPDATE {ARTICLES} SET {ARTICLE}=? WHERE {ID}=? AND {HASH}=?",
            (None, article_id, solidHash(article_de)))
    cur.execute(f"SELECT * FROM {ARTICLES}")
    xx = cur.fetchall()
    print(len(xx))
    
    cur.execute(
            f"UPDATE {ARTICLES} SET {ARTICLE}=? WHERE {ID}=? AND {HASH}=?",
            (None, article_id, solidHash(article_de)))
    cur.execute(f"SELECT * FROM {ARTICLES}")
    xx = cur.fetchall()
    print(len(xx))    
    
    cur.execute(
            f"INSERT INTO {ARTICLES} VALUES (?, ?, ?)",
            (article_id, solidHash(article_de), None))
    cur.execute(f"SELECT * FROM {ARTICLES}")
    xx = cur.fetchall()
    print(len(xx)) 

    con.commit()
    con.close()
    

    print('\n\nLearning ####################################################')


    article_drv = Article(article_id, article_de, article_pl)
    print(article_drv.article_db)

    article_drv.set_descr(de=None, pl=article_descr_pl)
    print(article_drv.article_db)

    article_drv.set_param(
        value=list(article_params.items())[0][0],
        pl=list(article_params.items())[0][1].pl)
    article_drv.set_param(
        value=list(article_params.items())[1][0],
        pl=list(article_params.items())[1][1].pl)
    print(article_drv.article_db)

    print('\n\nTranslating ##################################################')
    import pdb; pdb.set_trace()
    article_drv = Article(article_id, de=article_de)
    print('\nDE article name added: _________________________________________')
    print(article_drv.article_db)

    article_drv.set_descr(de=article_descr_de)
    print('\nDE article description added: __________________________________')
    print(article_drv.article_db)

    article_drv.set_param(
        value=list(article_params.items())[0][0],
        de=list(article_params.items())[0][1].de)
    article_drv.set_param(
        value=list(article_params.items())[1][0],
        de=list(article_params.items())[1][1].de)
    print('\nDE parameters added: ___________________________________________')
    print(article_drv.article_db)


def schody():
    import math
    r = 76.1 / 2
    count = 24
    # angle = 5.9 / 2 # deg
    # rotation = 13.8 # deg
    # alpha = math.tan(math.radians(angle))

    # print('cincumferrence: ',  2 * math.pi * r)
    # print('division: ', 2 * math.pi * r / count)
    # print('angle: ', angle)
    # print('rotation length: ', math.radians(rotation) * r)

    # def x(y):
    #     return alpha * r * (1 + math.cos(y / r))

    # for i in range(count):
    #     print(f'{x(2 * math.pi * r / count * i):.2f}, {2 * math.pi * r / count * i:.2f} ')

    angle = 13.3 / 2  # deg
    rotation = 6.9  # deg
    alpha = math.tan(math.radians(angle))

    print()
    print(f'cincumferrence: {2 * math.pi * r : 0.2f}')
    print(f'division: {2 * math.pi * r / count : 0.2f}')
    print(f'angle: {angle : 0.2f}')
    print(f'angle gauge: 180:{180 * math.tan(2 * alpha) : 0.2f}')
    print(f'rotation length: {math.radians(rotation) * r : 0.2f}')

    def x(y):
        return alpha * r * (1 + math.cos(y / r))

    for i in range(count):
        print(
            f'{x(2 * math.pi * r / count * i):.2f}, {2 * math.pi * r / count * i:.2f} ')


init()

if __name__ == '__main__':
    test()
    # schody()
    # article_name_de = 'Segm.bogen 15° 2D NV/NV 350mm' # Kolano 45°, NV/NV, 3D, 300 mm
    # article_name_de = 'Rohr 1m lang NV/NX 900mm'
    # article_name_de = 'Sichtstrecke, 500mm lg 250mm'
    # article_name_de = 'Sickenschelle verz. 250mm'
    # article_name_de = 'Flex. Anschluss-Stück 350mm' # Przyłącze elastyczne z wewn. rurą ochronną, 350 mm
    # article_name_de = 'Abzweig 300NV - 200NV / 200NV' # Rozgałęzienie "Y" 300 NV – 200 NV / 200 NV
    # article_name_de = 'Konus 2mm von 300mm auf 250mm'
    # article_name_de = 'Multi-Rohrhalterung /D 250mm'
    # article_name_de = 'Kanalbogen 90° sym. | 920mm x 650mm' # Kolano kanału 1200, 1.450 x 920 mm
    # article_name_de = 'Pneumatik-Absperrschieber ECO-P S 24V 350mm'
    # article_name_de = 'Multi-Rohrhalterung /D B= 35mm M 8 400mm' # Mocowanie Multi /D {} mm
    # article_name_de = 'Multi-Rohrhalterung B= 60mm M 10 700mm' # Mocowanie Multi /D {} mm
    # article_name_de = 'Einblasbogen 90° 2mm 690x1380mm - 800mm' # Kolano kanału 90°, 2 mm, 690 x 1.380 mm – 800 mm
    # article_name_de = 'Kanal | 1260mm x 800mm | 1000mm lang' # Kanał 1.260 x 800, dł. 1.000 mm
    # article_name_de = 'Lochsiebkanal | 1260mm x 800mm | 1000mm lang' # Kanał perforowany 1.260 x 800, dł. 1.000 mm
    # article_name_de = 'Untergestell für MultiStar 10/ 5 1550mm h'

    # print(f'is regex "{article_name_de}": {Regex.get().is_regex(article_name_de)}')
    # print(f'{article_name_de}: {Regex.get().regex_name(article_name_de)}')

    