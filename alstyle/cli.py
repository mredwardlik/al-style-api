"""Command line: ``alstyle date | categories | elements | info | images | quantity | articles | config``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from rich.console import Console
from rich.table import Table

from . import __version__, config, export
from .client import CATEGORY_COLUMNS, ELEMENT_COLUMNS, ELEMENT_FIELDS, INFO_FIELDS, PAGE_LIMIT, ApiError, Client

TABLE_COLUMNS = ('article', 'name', 'price1', 'price2', 'quantity')
HEADERS = {'price1': 'dealer price', 'price2': 'retail price', 'full_name': 'full name'}
FLAGS = (('isnew', 'new'), ('ishit', 'hit'), ('ispromo', 'promo'))


class Output:
    """Prints tables, or JSON with ``--json``, and saves files with ``--output``."""

    def __init__(self, console: Console, args: argparse.Namespace):
        self.console = console
        self.args = args

    def emit(self, data: Any, rows: list[dict], columns: Sequence[str], title: str = '',
             shown: list[dict] | None = None) -> None:
        path = getattr(self.args, 'output', None)
        if path:
            saved = export.save(data if Path(path).suffix.lower() == '.json' else rows, path, columns)
            self.console.print(f'[green]Saved[/green] {len(rows)} rows to [bold]{saved}[/bold]', highlight=False)
        if self.args.json:
            self.console.print_json(json.dumps(data, ensure_ascii=False))
        elif not path or self.args.show:
            self.table(rows if shown is None else shown, columns, title)

    def table(self, rows: list[dict], columns: Sequence[str], title: str) -> None:
        if not rows:
            self.console.print('[yellow]The answer is empty.[/yellow]')
            return
        table = Table(title=title or None, title_justify='left', header_style='bold magenta')
        for column in columns:
            numeric = column in ('article', 'id', 'price1', 'price2', 'quantity', 'elements', 'number', 'level')
            table.add_column(HEADERS.get(column, column), justify='right' if numeric else 'left',
                             overflow='fold', max_width=60 if column in ('name', 'full_name', 'url') else None)
        if any(flag in rows[0] for flag, _ in FLAGS) and 'flags' not in columns:
            table.add_column('')
        for row in rows:
            cells = [_text(row.get(column, '')) for column in columns]
            if len(table.columns) > len(columns):
                cells.append(' '.join(f'[cyan]{label}[/cyan]' for flag, label in FLAGS if row.get(flag)))
            table.add_row(*cells)
        self.console.print(table)
        if len(rows) > 1:
            self.console.print(f'[dim]{len(rows)} rows[/dim]')


def _text(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def fields(text: str) -> list[str]:
    return [name.strip() for name in text.split(',') if name.strip()]


# ---------------------------------------------------------------- commands

def cmd_date(client: Client, out: Output, args) -> None:
    date = client.date()
    if args.json:
        out.console.print_json(json.dumps(date))
    else:
        out.console.print(f'Data updated: [bold]{date}[/bold]')


def cmd_categories(client: Client, out: Output, args) -> None:
    rows = client.categories(args.id)
    rows.sort(key=lambda row: row.get('left') if isinstance(row.get('left'), int) else 0)
    # in the table, names are indented by the depth of the Nested Sets tree
    tree = [{**row, 'name': '  ' * max(0, int(row.get('level') or 1) - 1) + str(row.get('name', ''))}
            for row in rows]
    out.emit(rows, rows, CATEGORY_COLUMNS, 'Categories', shown=tree)


def cmd_elements(client: Client, out: Output, args) -> None:
    extra = fields(args.fields)
    if args.all:
        rows = []
        with out.console.status('Loading products…') as status:
            for row in client.all_elements(args.category, extra):
                rows.append(row)
                if len(rows) % PAGE_LIMIT == 0:
                    status.update(f'Loading products… {len(rows)}')
    else:
        rows = client.elements(args.category, args.limit, args.offset, extra)
    out.emit(rows, rows, ELEMENT_COLUMNS if args.output else TABLE_COLUMNS + tuple(extra), 'Products')


def cmd_info(client: Client, out: Output, args) -> None:
    extra = fields(args.fields)
    rows = client.element_info(args.articles, extra)
    out.emit(rows, rows, ELEMENT_COLUMNS + tuple(extra) if args.output else
             ('article', 'full_name', 'price1', 'price2', 'quantity') + tuple(extra), 'Products')


def cmd_images(client: Client, out: Output, args) -> None:
    images = client.images(args.articles, args.thumbs)
    rows = export.flatten(images)
    out.emit(images, rows, ('article', 'number', 'url'), 'Photos')
    if args.download:
        failed = []

        def progress(url, path, error):
            if error:
                failed.append((url, error))

        with out.console.status(f'Downloading {len(rows)} photos…'):
            saved = export.download_images(images, args.download, args.workers, progress=progress)
        out.console.print(f'[green]Downloaded[/green] {len(saved)} of {len(rows)} photos to '
                          f'[bold]{args.download}[/bold]', highlight=False)
        for url, error in failed:
            out.console.print(f'[red]✗[/red] {url}: {error}', highlight=False)


def cmd_quantity(client: Client, out: Output, args) -> None:
    stock = client.quantity(args.articles)
    out.emit(stock, export.as_rows(stock, 'article', 'quantity'), ('article', 'quantity'), 'Stock')


def cmd_articles(client: Client, out: Output, args) -> None:
    articles = client.articles(args.category)
    if args.output:
        export.save([{'article': article} for article in articles] if args.output.endswith('.csv') else articles,
                    args.output)
        out.console.print(f'[green]Saved[/green] {len(articles)} articles to [bold]{args.output}[/bold]',
                          highlight=False)
    else:
        out.console.print(','.join(articles), soft_wrap=True, highlight=False)


def cmd_config(args, console: Console) -> int:
    path = Path(args.file) if args.file else config.USER_FILE
    if not args.token and not args.url:
        settings = config.load(files=(path,) if args.file else None)
        console.print(f'URL:   {settings.url}', highlight=False)
        if settings.token:
            hidden = settings.token[:4] + '…' + settings.token[-2:] if len(settings.token) > 8 else '…'
            console.print(f'Token: {hidden} [dim](from {settings.source})[/dim]', highlight=False)
        else:
            console.print('Token: [yellow]not set[/yellow]. Run alstyle config --token YOUR_TOKEN')
        return 0
    saved = config.save(args.token, args.url, path)
    console.print(f'[green]Saved[/green] to [bold]{saved}[/bold]', highlight=False)
    return 0


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='alstyle',
        description='Al-Style dealer API from the command line: categories, products, stock and photos, '
                    'shown as tables or saved to CSV and JSON.',
        epilog='The token is taken from --token, the ALSTYLE_TOKEN variable, alstyle.ini in the current '
               'folder or ~/.alstyle.ini (see alstyle config).',
    )
    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--token', help='access token')
    common.add_argument('--url', help='API address (default: %(default)s)', default=None)
    common.add_argument('--delay', type=float, default=0, metavar='SECONDS', help='pause between requests')
    common.add_argument('--timeout', type=float, default=30, metavar='SECONDS', help='request timeout (default: 30)')
    common.add_argument('--json', action='store_true', help='print the raw JSON answer')
    saving = argparse.ArgumentParser(add_help=False)
    saving.add_argument('-o', '--output', metavar='FILE', help='save to a .csv (for Excel) or .json file')
    saving.add_argument('--show', action='store_true', help='print the table too when saving')

    commands = parser.add_subparsers(dest='command', metavar='COMMAND', required=True)
    commands.add_parser('date', parents=[common], help='when the data was last updated')

    p = commands.add_parser('categories', parents=[common, saving], help='the category tree')
    p.add_argument('--id', type=int, help='only this category')

    p = commands.add_parser('elements', parents=[common, saving], help='products of categories')
    p.add_argument('-c', '--category', help='category IDs, comma separated (default: all)')
    p.add_argument('--limit', type=int, default=PAGE_LIMIT, help=f'products per request, 1-{PAGE_LIMIT}')
    p.add_argument('--offset', type=int, default=0, help='skip this many products')
    p.add_argument('-a', '--all', action='store_true', help='load every page, not only the first')
    p.add_argument('-f', '--fields', default='', metavar='LIST',
                   help='additional fields, comma separated: ' + ', '.join(ELEMENT_FIELDS))

    p = commands.add_parser('info', parents=[common, saving], help='full information about products')
    p.add_argument('articles', help='articles, comma separated')
    p.add_argument('-f', '--fields', default='', metavar='LIST',
                   help='additional fields, comma separated: ' + ', '.join(INFO_FIELDS))

    p = commands.add_parser('images', parents=[common, saving], help='photo links, and download them')
    p.add_argument('articles', help='articles, comma separated')
    p.add_argument('-t', '--thumbs', action='store_true', help='thumbnails instead of full size')
    p.add_argument('-d', '--download', metavar='FOLDER', help='download the photos into a folder')
    p.add_argument('-w', '--workers', type=int, default=5, help='parallel downloads (default: 5)')

    p = commands.add_parser('quantity', parents=[common, saving], help='stock of products')
    p.add_argument('articles', help='articles, comma separated')

    p = commands.add_parser('articles', parents=[common, saving], help='articles of all products in categories')
    p.add_argument('-c', '--category', help='category IDs, comma separated (default: all)')

    p = commands.add_parser('config', help='save the token and the address, or show them')
    p.add_argument('--token', help='access token to save')
    p.add_argument('--url', help='API address to save')
    p.add_argument('--file', help=f'config file (default: {config.USER_FILE})')
    return parser


HANDLERS = {'date': cmd_date, 'categories': cmd_categories, 'elements': cmd_elements, 'info': cmd_info,
            'images': cmd_images, 'quantity': cmd_quantity, 'articles': cmd_articles}


def use_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, 'encoding', None) or '').lower().replace('-', '')
        if encoding != 'utf8' and hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')


def main(argv: Sequence[str] | None = None, console: Console | None = None, session=None) -> int:
    args = build_parser().parse_args(argv)
    if console is None:
        use_utf8()
        console = Console(highlight=False)
    errors = Console(stderr=True, highlight=False) if console.file is sys.stdout else console
    if args.command == 'config':
        return cmd_config(args, console)
    try:
        settings = config.load(args.token, args.url)
        client = Client(settings.token, settings.url, session=session, timeout=args.timeout, delay=args.delay)
        HANDLERS[args.command](client, Output(console, args), args)
    except (ApiError, ValueError) as error:
        errors.print(f'[red]alstyle: {error}[/red]', highlight=False)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0
