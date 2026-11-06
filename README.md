# Top NCBI Cite

A `nanoagent.plugin/v0001` plugin, created by `nanoagent plugin new` with the
structure of NanoAgent's reference plugin,
[arxiv-source](https://github.com/zeyuyang8/arxiv-source).

Given a PubMed query and an inclusive publication-date window, it returns the
PMID of the paper in that result set with the highest NIH iCite citation count.

## Tools

| Tool | Does | Code |
|---|---|---|
| `top_cited_pubmed` | Searches PubMed for the date window, loads iCite citation counts, and returns the top PMID | `src/plugin/top_cited.py` |
| `pin_top_cited` | Computes the same PMID as the task's answer key, and writes no file | `src/plugin/pin.py` |

`top_cited_pubmed` writes `ranking.json` in the workspace: one row per PMID with its citation count. A PMID that iCite omits scores 0. Equal counts select the numerically smaller PMID. A search with no hits, or with more than 1000 hits, raises instead of returning a partial ranking.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `top-cited-paper` | Returns the most-cited PMID in the window | `tool`, with `top_cited_pubmed` and reference `pin_top_cited` |

The input is `term`, `start_date`, and `end_date` (`YYYY-MM-DD`, inclusive, publication date). The output is `pmid`, `citation_count`, and `papers_considered`.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs, never values
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, and the plugin's own modules
├── tests/
├── ui/              # how the page draws the outputs: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

`contract.py` is the one place a value's shape is declared. Its `Output`
classes are the JSON Schemas the server offers and the agent sees, and every
input and output is built into its class on the way in and out: the server,
NanoAgent and the verifier all get typed values, never loose dicts. A tool
that fails raises; NanoAgent sees an MCP error.

## Develop and run

```bash
uv sync --extra dev
uv run pytest
```

The tests use a fake HTTP client and do not call NCBI or iCite. A live run
needs network access to `eutils.ncbi.nlm.nih.gov` and `icite.od.nih.gov`.
`.env` declares no variables. The client adds `NCBI_API_KEY` and `NCBI_EMAIL`
to the E-utilities request only when the process already has them, and still
ranks when they are absent. No workspace file is required before a run; `top_cited_pubmed`
creates `ranking.json`.
