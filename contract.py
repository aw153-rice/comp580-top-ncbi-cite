"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    TOP_CITED_PUBMED = "top_cited_pubmed"
    PIN_TOP_CITED = "pin_top_cited"


class Task(Enum):
    TOP_CITED_PAPER = "top-cited-paper"


@dataclass
class TopCitedInput(Output):
    term: Annotated[str, "PubMed query in Entrez syntax"]
    start_date: Annotated[str, "Inclusive publication date start, YYYY-MM-DD"]
    end_date: Annotated[str, "Inclusive publication date end, YYYY-MM-DD"]


@dataclass
class TopCitedOutput(Output):
    pmid: Annotated[str, "PubMed ID of the paper with the most iCite citations"]
    citation_count: Annotated[int, "iCite citation_count of that paper; a paper iCite omits scores 0"]
    papers_considered: Annotated[int, "How many PubMed hits were ranked"]


TOOLS = {
    Tool.TOP_CITED_PUBMED: (TopCitedInput, TopCitedOutput),
    Tool.PIN_TOP_CITED: (TopCitedInput, TopCitedOutput),
}
TASKS = {Task.TOP_CITED_PAPER: (TopCitedInput, TopCitedOutput)}
