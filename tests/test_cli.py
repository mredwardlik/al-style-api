import io
import json

from rich.console import Console

from alstyle import config
from alstyle.cli import main

from .conftest import CATEGORIES, TOKEN, URL, product


def run(*argv):
    output = io.StringIO()
    code = main(list(argv), Console(file=output, width=140, color_system=None))
    return code, output.getvalue()


def test_date(api):
    api.get(f'{URL}/date', json='2017-12-11 23:16:00')
    assert run('date') == (0, 'Data updated: 2017-12-11 23:16:00\n')


def test_categories_tree(api):
    api.get(f'{URL}/categories', json=CATEGORIES)
    code, text = run('categories')
    lines = text.splitlines()
    parent = next(i for i, line in enumerate(lines) if 'и аксессуары' in line)
    child = next(i for i, line in enumerate(lines) if '  Мобильные телефоны ' in line)
    assert parent < child  # sorted by the tree, the child is indented


def test_elements_table_and_csv(api, tmp_path):
    api.get(f'{URL}/elements', json=[product(20908), product(20932, ishit=1)])
    code, text = run('elements', '-c', '3472')
    assert code == 0
    assert 'dealer price' in text and '20932' in text and 'hit' in text
    code, text = run('elements', '-c', '3472', '-o', 'products.csv')
    assert 'Saved 2 rows to products.csv' in text
    header = (tmp_path / 'products.csv').read_text(encoding='utf-8-sig').splitlines()[0]
    assert header == 'article;name;full_name;category;sort;price1;price2;quantity;isnew;ishit;ispromo'


def test_elements_all_json(api):
    api.get(f'{URL}/elements', json=[product(1)])
    code, text = run('elements', '--all', '--json')
    assert json.loads(text)[0]['article'] == 1


def test_info_and_quantity(api):
    api.get(f'{URL}/element-info', json=[product(20908, brand='Xiaomi')])
    api.get(f'{URL}/quantity', json={'20908': '>50'})
    assert 'Xiaomi' in run('info', '20908', '-f', 'brand')[1]
    assert '>50' in run('quantity', '20908')[1]


def test_images_download(api, tmp_path):
    api.get(f'{URL}/images', json=['http://img.test/a.jpg'])
    api.get('http://img.test/a.jpg', body=b'jpeg')
    code, text = run('images', '24', '--download', 'photos')
    assert 'Downloaded 1 of 1 photos' in text
    assert (tmp_path / 'photos' / '24_1.jpg').read_bytes() == b'jpeg'


def test_articles_to_file(api, tmp_path):
    api.get(f'{URL}/elements', json=[product(1), product(2)])
    assert run('articles')[1].strip() == '1,2'
    run('articles', '-o', 'articles.json')
    assert json.loads((tmp_path / 'articles.json').read_text(encoding='utf-8')) == ['1', '2']


def test_errors(api, monkeypatch):
    api.get(f'{URL}/date', status=403)
    code, text = run('date')
    assert code == 1 and 'token was not accepted' in text
    code, text = run('elements', '-f', 'color')
    assert code == 1 and 'Unknown field' in text
    monkeypatch.delenv('ALSTYLE_TOKEN')
    code, text = run('date')
    assert code == 1 and 'token is required' in text


def test_config(api, tmp_path, monkeypatch):
    monkeypatch.delenv('ALSTYLE_TOKEN')
    monkeypatch.delenv('ALSTYLE_URL')
    assert 'not set' in run('config')[1]
    run('config', '--token', 'abcdefghijkl', '--url', 'https://new.test/api/')
    settings = config.load()
    assert (settings.token, settings.url) == ('abcdefghijkl', 'https://new.test/api')
    assert 'abcd…kl' in run('config')[1]
    # options and the environment win over the file
    monkeypatch.setenv('ALSTYLE_TOKEN', TOKEN)
    assert config.load().token == TOKEN
    assert config.load(token='cli').token == 'cli'
