#!/usr/bin/env python
# encoding: utf-8

# https://regex101.com/

import re
import locale #https://herrmann.tech/en/blog/2021/02/05/how-to-deal-with-international-data-formats-in-python.html
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextLineHorizontal
from core import *
from offer_pl import OfferPl

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

FONT = r'# [^#]+ #\n'
INSERT = r'(# [^#]* #[^#]*# [^#]* #\n.{,3}\n*)*'
OPEN_DE_OFFER = 'Wybierz niemiecką ofertę:'
DOCUMENT_PDF = [('pdf', 'pdf')]
OPTIONAL = 'optional'
GROUP_HEADER = FONT + r'(\d+\.\nGruppe:[^#]+)'
GROUP_DETAILS = r'(?P<index>\d+)\.\nGruppe: (?P<name>[^\n]+)\n(?P<total>[\d.,]+)\s*'
ARTICLE_INDEX = r'\n(?:\d+\.)+\n(\d{4,})\n'
ARTICLE_DETAILS = r'(?P<count>\d+) (ST|SET)\n+(?P<price>[\d.,]+)\n+(?P<cost>[\d.,]+)\n+' + INSERT + '(?P<name>[^\n]*)(?P<rest>[\s\S]*)'

DE_TEST = 'Sehr geehrte Damen und Herren,'

HEADER = r'\nE\-Mail:\njana\.wittenbrink@hpt\.net'
ANGEBOT_NR = r'Angebot\-Nr\.: ([A-Z\- \d]+)'
def TRASH(angebot_nr):
    return (
        FONT + re.escape("Angebot-Nr.: " + angebot_nr) + '\nSeite \d+ von \d+\n' + re.escape(
'''Pos.
Art.-Nr.
Menge
 Einzelpreis
 Pos.Rabatt Gesamtpreis Euro
'''),
        FONT + re.escape(
'''Geschäftsführer/CEO
Ust-ID-Nr. DE 117574302
Deutsche Bank AG Osnabrück
Sparkasse Osnabrück
Postbank Hannover
Frank Höcker
Steuer-Nr. 6520023063
IBAN DE57 2657 0090 0186 6664 00
IBAN DE44 2655 0105 0001 2150 03
IBAN DE20 2501 0030 0089 6903 02
Christian Vennemann
Zoll-Nr. 327 160 9
BICDEUTDE3B265
BICNOLADE22XXX
BIC PBNKDEFF
'''),
        FONT + re.escape(
'''HÖCKER POLYTECHNIK GmbH

''') \
        + FONT + re.escape(
'''Fon +49 5409 405-0
Lufttechnische Anlagen/Dedusting Systems
Fax +49 5409 405-555
Borgloher Straße 1
www.hoecker-polytechnik.de
49176 Hilter a.T.W.
info@hpt.net
Germany
'''),
        )

OUTLINE = re.escape('Übersicht Positionsgruppen:')

