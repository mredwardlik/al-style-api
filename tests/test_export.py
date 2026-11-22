import csv
import json

import responses

from alstyle import export


def test_csv_for_excel(tmp_path):
    rows = [{'article': 1, 'name': 'Колонки; чёрные', 'images': ['a', 'b']}, {'article': 2, 'extra': 'x'}]
    path = export.write_csv(rows, tmp_path / 'out' / 'products.csv', columns=['name', 'article'])
    raw = path.read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')  # BOM: Excel reads UTF-8
    with path.open(encoding='utf-8-sig', newline='') as file:
        table = list(csv.reader(file, delimiter=';'))
    assert table[0] == ['name', 'article', 'images', 'extra']
    assert table[1] == ['Колонки; чёрные', '1', '["a", "b"]', '']
    assert table[2] == ['', '2', '', 'x']


def test_save_by_extension(tmp_path):
    assert json.loads(export.save({'a': 1}, tmp_path / 'x.json').read_text(encoding='utf-8')) == {'a': 1}
    export.save([1, 2], tmp_path / 'x.csv')
    assert (tmp_path / 'x.csv').read_text(encoding='utf-8-sig').split() == ['value', '1', '2']
    try:
        export.save([], tmp_path / 'x.txt')
    except ValueError as error:
        assert '.csv or .json' in str(error)
    else:
        raise AssertionError


@responses.activate
def test_download_images(tmp_path):
    responses.get('http://img.test/1.jpg', body=b'one')
    responses.get('http://img.test/2.png', body=b'two')
    responses.get('http://img.test/missing.jpg', status=404)
    events = []
    images = {'24': ['http://img.test/1.jpg', 'http://img.test/2.png'], '25': ['http://img.test/missing.jpg']}
    saved = export.download_images(images, tmp_path / 'photos', workers=2,
                                   progress=lambda url, path, error: events.append((url, error)))
    assert sorted(path.name for path in saved) == ['24_1.jpg', '24_2.png']
    assert (tmp_path / 'photos' / '24_2.png').read_bytes() == b'two'
    assert [url for url, error in events if error] == ['http://img.test/missing.jpg']


def test_flatten():
    assert export.flatten({'1': ['a', 'b']}) == [{'article': '1', 'number': 1, 'url': 'a'},
                                                 {'article': '1', 'number': 2, 'url': 'b'}]
