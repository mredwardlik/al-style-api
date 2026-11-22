"""Saving results: CSV for Excel, JSON, and downloading photos."""

from __future__ import annotations

import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Sequence

import requests

UNSAFE = re.compile(r'[^\w.-]+', re.UNICODE)


def columns_of(rows: Sequence[dict], preferred: Sequence[str] = ()) -> list[str]:
    """Preferred columns first, then any other keys in the order they appear.

    >>> columns_of([{'b': 1, 'a': 2}, {'c': 3}], preferred=['a'])
    ['a', 'b', 'c']
    """
    columns = [column for column in preferred if any(column in row for row in rows)]
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def cell(value: Any) -> Any:
    """Lists and dicts go into one cell as JSON."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_csv(rows: Sequence[dict], path: str | Path, columns: Sequence[str] = (),
              delimiter: str = ';', encoding: str = 'utf-8-sig') -> Path:
    """Semicolons and a BOM: Excel opens the file with the right columns and Cyrillic text."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = columns_of(rows, columns)
    with path.open('w', newline='', encoding=encoding) as file:
        writer = csv.writer(file, delimiter=delimiter)
        writer.writerow(header)
        for row in rows:
            writer.writerow([cell(row.get(column, '')) for column in header])
    return path


def write_json(data: Any, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def save(data: Any, path: str | Path, columns: Sequence[str] = ()) -> Path:
    """By the extension: ``.json`` or ``.csv``."""
    suffix = Path(path).suffix.lower()
    if suffix == '.json':
        return write_json(data, path)
    if suffix == '.csv':
        rows = data if isinstance(data, list) else [data]
        return write_csv([row if isinstance(row, dict) else {'value': row} for row in rows], path, columns)
    raise ValueError('The output file must end with .csv or .json.')


def image_files(images: dict[str, list[str]], folder: str | Path) -> list[tuple[str, Path]]:
    """Where every photo goes: ``20908_1.jpg``, ``20908_2.jpg``…

    >>> [(url, path.name) for url, path in image_files({'209/08': ['http://x/a.png', 'http://x/b']}, 'img')]
    [('http://x/a.png', '209_08_1.png'), ('http://x/b', '209_08_2.jpg')]
    """
    folder = Path(folder)
    files = []
    for article, urls in images.items():
        name = UNSAFE.sub('_', str(article)).strip('_') or 'article'
        for number, url in enumerate(urls, 1):
            suffix = Path(url.split('?')[0]).suffix.lower()
            suffix = suffix if suffix in ('.jpg', '.jpeg', '.png', '.gif', '.webp') else '.jpg'
            files.append((url, folder / f'{name}_{number}{suffix}'))
    return files


def download_images(images: dict[str, list[str]], folder: str | Path, workers: int = 5,
                    session: requests.Session | None = None, timeout: float = 60,
                    progress: Callable[[str, Path, Exception | None], None] | None = None) -> list[Path]:
    """Download photos in parallel. Returns the saved files; failures go to ``progress`` with the error."""
    session = session or requests.Session()
    files = image_files(images, folder)
    Path(folder).mkdir(parents=True, exist_ok=True)

    def fetch(item: tuple[str, Path]) -> Path | None:
        url, path = item
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            path.write_bytes(response.content)
        except (requests.RequestException, OSError) as error:
            if progress:
                progress(url, path, error)
            return None
        if progress:
            progress(url, path, None)
        return path

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return [path for path in pool.map(fetch, files) if path is not None]


def flatten(images: dict[str, list[str]]) -> list[dict]:
    """``{'1': ['a', 'b']}`` → rows for a table or CSV."""
    return [{'article': article, 'number': number, 'url': url}
            for article, urls in images.items() for number, url in enumerate(urls, 1)]


def as_rows(mapping: dict[str, Any], key: str, value: str) -> list[dict]:
    return [{key: k, value: v} for k, v in mapping.items()]

