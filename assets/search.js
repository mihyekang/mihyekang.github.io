// Keyword search over /search.json (built by tools/build_search_index.py).
// Plain substring matching, so Korean words still match with particles attached
// ("매입사" finds "매입사가"). Every space-separated term must appear.
(function () {
  var input = document.getElementById('site-search');
  var panel = document.getElementById('search-results');
  if (!input || !panel) return;

  var index = null, loading = null, active = -1, timer = null;

  function load() {
    if (!loading) {
      loading = fetch('/search.json')
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) {
          index = data.map(function (e) {
            return { e: e, title: e.title.toLowerCase(), body: e.body.toLowerCase() };
          });
        })
        .catch(function () { loading = null; });
    }
    return loading;
  }

  function esc(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function highlight(text, terms) {
    var re = new RegExp('(' + terms.map(function (t) {
      return t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }).join('|') + ')', 'gi');
    return text.split(re).map(function (part, i) {
      return i % 2 ? '<mark>' + esc(part) + '</mark>' : esc(part);
    }).join('');
  }

  function snippet(item, terms) {
    var at = -1;
    terms.forEach(function (t) {
      var i = item.body.indexOf(t);
      if (i >= 0 && (at < 0 || i < at)) at = i;
    });
    var body = item.e.body;
    if (at < 0) return body.slice(0, 110) + (body.length > 110 ? '…' : '');
    var start = Math.max(0, at - 40), end = Math.min(body.length, at + 90);
    return (start > 0 ? '…' : '') + body.slice(start, end) + (end < body.length ? '…' : '');
  }

  function count(hay, t) {
    var n = 0, i = hay.indexOf(t);
    while (i >= 0 && n < 20) { n++; i = hay.indexOf(t, i + t.length); }
    return n;
  }

  function search(q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return null;
    var hits = [];
    index.forEach(function (item) {
      var score = 0;
      for (var k = 0; k < terms.length; k++) {
        var t = terms[k], inTitle = item.title.indexOf(t) >= 0, n = count(item.body, t);
        if (!inTitle && !n) return;
        score += (inTitle ? 20 : 0) + n;
      }
      hits.push({ item: item, score: score });
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    return { terms: terms, hits: hits.slice(0, 20), total: hits.length };
  }

  function close() { panel.hidden = true; active = -1; input.setAttribute('aria-expanded', 'false'); }

  function render() {
    var q = input.value.trim();
    if (!q) { close(); return; }
    if (!index) {
      panel.innerHTML = '<p class="search-empty">불러오는 중…</p>';
      panel.hidden = false;
      load().then(function () { if (index) render(); else panel.innerHTML = '<p class="search-empty">검색 색인을 불러오지 못했어요.</p>'; });
      return;
    }
    var r = search(q);
    active = -1;
    if (!r.total) {
      panel.innerHTML = '<p class="search-empty">"' + esc(q) + '" 검색 결과가 없어요.</p>';
    } else {
      panel.innerHTML = '<p class="search-count">' + r.total + '건</p>' + r.hits.map(function (h) {
        var e = h.item.e;
        return '<a class="search-hit" href="' + esc(e.url) + '">' +
          '<span class="search-tag">' + esc(e.tag) + (e.date ? ' · ' + esc(e.date) : '') + '</span>' +
          '<span class="search-title">' + highlight(e.title, r.terms) + '</span>' +
          '<span class="search-snippet">' + highlight(snippet(h.item, r.terms), r.terms) + '</span></a>';
      }).join('');
    }
    panel.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function move(d) {
    var links = panel.querySelectorAll('.search-hit');
    if (!links.length) return;
    if (active >= 0) links[active].classList.remove('is-active');
    active = (active + d + links.length) % links.length;
    links[active].classList.add('is-active');
    links[active].scrollIntoView({ block: 'nearest' });
  }

  input.addEventListener('focus', function () { load(); if (input.value.trim()) render(); });
  input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(render, 80); });
  input.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowDown') { ev.preventDefault(); move(1); }
    else if (ev.key === 'ArrowUp') { ev.preventDefault(); move(-1); }
    else if (ev.key === 'Enter') {
      ev.preventDefault();
      var links = panel.querySelectorAll('.search-hit');
      var target = links[active >= 0 ? active : 0];
      if (target) location.href = target.href;
    } else if (ev.key === 'Escape') { input.value = ''; close(); input.blur(); }
  });
  document.addEventListener('click', function (ev) {
    if (!panel.contains(ev.target) && ev.target !== input) close();
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === '/' && document.activeElement !== input && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      ev.preventDefault(); input.focus();
    }
  });
})();
