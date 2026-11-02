"""Read ranking.json and recompute the winner. The stored winner is not trusted."""

import json
from pathlib import Path

from .fields import PMID
from .rank import choose_top


def load_papers(workspace):
    """Return ("ok", papers), or ("missing"|"malformed", message)."""
    path = Path(workspace) / "ranking.json"
    if not path.is_file():
        return ("missing", "ranking.json is missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ("malformed", "ranking.json is not JSON")
    if type(data) is not dict or type(data.get("papers")) is not list:
        return ("malformed", "ranking.json has no papers list")
    papers = []
    seen = []
    for row in data["papers"]:
        if type(row) is not dict:
            return ("malformed", "ranking.json has a paper that is not an object")
        pmid = row.get("pmid")
        count = row.get("citation_count")
        if type(pmid) is not str or PMID.fullmatch(pmid) is None:
            return ("malformed", "ranking.json has an invalid pmid")
        if type(count) is not int or count < 0:
            return ("malformed", "ranking.json has an invalid citation_count")
        if pmid in seen:
            return ("malformed", "ranking.json repeats a pmid")
        seen.append(pmid)
        papers.append({"pmid": pmid, "citation_count": count})
    if not papers:
        return ("malformed", "ranking.json lists no papers")
    return ("ok", papers)


def matches_rows(output, papers):
    winner = choose_top(papers)
    return (
        output.papers_considered == len(papers)
        and output.pmid == winner["pmid"]
        and output.citation_count == winner["citation_count"]
    )
