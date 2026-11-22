import pytest
import responses

URL = 'https://api.test/api'
TOKEN = 'test-token'

CATEGORIES = [
    {'id': 3638, 'name': 'Мобильные телефоны', 'left': 2, 'right': 3, 'level': 2, 'elements': 25},
    {'id': 3633, 'name': 'Мобильные телефоны и аксессуары', 'left': 1, 'right': 22, 'level': 1, 'elements': 0},
]


def product(article, **extra):
    return {'article': article, 'name': f'Колонки {article}', 'full_name': f'Колонки, Xiaomi, {article}',
            'category': 3472, 'sort': 0, 'price1': 8434, 'price2': 11490, 'quantity': '>50',
            'isnew': 1, 'ishit': 0, 'ispromo': 0, **extra}


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv('ALSTYLE_TOKEN', TOKEN)
    monkeypatch.setenv('ALSTYLE_URL', URL)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('alstyle.config.USER_FILE', tmp_path / 'home.ini')
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock
