"""Reference tool: the same ranking, with no workspace file, pinned before the task runs."""

from __future__ import annotations

from pathlib import Path

from contract import TopCitedInput, TopCitedOutput
from plugin.client import get_client
from plugin.query import rank_query


def pin_top_cited(given: TopCitedInput, _workspace: Path) -> TopCitedOutput:
    output, _papers = rank_query(given, get_client())
    return output
