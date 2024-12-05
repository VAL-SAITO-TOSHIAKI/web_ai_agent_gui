# parsers/dom_parser.py

import logging
import json
from bs4 import BeautifulSoup

class DOMParser:
    @staticmethod
    def parse(html_source: str) -> list:
        soup = BeautifulSoup(html_source, 'html.parser')
        elements = []
        for i, el in enumerate(soup.find_all(True)):
            elements.append({
                'dom_id': i,
                'tag': el.name,
                'attributes': dict(el.attrs),
                'text': (el.get_text(strip=True) or '')[:100],
            })
        total_chars = sum(len(json.dumps(e, ensure_ascii=False)) for e in elements)
        logging.info(f"DOMの要素数: {len(elements)}, 合計文字数: {total_chars}")
        return elements