class OfferDe:
    def __init__(self, ofer_file=OFFER_DE, args_json=None):
        self.pages = open_offer_file(
            ofer_file, OPEN_DE_OFFER, DOCUMENT_PDF, extract_pages, args_json=args_json)
        if not self.pages:
            return
        
        self.args_json = args_json
        self.groups = []
        self.ubersicht = None
        self.offer_pl = None
        self.text = self.readDe()
        self.angebot_nr = None

    def write_debug(self, text, suffix=''):
        with open(OFFER_DE + suffix + '.txt', 'w', encoding='utf-8') as f:
            f.write(text)

    def readDe(self):
        text = ''
        style_prev = None

        for page_layout in self.pages:
            lines = []
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    for line in element:
                        if isinstance(line, LTTextLineHorizontal):
                            lines.append(line)
            
            lines = sorted(lines, key=lambda e: (-e.bbox[1], e.bbox[0]))
            for line in lines:
                for character in line:
                    if isinstance(character, LTChar):
                        style =\
                            f'# {character.fontname}: {round(character.size)} #\n'
                        if not style == style_prev:
                            text += '\n' + style
                            style_prev = style
                        break
                text += line.get_text()
        
        text = re.sub(' +\n', '\n', text)
        text = re.sub(' {2,}', ' ', text)
        text = re.sub('\n{3,}', '\n\n', text)
        text = re.sub('\s*:', ':', text)
        
        self.write_debug(text)

        return text

    def print_groups(self):
        for group in self.groups:
            print(f'## GROUP {group.index}: {group.name}\n')
            comment = group.comment
            if comment:
                print(f'{comment}\n')
            for article in group.articles:
                line = f'\n{article.article_db.article_id:11s}{article.article_db.pl:40s}{article.count:5d} Stk.'
                
                if article.price:
                    line += f'{article.price:10.2f}'
                if article.cost:
                    line += f'{article.cost:10.2f}'
                if article.descr:
                    line += f'\n\n{article.article_db.descr}\n'
                print(line)
            print()

    def write_offer_pl_groups(self):
        self.offer_pl = OfferPl(self.args_json)
        for group in self.groups:
            self.offer_pl.add_group(
                group.index, 
                db_group(self.angebot_nr, group.index, group.name))

            if group.comment:
                self.offer_pl.add_comment(group.comment)
            
            for article in group.articles:
                # if article.article_db.article_id == '397240':
                #     import pdb; pdb.set_trace()
                self.offer_pl.add_article(article)

                if article.article_db.descr and article.article_db.descr.pl:
                    self.offer_pl.add_descr(article.article_db.descr.pl)
                
                if article.article_db.params:
                    self.offer_pl.add_article_params(article.article_db.params)
        
        self.offer_pl.finish()

    def parse(self):
        text = self.text

        if not DE_TEST in text:
            raise HealthyException(f'''
Plik 
"{self.args_json[OFFER_DE]}" 
nie jest chyba niemiecką ofertą HÖCKER POLYTECHNIK GmbH.
Niemiecka oferta tak się otwiera:
"{DE_TEST}"
''')
        # import pdb; pdb.set_trace()
        angebot_nr_match = re.search(ANGEBOT_NR, text)
        if not angebot_nr_match:
            msg = f'''Nie mogę odczytać wyrażenia "{angebot_nr_match}". Zmieniony format oferty?'''
            raise HealthyException(msg)
        self.angebot_nr = angebot_nr_match[1]

        header_match = re.search(HEADER, text)
        if not header_match:
            msg = f'''Nie mogę odczytać wyrażenia "{HEADER}". Zmieniony format oferty?'''
            raise HealthyException(msg)
        text = re.split(header_match[0], text)[1]
                    
        for tr in TRASH(self.angebot_nr):
            text = re.sub(tr, '\n', text)
        text = re.sub('\n{3,}', '\n\n', text)
        self.write_debug(text)

        ubersicht = re.split(FONT + OUTLINE +'\n', text)
        text = ubersicht[0]
        del ubersicht[0]
        self.ubersicht = '\n'.join(ubersicht)
        self.write_debug(text)
        
        if not re.search(GROUP_HEADER, text):
            msg = f'''Nie mogę znaleźć żadnej grupy. Zmieniony format oferty?'''
            raise HealthyException(msg)

        _groups = re.split(GROUP_HEADER, text)

        del _groups[0]

        for name_items in range(len(_groups) // 2):   
            group = Group()
            self.groups.append(group)
            group.index = re.search(GROUP_DETAILS, _groups[2 * name_items])['index']
            # if group.index == '10':
            #     import pdb; pdb.set_trace()
            group.name = re.search(GROUP_DETAILS, _groups[2 * name_items])['name']
            # _comment = _group[4].replace('\n', ' ').strip()
            # if _comment:
            #     group.comment = _comment
            # xx = 'Shredder PHSS K/G-25/150/11,00\n4\nStk.\n26.378,00\n105.512,00\n\n# CourierNew: 10 #\nDer Hochleistungs-Shredder ist ausgelegt zum\nEinsatz an Stanzen mit Nutzentrennung und\ndient der Zerkleinerung zur Aufbereitung für\ndie pneumatische Förderung von Stanzabfällen.\nDer Shredder ist ausgelegt für den Einsatz\naußerhalb explosionsgefährdeter Bereiche.\nDas Shreddergehäuse besteht aus einer stabilen\nSchweißkonstruktion in grundierter und lackier-\nter Ausführung (RAL 9006 - weißaluminium).\nDie Materialzerkleinerung erfolgt durch eine\nspeziell entwickelte Welle mit Schlägern nach\ndem Zerreiß-Schneid-Prinzip. Die Welle mit\nSchlägern rotiert gegen einen fest stehenden\nKamm. Durch die Anordnung der Welle mit\nSchlägern wird eine hohe Schredderleistung\nund eine gleichmäßige Zerkleinerung bei\nunterschiedlichen Stanzabfällen erreicht.\nDie Zerkleinerungswelle wird von einem IEC-\nNormmotor mit Federdruckbremse über einen\nKeilriementriebsatz angetrieben.\nDie Federdruckbremse gewährleistet ein\nsicheres Abbremsen der Welle im Störungsfall\nund bei Stromausfall. Für Revisionsarbeiten,\nbei Stillstand des Motors, ist die Bremse mit\neiner zusätzlichen Handlüftung ausgerüstet.\nA C H T U N G !\nAm Shreddereinlass können materialabhängige\nSchallemissionen über 85 dB(A) auftreten!\nZusätzlich im Lieferumfang enthalten sind:\n- Einfüllschacht, in schallisolierter\n Ausführung, mit Revisionsöffnung, Klappe\n und elektrischem Endschalter\n- Absaughaube, zum Anschluss einer Absaug-\n rohrleitung\n- Axial-Rohrventilator, als Stützventilator\n für die Absaugung\n- Fahrgestell mit Bock- und Lenkrollen\n- Schaltschrank\n- Handlüftung der Bremse - bei Stillstand -\n zu Revisionsarbeiten\nOptional:\n- Führungsschienen mit Anschlag\n- Manueller Anschluss mit Rohrschnellverschluss\n und Flex-Metallschlauch\n- Vereinfachter Anschluss mit Andockstation\n und Flex-Metallschlauch\n- Easy-Anschluss mit Andockstation, mit\n\n# CourierNew: 10 #\n Schieberohr und fester Rohrleitung\nTechnische Daten:\nAxial-Anbauventilator:\n- Nenn-Volumenstrom: 2000 m3/h\n- Druckerhöhung: 120 Pa\n- Rohrquerschnitt: 250 mm Durchmesser\n- Motor: 0,22 kW, 2800 min-1,\n 400 V, 50 Hz\nAbsauganschluss: 250 mm Durchmesser\n- erforderl. Volumenstrom: 5200 m3/h\n- erforderl. Unterdruck: 500 Pa\nShredder PHSS K/G:\n- Einzugsbreite: 1500 mm\n- Rotor: 250 mm Durchmesser\n- Antriebsmotor: 11,00 kW, 1500 min-1,\n 400 V, 50 Hz\n\n# FranklinGothicMedium: 10 #\n'
            # xx1 = 'Shredder PHSS K/G-25/150/11,00\n4\nStk.\n26.378,00\n\n# CourierNew: 10 #\nDer Hochleistungs-Shredder ist ausgelegt zum\nEinsatz an Stanzen mit Nutzentrennung und\ndient der Zerkleinerung zur Aufbereitung für\ndie pneumatische Förderung von Stanzabfällen.\nDer Shredder ist ausgelegt für den Einsatz\naußerhalb explosionsgefährdeter Bereiche.\nDas Shreddergehäuse besteht aus einer stabilen\nSchweißkonstruktion in grundierter und lackier-\nter Ausführung (RAL 9006 - weißaluminium).\nDie Materialzerkleinerung erfolgt durch eine\nspeziell entwickelte Welle mit Schlägern nach\ndem Zerreiß-Schneid-Prinzip. Die Welle mit\nSchlägern rotiert gegen einen fest stehenden\nKamm. Durch die Anordnung der Welle mit\nSchlägern wird eine hohe Schredderleistung\nund eine gleichmäßige Zerkleinerung bei\nunterschiedlichen Stanzabfällen erreicht.\nDie Zerkleinerungswelle wird von einem IEC-\nNormmotor mit Federdruckbremse über einen\nKeilriementriebsatz angetrieben.\nDie Federdruckbremse gewährleistet ein\nsicheres Abbremsen der Welle im Störungsfall\nund bei Stromausfall. Für Revisionsarbeiten,\nbei Stillstand des Motors, ist die Bremse mit\neiner zusätzlichen Handlüftung ausgerüstet.\nA C H T U N G !\nAm Shreddereinlass können materialabhängige\nSchallemissionen über 85 dB(A) auftreten!\nZusätzlich im Lieferumfang enthalten sind:\n- Einfüllschacht, in schallisolierter\n Ausführung, mit Revisionsöffnung, Klappe\n und elektrischem Endschalter\n- Absaughaube, zum Anschluss einer Absaug-\n rohrleitung\n- Axial-Rohrventilator, als Stützventilator\n für die Absaugung\n- Fahrgestell mit Bock- und Lenkrollen\n- Schaltschrank\n- Handlüftung der Bremse - bei Stillstand -\n zu Revisionsarbeiten\nOptional:\n- Führungsschienen mit Anschlag\n- Manueller Anschluss mit Rohrschnellverschluss\n und Flex-Metallschlauch\n- Vereinfachter Anschluss mit Andockstation\n und Flex-Metallschlauch\n- Easy-Anschluss mit Andockstation, mit\n\n# CourierNew: 10 #\n Schieberohr und fester Rohrleitung\nTechnische Daten:\nAxial-Anbauventilator:\n- Nenn-Volumenstrom: 2000 m3/h\n- Druckerhöhung: 120 Pa\n- Rohrquerschnitt: 250 mm Durchmesser\n- Motor: 0,22 kW, 2800 min-1,\n 400 V, 50 Hz\nAbsauganschluss: 250 mm Durchmesser\n- erforderl. Volumenstrom: 5200 m3/h\n- erforderl. Unterdruck: 500 Pa\nShredder PHSS K/G:\n- Einzugsbreite: 1500 mm\n- Rotor: 250 mm Durchmesser\n- Antriebsmotor: 11,00 kW, 1500 min-1,\n 400 V, 50 Hz\n\n# FranklinGothicMedium: 10 #\n'
            # xx2 = 'Shredder PHSS K/G-25/150/11,00\n4\nStk.\n26.378,00\n105.512,00\n'
            # xx3 = 'Mp/Montagematerial\n1\nStk.\n'
            # xx4 = '397240\nFuß f.Multi-Rohrhalterg.-400mm\n11\nStk.\n28,16\n309,76\n285,00\n285,00\n'


            items = re.split(ARTICLE_INDEX, _groups[2 * name_items + 1])
            del items[0]

            for id_body in range(len(items) // 2):
                article_id = items[2 * id_body]                
                
                # if items[2 * id_body + 1] == '2 ST\n51,43\n102,86\n\n# FAAAAH+FranklinGothic-Book: 7 #\nOsnabrück HRB 110203\n\n# FAAABC+TimesNewRomanPSMT: 12 #\n.\n\nSegmentbogen ø450mm 15° 2D | NV/NV':
                # if  article_id == '0000126000':
                #     import pdb; pdb.set_trace()                

                # import pdb; pdb.set_trace()
                # if article_id == '0000361800':
                #     import pdb; pdb.set_trace()

                article_name = CANNOT_PARSE
                article_count = 0
                article_price = locale.atof('0.00')
                article_cost = locale.atof('0.00')

                parsed = False
                rest = ''
                if not parsed:
                    parse = re.search(ARTICLE_DETAILS, items[2 * id_body + 1])
                    if parse:
                        try:
                            article_name = re.sub(MEHRPRIES, '', parse['name'])
                            article_count = int(parse['count'])
                            article_price = locale.atof(parse['price'])
                            article_cost = locale.atof(parse['cost'])
                            rest = parse['rest']
                            parsed = True
                        except:
                            pass
                        
                if not parsed:
                    print(f'''
###############################################################################
WARNING!!!
Cannot parse:
                          
{items[2 * id_body + 1]}

Bug, or the format of the current offer is modified.
###############################################################################

''')
                article = Article(
                    article_id, de=article_name,
                    count=article_count, price=article_price, cost=article_cost)
                
                descr = re.sub(FONT, '', rest).strip()
                article.set_descr(de=re.sub('\n{2,}', '\n', descr))
                article.is_optional = descr.lower().find(OPTIONAL) == 0
                        
                group.articles.append(article)
                
    
    def save_pl(self):
        self.offer_pl.save_offer()

def main():
    # import pdb; pdb.set_trace()
    offer = OfferDe()
    text = offer.text
    offer.parse()
    offer.print_groups()
    # print('HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH')
    # print(offer.ubersicht)

    # offer = OfferDe()
    # offer.parse()
    # offer.write_offer_pl_groups()
    # offer.save_pl()        

if __name__ == '__main__':
    main()