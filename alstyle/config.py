"""Where the token and the API address come from: options, environment, config files."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from .client import DEFAULT_URL

SECTION = 'alstyle'
LOCAL_FILE = Path('alstyle.ini')
USER_FILE = Path.home() / '.alstyle.ini'


@dataclass(frozen=True)
class Settings:
    token: str | None
    url: str
    source: str  # where the token was found, for messages


def read_file(path: Path) -> dict[str, str]:
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding='utf-8')
    except configparser.Error as error:
        raise ValueError(f'{path}: {error}') from None
    return dict(parser[SECTION]) if parser.has_section(SECTION) else {}


def load(token: str | None = None, url: str | None = None, files: tuple[Path, ...] | None = None) -> Settings:
    """The first value found wins: options, then ``ALSTYLE_TOKEN`` / ``ALSTYLE_URL``,
    then ``alstyle.ini`` in the current folder, then ``~/.alstyle.ini``."""
    files = (LOCAL_FILE, USER_FILE) if files is None else files
    found_token, found_url, source = token, url, 'option' if token else ''
    if not found_token and os.environ.get('ALSTYLE_TOKEN'):
        found_token, source = os.environ['ALSTYLE_TOKEN'], 'ALSTYLE_TOKEN'
    found_url = found_url or os.environ.get('ALSTYLE_URL')
    for path in files:
        if found_token and found_url:
            break
        if path.is_file():
            values = read_file(path)
            if not found_token and values.get('token'):
                found_token, source = values['token'], str(path)
            found_url = found_url or values.get('url')
    return Settings(found_token, (found_url or DEFAULT_URL).rstrip('/'), source)


def save(token: str | None, url: str | None, path: Path = USER_FILE) -> Path:
    """Write the token and the address into a config file, keeping other values."""
    parser = configparser.ConfigParser()
    if path.is_file():
        parser.read(path, encoding='utf-8')
    if not parser.has_section(SECTION):
        parser.add_section(SECTION)
    if token:
        parser[SECTION]['token'] = token
    if url:
        parser[SECTION]['url'] = url.rstrip('/')
    with path.open('w', encoding='utf-8') as file:
        parser.write(file)
    try:
        path.chmod(0o600)  # the token is a secret
    except OSError:
        pass
    return path
