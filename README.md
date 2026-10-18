# CXBench research website

Public academic project page: **https://cxbench.github.io/**.

The site presents _CXBench: A Benchmark for Process-Compliant LLM Agents in
Regulated Customer-Experience Workflows_. It includes the complete manuscript
and appendices, six original paper figures with zoom and PDF downloads, exact
model results, domain and rule heatmaps, and a narrated 1080p introduction
with synchronized English and Chinese captions.

## Content provenance

- The research source is `cxbench_arr.zip`, supplied on 2026-10-18. Its checksum
  and entry point are recorded in `production/provenance.json`.
- `assets/cxbench-paper.pdf` is compiled from the supplied preprint entry point.
  `production/paper-layout.patch` records line-break and table-spacing
  adjustments that prevent long appendix identifiers from crossing columns.
  Scientific content is unchanged.
- The six figure PDFs in `assets/figures/` are unchanged copies from the
  supplied manuscript. `manifest.json` records their checksums, figure numbers,
  and full-resolution WebP derivatives. Table 3 is cropped from page 8 of the
  paper; `table3-source.json` records the source and crop coordinates.
- Headline values follow the active manuscript tables, not historical
  commented text or unused numbers in `results-macros.tex`.
- All 840 retained records enter headline denominators. Formal process
  verdicts require hybrid grading; rule-only and LLM-only evaluations are
  diagnostic views, not formal benchmark scores.
- `assets/data/results.json` records counts, denominators, intervals,
  sensitivity results, and provenance. No experiments were rerun for this site.
- The supplied paper lists anonymous authors. The website retains that status
  and makes no claim about venue acceptance.
- Benchmark implementation and raw traces are not included in this repository.

The submission-control comparison is rescoring of recorded traces, with its
sensitivity to submission-specific checks retained. The expert comparison
uses development traces, not an independent validation set. Benchmark
verdicts are not legal certification.

## Visual design

The site's centered introduction, prominent video, and figure selectors draw
on the information layout of [MinerU](https://mineru.net/). Its original
figures, typography, icon, and blue/green palette belong to the CXBench page.
`assets/theme.json` records the shared palette used in the website stylesheet
and read directly by the film renderer.

The film retains the explanatory approach of mathematical animation: smooth
camera moves, progressive outlines, formulas, and a count-based dot diagram.
The visual material comes from Figures 1–6 and Table 3 of the CXBench paper.
Annotations and cropped views are additions in the film; the full figures on
the website are unchanged. No third-party footage, characters, or voice
impersonation is used.

## Preview and publish

The website has no build dependencies. Serve this directory locally:

```sh
python3 -m http.server 8765
python3 production/validate_site.py
```

Open `http://localhost:8765`. The check verifies scientific counts,
denominators, local links, figure provenance, video metadata, and caption
synchronization. The exact HTML results table is available without JavaScript.

Push changes to `main` to run the GitHub Pages workflow. It validates and
publishes only the static page and `assets/`. Production tools remain in the
repository for reproducibility and are excluded from the deployment.

When updating the paper, update `assets/data/results.json`, the exact HTML
table, figure sources, and the narration together. Do not combine results
from different benchmark releases or judge protocols.

## Rebuild media

```sh
python3 -m venv .venv
.venv/bin/pip install -r production/requirements.txt
.venv/bin/python production/export_figures.py
.venv/bin/python production/render_video.py --prepare
.venv/bin/python production/render_video.py --preview
.venv/bin/python production/render_video.py
```

`--prepare` creates narration with the Andrew neural voice through `edge-tts`
and requires network access. Clips and timing are cached in `production/work/`
(gitignored). Set `CXBENCH_VIDEO_WORK` to choose a different cache directory.
The preview and render steps use the cached audio without network access.

`production/narration.json` contains the bilingual script. The Pillow/FFmpeg
renderer creates the 1920 x 1080, 30 fps MP4, poster, captions, transcript,
chapter timings, and metadata. Preview frames and a contact sheet are stored
in the work directory. Typography is self-hosted; font license notices are
included in `assets/fonts/`.

## Accessibility

Keyboard-operable figure and results tabs, visible focus indicators, mobile
navigation, reduced-motion preferences, semantic tables, native video
controls, two caption tracks, and a bilingual transcript are included.
Figure dialogs support zoom, Escape to close, and focus restoration.
