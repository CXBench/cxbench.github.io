"""Rebuild web derivatives from the original paper PDFs already stored in assets."""
import hashlib
import json
from pathlib import Path

import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/figures'
NAMES = ['figure1', 'figure2', 'figure3', 'figure4', 'domain_heatmap', 'rule_failure_heatmap']
manifest = []
for number, name in enumerate(NAMES, 1):
    source = DIRECTORY / f'{name}.pdf'
    with pymupdf.open(source) as document:
        page = document[0]
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2600 / page.rect.width, 2600 / page.rect.width), alpha=False)
        image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
        image.save(DIRECTORY / f'{name}.webp', quality=94, method=6)
    manifest.append({
        'id': name, 'paper_figure': number, 'source': source.name,
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'width': image.width, 'height': image.height,
        'image': f'assets/figures/{name}.webp', 'pdf': f'assets/figures/{name}.pdf',
        'modified': False,
    })
(DIRECTORY / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

# Table 3 is a spatial crop of page 8, with no changes to text or cell values.
clip = (65, 68, 531, 194)
paper = ROOT / 'assets/cxbench-paper.pdf'
with pymupdf.open(paper) as document:
    pixmap = document[7].get_pixmap(matrix=pymupdf.Matrix(5, 5), clip=pymupdf.Rect(clip), alpha=False)
    Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples).save(DIRECTORY / 'table3.webp', quality=96)
(DIRECTORY / 'table3-source.json').write_text(json.dumps({
    'source': 'assets/cxbench-paper.pdf', 'source_sha256': hashlib.sha256(paper.read_bytes()).hexdigest(),
    'page': 8, 'table': 3, 'crop_points': clip, 'content_modified': False,
}, indent=2) + '\n')
print('Exported six complete figures and the original Table 3 crop.')
