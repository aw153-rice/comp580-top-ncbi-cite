"""The task tool: rank the date-bounded PubMed search and record the rows."""

from __future__ import annotations

import json
from pathlib import Path

from contract import TopCitedInput, TopCitedOutput
from plugin.client import get_client
from plugin.query import rank_query

RANKING_FILE = "ranking.json"


def top_cited_pubmed(given: TopCitedInput, workspace: Path) -> TopCitedOutput:
    output, papers = rank_query(given, get_client())
    payload = {
        "papers": papers,
        "pmid": output.pmid,
        "citation_count": output.citation_count,
        "papers_considered": output.papers_considered,
    }
    (workspace / RANKING_FILE).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output
