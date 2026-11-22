"""A client of the Al-Style dealer API: categories, products, stock and photos.

Every method sends a GET request with the access token and returns parsed
JSON. The base URL is configurable because the API has moved before.

>>> client = Client('TOKEN', url='https://example.com/api/')
>>> client.url
'https://example.com/api'
"""

from __future__ import annotations

import time
from typing import Any, Iterable, Iterator
from urllib.parse import urlparse

import requests

DEFAULT_URL = 'https://order.al-style.kz/api'
PAGE_LIMIT = 100  # the API returns at most 100 products per request

ELEMENT_FIELDS = ('description', 'brand', 'weight', 'warranty', 'images', 'url', 'model', 'barcode')
INFO_FIELDS = ELEMENT_FIELDS + ('detailtext', 'properties')
ELEMENT_COLUMNS = ('article', 'name', 'full_name', 'category', 'sort', 'price1', 'price2',
                   'quantity', 'isnew', 'ishit', 'ispromo')
CATEGORY_COLUMNS = ('id', 'name', 'left', 'right', 'level', 'elements')


class ApiError(RuntimeError):
    """The request failed: no connection, an HTTP error or an answer that is not JSON."""


def join(values: Iterable[Any] | Any) -> str:
    """``[1, 2]`` → ``'1,2'``; strings and numbers pass through, spaces are dropped.

    >>> join([20908, '20932']), join('1, 2'), join(5)
    ('20908,20932', '1,2', '5')
    """
    if isinstance(values, (str, int)):
        values = str(values).split(',')
    items = [str(value).strip() for value in values]
    return ','.join(item for item in items if item)


def check_fields(fields: Iterable[str], allowed: tuple[str, ...]) -> str:
    """Validate additional fields and join them.

    >>> check_fields(['brand', 'url'], ELEMENT_FIELDS)
    'brand,url'
    >>> check_fields(['color'], ELEMENT_FIELDS)
    Traceback (most recent call last):
    ...
    ValueError: Unknown field «color». Available: description, brand, weight, warranty, images, url, model, barcode.
    """
    names = join(fields).split(',') if fields else []
    for name in filter(None, names):
        if name not in allowed:
            raise ValueError(f'Unknown field «{name}». Available: {", ".join(allowed)}.')
    return ','.join(filter(None, names))


class Client:
    """``Client(token).elements(category=3638)`` and so on. ``delay`` waits between requests."""

    def __init__(self, token: str, url: str = DEFAULT_URL, session: requests.Session | None = None,
                 timeout: float = 30, delay: float = 0):
        if not token:
            raise ValueError('An access token is required: pass --token or set ALSTYLE_TOKEN.')
        self.token = token
        self.url = url.rstrip('/')
        self.session = session or requests.Session()
        self.timeout = timeout
        self.delay = delay
        self._last_request = 0.0

    # ------------------------------------------------------------ transport

    def get(self, method: str, **params: Any) -> Any:
        """Send ``GET {url}/{method}?access-token=…&params`` and return the JSON answer."""
        query = {'access-token': self.token}
        query.update({key: value for key, value in params.items() if value not in (None, '')})
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        host = urlparse(self.url).netloc or self.url
        try:
            response = self.session.get(f'{self.url}/{method}', params=query, timeout=self.timeout)
        except requests.ConnectionError as error:
            raise ApiError(f'Cannot connect to {host}. Check the address (--url) and the connection. '
                           f'Details: {type(error).__name__}') from None
        except requests.Timeout:
            raise ApiError(f'{host} did not answer in {self.timeout:g} seconds.') from None
        finally:
            self._last_request = time.monotonic()
        if response.status_code in (401, 403):
            raise ApiError('The access token was not accepted (HTTP %d).' % response.status_code)
        if response.status_code != 200:
            raise ApiError(f'{method}: HTTP {response.status_code} {response.reason}'.rstrip())
        try:
            return response.json()
        except ValueError:
            raise ApiError(f'{method}: the answer is not JSON.') from None

    # ------------------------------------------------------------ methods

    def date(self) -> str:
        """When the data was last updated, for example ``'2017-12-11 23:16:00'``."""
        return str(self.get('date'))

    def categories(self, category_id: int | None = None) -> list[dict]:
        """All categories, or one by its ID. Categories form a tree by the Nested Sets method."""
        return _as_list(self.get('categories', id=category_id))

    def elements(self, categories: Iterable[int] | int | str | None = None, limit: int = PAGE_LIMIT,
                 offset: int = 0, fields: Iterable[str] = ()) -> list[dict]:
        """One page of products, optionally only from some categories."""
        if not 1 <= limit <= PAGE_LIMIT:
            raise ValueError(f'The limit must be from 1 to {PAGE_LIMIT}.')
        if offset < 0:
            raise ValueError('The offset can not be negative.')
        return _as_list(self.get('elements', category=join(categories) if categories else None,
                                 limit=limit, offset=offset,
                                 additional_fields=check_fields(fields, ELEMENT_FIELDS)))

    def all_elements(self, categories: Iterable[int] | int | str | None = None,
                     fields: Iterable[str] = ()) -> Iterator[dict]:
        """Every product, page after page, until a page comes back shorter than the limit."""
        offset = 0
        while True:
            page = self.elements(categories, PAGE_LIMIT, offset, fields)
            yield from page
            if len(page) < PAGE_LIMIT:
                return
            offset += PAGE_LIMIT

    def element_info(self, articles: Iterable[int] | int | str, fields: Iterable[str] = ()) -> list[dict]:
        """Full information about products by their articles."""
        return _as_list(self.get('element-info', article=_articles(articles),
                                 additional_fields=check_fields(fields, INFO_FIELDS)))

    def images(self, articles: Iterable[int] | int | str, thumbs: bool = False) -> dict[str, list[str]]:
        """Photo URLs of every article: ``{'20908': ['http://…_1.jpg', …]}``."""
        articles = _articles(articles)
        answer = self.get('images', article=articles, thumbs=int(thumbs))
        if isinstance(answer, dict):
            return {str(key): list(value or []) for key, value in answer.items()}
        # one article: the API returns a plain list
        return {articles.split(',')[0]: list(answer or [])}

    def quantity(self, articles: Iterable[int] | int | str) -> dict[str, Any]:
        """Stock of every article. A number, or a string like ``'>50'``."""
        articles = _articles(articles)
        answer = self.get('quantity', article=articles)
        if isinstance(answer, dict):
            return {str(key): value for key, value in answer.items()}
        return {articles.split(',')[0]: answer}

    def articles(self, categories: Iterable[int] | int | str | None = None) -> list[str]:
        """Articles of all products in the categories."""
        return [str(item['article']) for item in self.all_elements(categories)]


def _articles(articles: Iterable[int] | int | str) -> str:
    text = join(articles)
    if not text:
        raise ValueError('At least one article is required.')
    return text


def _as_list(answer: Any) -> list:
    if answer is None or answer == '':
        return []
    return answer if isinstance(answer, list) else [answer]
