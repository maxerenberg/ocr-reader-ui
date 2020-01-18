import sqlite3
import json
import os
from lxml import etree

DATABASE = './jmdict.db'
JMDICT_E = './JMdict_e'


def textiter(parent, tag):
    return [child.text for child in parent.iter(tag)]


schema_script = os.path.join(os.path.dirname(__file__), 'schema.sql')
# see http://www.edrdg.org/jmdict/jmdict_dtd_h.html for the DTD
with open(JMDICT_E) as f:
    jmdict = etree.parse(f).getroot()
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")
cursor.executescript(open(schema_script).read())
conn.commit()
counter = 0
for entry in jmdict:
    ent_seq = int(entry.find('ent_seq').text)
    word_info = {
        'main_read': None,
        'defns': []
    }
    k_elts = entry.findall('k_ele')
    if len(k_elts) > 0:
        d = {
            'kanji': k_elts[0].find('keb').text,
            'read': []
        }
        if k_elts[0].find('ke_inf') is not None:
            d['info'] = textiter(k_elts[0], 'ke_inf')
        word_info['main_read'] = d
        if len(k_elts) > 1:
            word_info['alt_read'] = []
            for k_ele in k_elts[1:]:
                d = {
                    'kanji': k_ele.find('keb').text,
                    'read': []
                }
                if k_ele.find('ke_inf') is not None:
                    d['info'] = textiter(k_ele, 'ke_inf')
                word_info['alt_read'].append(d)
    else:
        word_info['main_read'] = {
            'kanji': None,
            'read': []
        }
    for r_ele in entry.iter('r_ele'):
        d = {
            'text': r_ele.find('reb').text
        }
        if r_ele.find('re_inf') is not None:
            d['info'] = textiter(r_ele, 're_inf')
        if r_ele.find('re_nokanji') is not None:
            d['nokanji'] = True
        if r_ele.find('re_restr') is not None:
            for restr in textiter(r_ele, 're_restr'):
                for k_elt in word_info['alt_read']:
                    if k_elt['kanji'] == restr:
                        k_elt['read'].append(d)
                        break
        else:
            word_info['main_read']['read'].append(d)
    for sense in entry.iter('sense'):
        d = {}
        if sense.find('xref') is not None:
            d['xref'] = textiter(sense, 'xref')
        if sense.find('pos') is not None:
            d['pos'] = textiter(sense, 'pos')
        if sense.find('field') is not None:
            d['fields'] = textiter(sense, 'field')
        if sense.find('s_inf') is not None:
            d['info'] = textiter(sense, 's_inf')
        if sense.find('misc') is not None:
            d['misc'] = textiter(sense, 'misc')
        if sense.find('stagk') is not None:
            d['restrict'] = textiter(sense, 'stagk')
        if sense.find('stagr') is not None:
            d.setdefault('restrict', [])
            d['restrict'].extend(textiter(sense, 'stagr'))
        # the text for some of the <gloss> elements can be None
        # if they contain a <pri> element
        d['gloss'] = [text for text in textiter(sense, 'gloss')
                      if text is not None]
        word_info['defns'].append(d)
    cursor.execute("INSERT INTO WORDS VALUES (?, ?);",
                   (ent_seq, json.dumps(word_info, separators=(',', ':'))))
    for r in [word_info['main_read']] + word_info.get('alt_read', []):
        readings = []
        if r['kanji'] is not None:
            readings.append(r['kanji'])
        readings += [elem['text'] for elem in r['read']
                     if 'nokanji' not in elem]
        cursor.executemany("INSERT INTO TEXT_TO_WORDS VALUES (?, ?);",
                           [(txt, ent_seq) for txt in readings])
    conn.commit()
    counter += 1
    # TODO: use tqdm
    if counter % 100 == 0:
        print(counter)
# create an index to speed up queries based on text
cursor.execute("CREATE INDEX IX_TXT ON TEXT_TO_WORDS (TXT);")
conn.commit()
conn.close()
