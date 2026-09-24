import html
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree

from django.core.management.base import BaseCommand


class VisibleTextParser:
    def __init__(self):
        self.parts = []
        self.skip_depth = 0
        self.in_title = False

    def feed(self, markup):
        from html.parser import HTMLParser

        class Parser(HTMLParser):
            def __init__(self, owner):
                super().__init__(convert_charrefs=True)
                self.owner = owner

            def handle_starttag(self, tag, attrs):
                if tag in {'script', 'style', 'noscript', 'svg'}:
                    self.owner.skip_depth += 1
                if tag == 'title':
                    self.owner.in_title = True
                if tag in {'h1', 'h2', 'h3', 'p', 'li', 'dt', 'dd'}:
                    self.owner.parts.append(('START', tag))

            def handle_endtag(self, tag):
                if tag == 'title':
                    self.owner.in_title = False
                if tag in {'h1', 'h2', 'h3', 'p', 'li', 'dt', 'dd'}:
                    self.owner.parts.append(('END', tag))
                if tag in {'script', 'style', 'noscript', 'svg'} and self.owner.skip_depth:
                    self.owner.skip_depth -= 1

            def handle_data(self, data):
                if not self.owner.skip_depth:
                    text = re.sub(r'\s+', ' ', html.unescape(data)).strip()
                    if text:
                        self.owner.parts.append(('TEXT', text))

        Parser(self).feed(markup)

    def text(self):
        lines = []
        current = []
        for kind, value in self.parts:
            if kind == 'START':
                current = []
            elif kind == 'TEXT':
                current.append(value)
            elif kind == 'END' and current:
                line = ' '.join(current).strip()
                if line and line not in lines:
                    lines.append(line)
                current = []
        return '\n'.join(lines)


def page_metadata(markup):
    title = re.search(r'<title[^>]*>(.*?)</title>', markup, re.IGNORECASE | re.DOTALL)
    descriptions = re.findall(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description|keywords)["\'][^>]+content=["\'](.*?)["\']',
        markup,
        re.IGNORECASE | re.DOTALL,
    )
    values = []
    if title:
        values.append(html.unescape(re.sub(r'\s+', ' ', title.group(1)).strip()))
    values.extend(html.unescape(re.sub(r'\s+', ' ', value)).strip() for value in descriptions)
    return '\n'.join(dict.fromkeys(value for value in values if value))


class Command(BaseCommand):
    help = 'Fetch public Boldstone pages and refresh the AI knowledge file.'

    page_paths = (
        '/',
        '/about',
        '/farmers',
        '/lease-a-coffee-farm',
        '/lease-application',
        '/partnership',
        '/shop',
        '/contact',
        '/blog',
        '/team',
        '/terms',
        '/privacy',
    )

    def add_arguments(self, parser):
        parser.add_argument('--base-url', default=os.getenv('KNOWLEDGE_BASE_URL', 'https://www.boldstoneinvestments.com'))
        parser.add_argument('--timeout', type=int, default=15)

    def fetch_page(self, url, timeout):
        request = urllib.request.Request(url, headers={'User-Agent': 'BoldstoneAIKnowledgeSync/1.0'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')

    def handle(self, *args, **options):
        base_url = options['base_url'].rstrip('/')
        timeout = options['timeout']
        pages = []
        for path in self.page_paths:
            url = urljoin(f'{base_url}/', path.lstrip('/'))
            try:
                text_parser = VisibleTextParser()
                markup = self.fetch_page(url, timeout)
                text_parser.feed(markup)
                text = '\n'.join(filter(None, (page_metadata(markup), text_parser.text())))
                if text:
                    pages.append((url, text))
                    self.stdout.write(f'Fetched {url}')
                else:
                    self.stderr.write(f'No readable content found at {url}')
            except (OSError, urllib.error.URLError, ValueError) as error:
                self.stderr.write(f'Could not fetch {url}: {error}')

        if len(pages) < 3:
            self.stderr.write(self.style.WARNING('Knowledge sync kept the existing file because fewer than three pages were fetched.'))
            return

        knowledge_path = Path(__file__).resolve().parents[2] / 'ai_knowledge_base.md'
        existing_content = knowledge_path.read_text(encoding='utf-8') if knowledge_path.exists() else ''
        if '## Curated Boldstone Knowledge' in existing_content:
            existing_content = existing_content.split('## Curated Boldstone Knowledge', 1)[1].strip()
        output = [
            '# Boldstone AI Knowledge Base',
            '',
            'This file is refreshed from the public Boldstone website during deployment. Do not add private customer information here.',
            'Boldstone AI must answer factual questions only from the content below.',
            '',
        ]
        for url, text in pages:
            output.extend([f'## Source: {url}', '', text, ''])

        if existing_content:
            output.extend(['## Curated Boldstone Knowledge', '', existing_content, ''])
        temporary_path = knowledge_path.with_suffix('.md.tmp')
        temporary_path.write_text('\n'.join(output), encoding='utf-8')
        temporary_path.replace(knowledge_path)
        self.stdout.write(self.style.SUCCESS(f'Updated {knowledge_path} from {len(pages)} public pages.'))
