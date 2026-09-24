#!/usr/bin/env python3
"""Import one day of the payment-domain study from a claude.ai artifact HTML file.

Usage: python3 tools/import_study_day.py <day-number> <downloaded-artifact.html>

Does the mechanical part only:
  - writes study/payment/day-NN.html (lang, <title> in <head>, day counter /21,
    removes the "면접용 30초" box, adds back link and prev/next navigation)
  - links the previous day's "next" button to the new day
  - flips the day on study/payment-domain-map.html from pending to a link and
    recounts the progress bar, the "N / 21 발행" label and each week's count

Editorial clean-up (Toss Place framing, interview remarks) is left to the caller;
the script prints any remaining hits so they can be edited by hand.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DAYS_DIR = ROOT / "study" / "payment"
MAP = ROOT / "study" / "payment-domain-map.html"
TOTAL = 21

NAV_CSS = """
/* site nav */
.back{display:inline-block;margin-bottom:28px;font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.08em;color:var(--muted);text-decoration:none}
.back:hover{color:var(--key)}
.pager{display:flex;gap:12px;margin-top:46px}
.pager a{flex:1;min-width:0;display:block;padding:14px 16px;border:1px solid var(--line);border-radius:10px;color:var(--ink);text-decoration:none;font-size:15px;line-height:1.5}
.pager a:hover{border-color:var(--key);color:var(--key)}
.pager a small{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.1em;color:var(--muted)}
.pager .next{text-align:right}
.pager span{flex:1}
</style>"""


def title_of(html):
    return re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()


def day_path(n):
    return DAYS_DIR / f"day-{n:02d}.html"


def build_day(n, src):
    s = src
    t = title_of(s)
    s = s.replace("<!doctype html><html><head>", '<!doctype html><html lang="ko"><head>', 1)
    s = s.replace("<meta charset=utf8>", "<meta charset=utf-8>", 1)
    # the artifact host puts <title> in <body>; move it into <head>
    s = re.sub(r"\s*<title>.*?</title>", "", s, count=1, flags=re.S)
    s = s.replace("</head>", f"<title>{t}</title>\n</head>", 1)
    s = re.sub(r'\n\s*<div class="pull">\s*<span>면접용 30초</span>.*?</div>\n', "\n", s, flags=re.S)
    s = re.sub(r"(<s>/</s>)\s*30\s*(<s>)", rf"\g<1>{TOTAL}\g<2>", s)
    if ".pager{" not in s:
        k = s.rindex("</style>")
        s = s[:k] + NAV_CSS[1:] + s[k + len("</style>"):]
    if 'class="back"' not in s:
        s = s.replace('<div class="wrap">',
                      '<div class="wrap">\n\n  <a class="back" href="../payment-domain-map.html">← 결제 도메인 지도</a>', 1)
    s = re.sub(r'\s*<nav class="pager">.*?</nav>\n', "\n", s, flags=re.S)
    prev = day_path(n - 1)
    prev_link = (f'<a class="prev" href="{prev.name}"><small>← DAY {n-1:02d}</small>'
                 f'{title_of(prev.read_text(encoding="utf-8"))}</a>') if prev.exists() else "<span></span>"
    nxt = day_path(n + 1)
    next_link = (f'<a class="next" href="{nxt.name}"><small>DAY {n+1:02d} →</small>'
                 f'{title_of(nxt.read_text(encoding="utf-8"))}</a>') if nxt.exists() else "<span></span>"
    pager = f'  <nav class="pager">\n    {prev_link}\n    {next_link}\n  </nav>\n\n'
    k = s.rindex("  <footer>")
    return s[:k] + pager + s[k:], t


def link_prev_to(n, title):
    prev = day_path(n - 1)
    if not prev.exists():
        return
    s = prev.read_text(encoding="utf-8")
    s = re.sub(r'(<nav class="pager">\s*(?:<a class="prev".*?</a>|<span></span>)\s*)(?:<a class="next".*?</a>|<span></span>)',
               lambda m: m.group(1) + f'<a class="next" href="day-{n:02d}.html"><small>DAY {n:02d} →</small>{title}</a>',
               s, count=1, flags=re.S)
    prev.write_text(s, encoding="utf-8")


def update_map(n, title):
    s = MAP.read_text(encoding="utf-8")
    pending = re.compile(
        r'<div class="day pending">\s*<div class="day-row">\s*<span class="day-num">%02d</span>\s*'
        r'<div class="day-body">\s*<div class="day-title">.*?</div>\s*(<div class="day-sub">.*?</div>)\s*'
        r'</div>\s*</div>\s*</div>' % n, re.S)
    done = ('<a class="day done" href="payment/day-%02d.html">\n'
            '      <div class="day-row">\n'
            '        <span class="day-num">%02d</span>\n'
            '        <div class="day-body">\n'
            '          <div class="day-title">%s</div>\n'
            '          \\1\n'
            '        </div>\n'
            '        <span class="arrow">→</span>\n'
            '      </div>\n'
            '    </a>') % (n, n, title.replace("\\", r"\\"))
    s, k = pending.subn(done, s)
    if k == 0 and f'href="payment/day-{n:02d}.html"' not in s:
        sys.exit(f"day {n:02d} not found on the map")
    # recount per-week and overall progress
    def week(m):
        block = m.group(0)
        d = block.count('class="day done"')
        total = d + block.count('class="day pending"')
        return re.sub(r"<small>\d+ / \d+</small>", f"<small>{d} / {total}</small>", block, count=1)
    s = re.sub(r'<div class="week">.*?(?=<div class="week">|<footer>)', week, s, flags=re.S)
    d = s.count('class="day done"')
    s = re.sub(r"<span>\d+ / \d+ 발행</span>", f"<span>{d} / {TOTAL} 발행</span>", s, count=1)
    bar = "\n      ".join(
        "".join('<i class="done"></i>' if i < d else "<i></i>" for i in range(a, b))
        for a, b in ((0, 7), (7, 14), (14, TOTAL)))
    s = re.sub(r'(<div class="bar" aria-hidden="true">\s*).*?(\s*</div>)', rf"\g<1>{bar}\g<2>", s, count=1, flags=re.S)
    MAP.write_text(s, encoding="utf-8")
    return d


def main():
    n, src = int(sys.argv[1]), pathlib.Path(sys.argv[2])
    if not 1 <= n <= TOTAL:
        sys.exit(f"day {n} is outside the {TOTAL}-day course; not imported")
    html, title = build_day(n, src.read_text(encoding="utf-8"))
    day_path(n).write_text(html, encoding="utf-8")
    link_prev_to(n, title)
    done = update_map(n, title)
    print(f"imported day {n:02d} '{title}', map now {done} / {TOTAL}")
    hits = [(i, l.strip()[:160]) for i, l in enumerate(html.splitlines(), 1)
            if re.search(r"토스플레이스|면접|4주차|Day 2[2-9]|Day 30", l)]
    for i, l in hits:
        print(f"  review {day_path(n).name}:{i}: {l}")


if __name__ == "__main__":
    main()
