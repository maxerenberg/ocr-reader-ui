from PIL import Image
from tesserocr import PyTessBaseAPI, RIL, PSM, iterate_level

HIRAGANA_MIN, HIRAGANA_MAX = '\u3040', '\u309F'
KATAKANA_MIN, KATAKANA_MAX = '\u30A0', '\u30FF'
KANJI_MIN, KANJI_MAX = '\u4E00', '\u9FEF'
MIN_CONF = 0.5


def should_ignore_box(conf: float, box: dict, max_width: int,
                      max_height: int) -> bool:
    return conf < MIN_CONF or \
        (box['width'] > max_width or box['height'] > max_height) or \
        not (HIRAGANA_MIN <= box['text'] <= HIRAGANA_MAX or
             KATAKANA_MIN <= box['text'] <= KATAKANA_MAX or
             KANJI_MIN <= box['text'] <= KANJI_MAX)


def get_shape(image_filename: str) -> tuple:
    image = Image.open(image_filename)
    return image.width, image.height


def get_boxes(image_filename: str) -> list:
    image = Image.open(image_filename)
    width = image.width
    height = image.height
    max_width = width // 2
    max_height = height // 2

    api = PyTessBaseAPI(lang="jpn_vert")
    # api.ReadConfigFile("tess.conf")
    api.SetPageSegMode(PSM.SPARSE_TEXT_OSD)
    api.SetImage(image)
    api.Recognize(0)
    ri = api.GetIterator()
    level = RIL.WORD
    boxes = []
    for r in iterate_level(ri, level):
        conf = r.Confidence(level)
        text = r.GetUTF8Text(level)
        left, top, right, bottom = r.BoundingBox(level)
    # boxes = api.GetComponentImages(RIL.SYMBOL, True)
    # for im, rect, _, _ in boxes:
    #     # im is a PIL image object
    #     # rect is a dict with x, y, w and h keys
    #     left, top, right, bottom = rect['x'], rect['y'], rect['w'], rect['h']
    #     api.SetRectangle(left, top, right, bottom)
    #     text = api.GetUTF8Text()
    #     conf = api.MeanTextConf()
        print("'%s' \tConf: %.2f \tCoords: %d,%d,%d,%d" %
              (text, conf, left, top, right, bottom))
        box = {
            'text': text,
            'left': left,
            'top': top,
            'width': right - left,
            'height': bottom - top
        }
        if should_ignore_box(conf, box, max_width, max_height):
            continue
        boxes.append(box)
    api.End()
    image.close()
    return boxes
