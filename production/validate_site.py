"""Check published scientific counts, local links, subtitles, and video metadata."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / 'assets/data/results.json').read_text())
assert data['protocol']['grader'] == 'hybrid'
assert data['protocol']['records'] == 840
assert sum(row['outcome'] for row in data['models']) == 582
assert sum(row['both'] for row in data['models']) == 116
assert sum(row['false_pass'] for row in data['models']) == 466
assert sum(row['outcome'] for row in data['domains']) == 582
assert sum(row['both'] for row in data['domains']) == 116
assert sum(row['false_pass'] for row in data['domains']) == 466
assert sum(data['false_pass_detection'].values()) == 466
for row in data['models'] + data['domains']:
    assert row['outcome'] == row['both'] + row['false_pass'], row


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'Duplicate id: {attrs["id"]}'
            self.ids.add(attrs['id'])
        for attribute in ['href', 'src', 'poster']:
            if attribute in attrs:
                self.links.append(attrs[attribute])


for path in [ROOT / 'index.html', ROOT / 'assets/video/transcript.html']:
    page = Page()
    page.feed(path.read_text())
    for link in page.links:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        if not url.path:
            if url.fragment:
                assert url.fragment in page.ids, f'Missing anchor: {link}'
            continue
        target = (path.parent / unquote(url.path)).resolve()
        assert target.is_relative_to(ROOT), f'Escaping link: {link}'
        assert target.exists(), f'Missing asset: {target}'

metadata = json.loads((ROOT / 'assets/video/metadata.json').read_text())
assert metadata['width'] == 1920 and metadata['height'] == 1080
assert 120 <= metadata['duration_seconds'] <= 210
assert (ROOT / 'assets/video/cxbench-introduction.mp4').stat().st_size > 1_000_000
tracks = []
for language in ['en', 'zh']:
    text = (ROOT / f'assets/video/captions-{language}.vtt').read_text()
    assert text.startswith('WEBVTT\n')
    timestamps = re.findall(r'(\d\d:\d\d:\d\d\.\d{3}) --> (\d\d:\d\d:\d\d\.\d{3})', text)
    assert len(timestamps) == 24
    previous_end = 0
    for start, end in timestamps:
        def seconds(value):
            h, m, s = value.split(':')
            return int(h)*3600+int(m)*60+float(s)
        assert previous_end <= seconds(start) < seconds(end) <= metadata['duration_seconds']
        previous_end = seconds(end)
    tracks.append(timestamps)
assert tracks[0] == tracks[1], 'Subtitle tracks are not synchronized'
print('PASS: counts, denominators, local links, 1080p metadata, and 24 synchronized bilingual cues.')
