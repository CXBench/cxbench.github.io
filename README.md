# CXBench research website

Public academic project page at **https://cxbench.github.io/**.

The site introduces CXBench: *A Benchmark for Process-Compliant LLM Agents
in Regulated Customer-Experience Workflows*. It includes the full supplied
manuscript and appendices, an original narrated animation, bilingual captions,
an interactive process example, and model/domain result visualizations.

## Content provenance

- The research source is `cxbench_arr.zip`, supplied on 2026-10-18.
- `assets/cxbench-paper.pdf` is compiled from its preprint entry point.
  `production/paper-layout.patch` records only line-break and table-spacing
  adjustments that prevent long appendix identifiers from crossing columns.
  Wording and scientific values are unchanged. The supplied archive checksum
  is recorded in `production/provenance.json`.
- Headline values follow the **active manuscript tables**, not historical
  commented text or unused numbers in `results-macros.tex`.
- All 840 retained records enter headline denominators. Formal process
  verdicts require the hybrid grader; diagnostic rule-only or LLM-only
  views are not presented as formal benchmark scores.
- `assets/data/results.json` records counts, denominators, intervals,
  sensitivity results, and provenance. Model and domain rates are computed
  from their corresponding counts. No experiments were rerun for this site.
- The supplied paper lists anonymous authors. The website keeps that status,
  and neither invents authors nor claims venue acceptance.
- The benchmark implementation and raw traces are not part of this website.

The submission-control comparison is presented as the paper describes it:
rescoring recorded traces, with the sensitivity to submission-specific
checks explicitly retained. The expert comparison uses development traces,
not an independent validation set. Benchmark verdicts are not legal certification.

## Local preview

No build tools or application dependencies are needed for the website.

```sh
python3 -m http.server 8765
```

Open `http://localhost:8765`. Directly opening `index.html` from the filesystem
does not enable the browser's JSON fetch for the interactive charts.

```sh
python3 production/validate_site.py
```

The validation checks count consistency, source denominators, local links,
video metadata, and bilingual subtitle synchronization.

## Update and publish

Push changes to `main`. The GitHub Actions Pages workflow validates and
publishes only the static website and `assets/`. Production tools are kept
in the repository for reproducibility and are excluded from the deployment.

Update `assets/data/results.json` and the exact HTML result table together
when the manuscript changes. Review the narration and limitations as well.
Do not mix figures from different benchmark releases or judge protocols.

## Rebuild the introduction

The 1920 x 1080, 30 fps film uses original geometric graphics drawn with
Pillow and encoded with FFmpeg. `production/narration.json` is the editable
English/Chinese script. The visual approach is inspired by explanatory
mathematical animation, including 3Blue1Brown's geometric storytelling;
no 3Blue1Brown footage, artwork, characters, music, or voice are included.

```sh
python3 -m venv .venv
.venv/bin/pip install -r production/requirements.txt
.venv/bin/python production/render_video.py --prepare
.venv/bin/python production/render_video.py --preview
.venv/bin/python production/render_video.py
```

The prepare step uses the Andrew neural speech voice through `edge-tts`
and needs network access. Narration segments are cached in `production/work/`
(gitignored). Set `CXBENCH_VIDEO_WORK` to choose a different cache location.
The render step needs no network. Captions, a bilingual transcript, chapter
timings, a poster, and video metadata are generated alongside the MP4.

Typography is self-hosted: DM Sans, Instrument Serif, IBM Plex Mono, and
STIX Two Math. Their SIL Open Font License notices are in `assets/fonts/`.

## Accessibility

The page supports keyboard-operable domain tabs, visible focus states,
mobile navigation, reduced-motion preferences, semantic data tables,
native video controls, two caption tracks, and a full text transcript.
The exact result table and explanatory content remain available without JS.
