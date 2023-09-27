#!/usr/bin/env python
# encoding: utf-8

from core import *


def process_articless():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f"SELECT * FROM {ARTICLES}")
    articles = cur.fetchall()
    con.commit()
    con.close()
    for _article in articles:
        article = pickle.loads(_article[2])
        if re.match(MEHRPRIES, article.de):
            article.de = re.sub(MEHRPRIES, '', article.de).strip()
        article.update()


def regex_in_database():
    """
    """
    # import pdb; pdb.set_trace()
    deleted = {}
    candidates = []
    Regex.get().reload()
    Regex.get().dump()
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            f'SELECT {ID}, COUNT(*) AS "Count" FROM {ARTICLES} GROUP BY {ID} HAVING COUNT(*) > 1')
        multiple_ids = cur.fetchall()
        if multiple_ids:          
            for id in multiple_ids:
                cur.execute(f"SELECT * FROM {ARTICLES} WHERE {ID}='{id[0]}'")
                articles = cur.fetchall()
                count = len(articles)
                for all in articles:
                    if Regex.get().is_regex(all[0]):
                        # import pdb; pdb.set_trace()
                        cur.execute(f"DELETE FROM {ARTICLES} WHERE {ID}='{all[0]}' AND {HASH}={all[1]}")
                        if cur.rowcount:
                            deleted[(all[0], all[1])] = pickle.loads(all[2]).de
    finally:
        con.commit()
        con.close()

    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            f'SELECT {ID}, COUNT(*) AS "Count" FROM {ARTICLES} GROUP BY {ID} HAVING COUNT(*) > 1')
        multiple_ids = cur.fetchall()
        if multiple_ids:
            is_regex_valid = True            
            for id in multiple_ids:
                cur.execute(f"SELECT * FROM {ARTICLES} WHERE {ID}='{id[0]}'")
                articles = cur.fetchall()
                count = len(articles)
                for all in articles:
                    article = pickle.loads(all[2])
                    if not Regex.get().is_regex(article.de):
                        is_regex_valid = is_regex_valid and (not article.descr or not article.descr.pl)

                if is_regex_valid:
                    candidates.append({(count, id[0]): (article.de, article.pl)})
    finally:
        con.commit()
        con.close()    
    
    msg = ''
    if deleted:
        deleted_msg = '### Deleting from database regex articles:\n\n'
        for article_id, de in deleted.items():
            deleted_msg += f'"{article_id[0]}": "{de}"' + '\n'
        deleted_msg += '\n'     
        msg += deleted_msg
        print(deleted_msg)

    if candidates:
        cand_msg = '### These are articles to be considered as regex candidates:\n\n'
        candidates = dict(sorted(candidates.items()))
        for key, value in candidates:
            cand_msg += f'{key[0]}| "{key[1]}": ["{value[0]}, "{value[1]}"],\n'
        msg += cand_msg
        print(cand_msg)

    return msg

if __name__ == '__main__':
    # process_articless()
    regex_in_database()