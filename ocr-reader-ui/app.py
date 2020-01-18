import os
import sqlite3
import json
from flask import g, current_app, Flask, request, jsonify, send_file, \
    render_template
from boxes import get_boxes, get_shape

app = Flask(
    __name__,
    static_url_path='',
    static_folder='static'
)
app.config.from_pyfile('config.py')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    if 'db' in g:
        g.pop('db').close()


@app.route('/fs')
def fs_request():
    path = request.args['path']
    extensions = current_app.config['IMG_EXTENSIONS']
    folders = []
    files = []
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.name[0] == '.':
                continue
            if entry.is_dir():
                folders.append(entry.name)
            elif entry.is_file():
                if any(entry.name.endswith(ext) for ext in extensions):
                    files.append(entry.name)
    if request.args.get('linkprev') == 'true':
        folders.append('..')
    folders.sort()
    files.sort()
    return render_template(
        'file_tree.html',
        data={'folders': folders, 'files': files}
    )


@app.route('/fs/images')
def fs_image_request():
    image_path = request.args['path']
    return send_file(os.path.abspath(image_path))


@app.route('/')
def root_request():
    return app.send_static_file('index.html')


@app.route('/ocr')
def ocr_request():
    path = request.args['path']
    boxes = get_boxes(path)
    width, height = get_shape(path)
    return jsonify({'boxes': boxes, 'imageWidth': width,
                    'imageHeight': height})


@app.route('/dict')
def dict_request():
    text = request.args['text']
    cursor = get_db().execute("""
    SELECT WORDS.INFO FROM TEXT_TO_WORDS
    INNER JOIN WORDS ON TEXT_TO_WORDS.ENT_SEQ = WORDS.ENT_SEQ
    WHERE TEXT_TO_WORDS.TXT = ?;
    """, (text,))
    words = [json.loads(row['INFO']) for row in cursor.fetchall()]
    # give priority to the words with an exact match
    words.sort(
        key=lambda word:
        0 if text in [word['main_read']['kanji']] +
        [read['text'] for read in word['main_read']['read']]
        else 1
    )
    # some preprocessing before the template rendering

    def kanji_alt_single(read_elem):
        post_info = ''
        if 'read' in read_elem and len(read_elem['read']) > 0:
            post_info += ' (' + ', '.join(
                r['text'] for r in read_elem['read']) + ')'
        return read_elem['kanji'] + post_info

    words = [
        {
            # use the first 'read' element for the big display if there
            # is no kanji
            'bg': word['main_read']['kanji'] if word['main_read']['kanji']
            is not None else word['main_read']['read'][0]['text'],
            # if there was no kanji, there should not be a hiragana element
            # for it
            'hg_main': word['main_read']['read'][0] if
            word['main_read']['kanji'] is not None else None,
            # 'hg_alt' is any of the 'read' elements which we haven't used
            'hg_alt': ", ".join(r["text"] for r in
                                word['main_read']['read'][1:])
            if len(word['main_read']['read']) > 1 else None,
            # 'kanji_alt' is a list of the alternative kanji readings and
            # any hiragana readings which are specific to them
            'kanji_alt': ", ".join(kanji_alt_single(elem)
                                   for elem in word['alt_read'])
            if 'alt_read' in word else None,
            # semicolon-separated list of similar terms for each defn entry
            'defns': ['; '.join(d['gloss']) for d in word['defns']]
        }
        for word in words
    ]
    return render_template('dict_lookup.html', words=words)


if __name__ == '__main__':
    app.run('127.0.0.1', 4869)
