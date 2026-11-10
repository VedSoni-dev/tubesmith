"""Shared helpers for the tubesmith pipeline. Standard library only (Python 3.8+)."""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DATA = "data"
UA = "tubesmith/1.0 (+https://github.com/VedSoni-dev/tubesmith)"

# Any YouTube video link: watch?v=, youtu.be/, embed/, shorts/, live/, v/
YT_RE = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:[^\s\"'<>]*?&(?:amp;)?)?v=|embed/|shorts/|live/|v/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])"
)
URL_RE = re.compile(r"https?://\S+")
TAG_RE = re.compile(r"<[^>]+>")


def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    os.makedirs(DATA, exist_ok=True)
    return cfg


def get(cfg, dotted, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass  # a half-written last line after a crash; skip it
    return out


def append_jsonl(path, rows):
    with open(path, "a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_jsonl(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def video_ids(text):
    """All distinct YouTube video ids in a string (HTML or plain), in order."""
    seen, out = set(), []
    for m in YT_RE.finditer(html.unescape(text or "")):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def html_to_text(s):
    s = re.sub(r"<p>", "\n\n", s or "")
    s = TAG_RE.sub("", s)
    return html.unescape(s).strip()


def own_text_len(text):
    """Characters the commenter wrote themselves, links excluded."""
    return len(re.sub(r"\s+", " ", URL_RE.sub("", text)).strip())


def http_json(url, headers=None, data=None, tries=4, timeout=30):
    """GET (or POST when data is given) JSON with polite retries. Raises HTTPError on 4xx."""
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    hdrs.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt < tries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise


def http_text(url, headers=None, timeout=30):
    hdrs = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def progress(msg):
    sys.stderr.write("\r" + msg[:160].ljust(80))
    sys.stderr.flush()
