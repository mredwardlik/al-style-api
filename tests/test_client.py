import pytest
import requests
import responses
from responses import matchers

from alstyle import ApiError, Client

from .conftest import CATEGORIES, TOKEN, URL, product


@pytest.fixture
def client():
    return Client(TOKEN, URL)


def query(**params):
    return [matchers.query_param_matcher({'access-token': TOKEN, **params})]


@responses.activate
def test_date(client):
    responses.get(f'{URL}/date', json='2017-12-11 23:16:00', match=query())
    assert client.date() == '2017-12-11 23:16:00'


@responses.activate
def test_categories(client):
    responses.get(f'{URL}/categories', json=CATEGORIES, match=query())
    responses.get(f'{URL}/categories', json=CATEGORIES[:1], match=query(id='3638'))
    assert client.categories() == CATEGORIES
    assert client.categories(3638)[0]['id'] == 3638


@responses.activate
def test_elements_parameters(client):
    responses.get(f'{URL}/elements', json=[product(1)],
                  match=query(category='3638,3639', limit='50', offset='100', additional_fields='brand,url'))
    assert client.elements([3638, 3639], limit=50, offset=100, fields=['brand', 'url'])[0]['article'] == 1


@responses.activate
def test_all_elements_pages(client):
    first = [product(i) for i in range(100)]
    responses.get(f'{URL}/elements', json=first, match=query(limit='100', offset='0'))
    responses.get(f'{URL}/elements', json=[product(100), product(101)], match=query(limit='100', offset='100'))
    assert [row['article'] for row in client.all_elements()] == list(range(102))
    assert len(responses.calls) == 2


@responses.activate
def test_all_elements_exact_page(client):
    responses.get(f'{URL}/elements', json=[product(i) for i in range(100)], match=query(limit='100', offset='0'))
    responses.get(f'{URL}/elements', json=[], match=query(limit='100', offset='100'))
    assert len(client.articles()) == 100


@pytest.mark.parametrize('kwargs', [dict(limit=0), dict(limit=101), dict(offset=-1), dict(fields=['color'])])
def test_elements_invalid(client, kwargs):
    with pytest.raises(ValueError):
        client.elements(**kwargs)


@responses.activate
def test_element_info(client):
    responses.get(f'{URL}/element-info', json=[product(20908, detailtext='…')],
                  match=query(article='20908,20932', additional_fields='detailtext'))
    assert client.element_info('20908, 20932', ['detailtext'])[0]['detailtext'] == '…'
    with pytest.raises(ValueError):
        client.element_info('')


@responses.activate
def test_images_list_and_dict(client):
    urls = ['http://img.al-style.kz/00024_1.jpg', 'http://img.al-style.kz/00024_2.jpg']
    responses.get(f'{URL}/images', json=urls, match=query(article='24', thumbs='0'))
    responses.get(f'{URL}/images', json={'24': urls, '25': []}, match=query(article='24,25', thumbs='1'))
    assert client.images(24) == {'24': urls}
    assert client.images([24, 25], thumbs=True) == {'24': urls, '25': []}


@responses.activate
def test_quantity_number_and_dict(client):
    responses.get(f'{URL}/quantity', json=10, match=query(article='24'))
    responses.get(f'{URL}/quantity', json={'24': 10, '25': '>50'}, match=query(article='24,25'))
    assert client.quantity('24') == {'24': 10}
    assert client.quantity('24,25') == {'24': 10, '25': '>50'}


@responses.activate
@pytest.mark.parametrize('status, message', [(401, 'token'), (403, 'token'), (500, 'HTTP 500')])
def test_http_errors(client, status, message):
    responses.get(f'{URL}/date', status=status)
    with pytest.raises(ApiError, match=message):
        client.date()


@responses.activate
def test_not_json(client):
    responses.get(f'{URL}/date', body='<html>')
    with pytest.raises(ApiError, match='not JSON'):
        client.date()


@responses.activate
def test_connection_error(client):
    responses.get(f'{URL}/date', body=requests.ConnectionError('Name or service not known'))
    with pytest.raises(ApiError, match='Cannot connect to api.test'):
        client.date()


@responses.activate
def test_timeout(client):
    responses.get(f'{URL}/date', body=requests.Timeout())
    with pytest.raises(ApiError, match='did not answer'):
        client.date()


def test_token_required():
    with pytest.raises(ValueError, match='token'):
        Client('')


@responses.activate
def test_delay_between_requests(monkeypatch):
    pauses = []
    monkeypatch.setattr('alstyle.client.time.sleep', pauses.append)
    responses.get(f'{URL}/date', json='x')
    client = Client(TOKEN, URL, delay=0.5)
    client.date()
    client.date()
    assert len(pauses) == 1 and 0 < pauses[0] <= 0.5
