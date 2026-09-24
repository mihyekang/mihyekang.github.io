#!/usr/bin/env python3
"""Build search.json, the keyword-search index for the site.

Usage: python3 tools/build_search_index.py

Indexes every post linked from index.html and every study day page. Each entry
holds the page's title, URL, tag and plain body text; assets/search.js matches
queries against it in the browser. Re-run whenever a page is added or edited.
"""
import html.parser
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "search.json"

SKIP_TAGS = {"style", "script", "svg", "nav", "head", "noscript"}
SKIP_CLASSES = {"back", "pager"}
BLOCK_TAGS = {"p", "li", "div", "section", "h1", "h2", "h3", "h4", "dt", "dd",
              "tr", "td", "th", "figcaption", "caption", "br", "q", "header", "footer"}
VOID_TAGS = {"br", "img", "meta", "link", "input", "hr", "source", "wbr"}


class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in VOID_TAGS:
            if tag == "br":
                self.parts.append(" ")
            return
        classes = set((dict(attrs).get("class") or "").split())
        skip = tag in SKIP_TAGS or bool(classes & SKIP_CLASSES)
        self._stack.append(skip)
        if skip:
            self._skip_depth += 1
        if tag in BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in VOID_TAGS or not self._stack:
            return
        if self._stack.pop():
            self._skip_depth -= 1
        if tag in BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self.parts.append(data)

    def text(self):
        return re.sub(r"\s+", " ", "".join(self.parts)).strip()


def extract(path):
    p = TextExtractor()
    p.feed(path.read_text(encoding="utf-8"))
    return p.title.strip(), p.text()


def posts():
    """Posts in the order index.html lists them, with their card title, tag and date."""
    s = (ROOT / "index.html").read_text(encoding="utf-8")
    for m in re.finditer(r'<a href="([^"]+)" class="post-item">(.*?)</a>', s, re.S):
        href, card = m.groups()
        tag = re.search(r'class="post-tag">(.*?)<', card)
        date = re.search(r'class="post-date">(.*?)<', card)
        title = re.search(r'class="post-title">(.*?)<', card)
        yield (href, title.group(1).strip() if title else "",
               tag.group(1) if tag else "", date.group(1) if date else "")


def main():
    entries = []
    for href, card_title, tag, date in posts():
        path = ROOT / href
        if not path.exists():
            continue
        title, body = extract(path)
        title = card_title or title
        entries.append({"url": "/" + href, "title": title, "tag": tag, "date": date, "body": body})
    for path in sorted((ROOT / "study" / "payment").glob("day-*.html")):
        title, body = extract(path)
        day = re.search(r"day-(\d+)", path.name).group(1)
        entries.append({"url": "/" + path.relative_to(ROOT).as_posix(), "title": title,
                        "tag": f"결제 도메인 · DAY {day}", "date": "", "body": body})
    OUT.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"search.json: {len(entries)} pages, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
