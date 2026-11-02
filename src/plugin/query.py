"""Search PubMed, load iCite citation counts, and rank every hit."""

from __future__ import annotations

import os
import re
from datetime import date

from contract import TopCitedInput, TopCitedOutput
from plugin.client import ESEARCH_URL, ICITE_BATCH, ICITE_URL, MAX_PAPERS, TOOL_NAME
from plugin.rank import choose_top

PMID = re.compile(r"^[1-9][0-9]{0,8}$")
DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
MAX_TERM = 2000


def clean_term(term: str) -> str:
    text = term.strip()
    if not text:
        raise ValueError("term is empty")
    if len(text) > MAX_TERM:
        raise ValueError("term is longer than 2000 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise ValueError("term contains a control character")
    return text


def parse_date(value: str) -> date:
    match = DATE.fullmatch(value)
    if match is None or int(match.group(1)) < 1800:
        raise ValueError(f"date must be YYYY-MM-DD: {value!r}")
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError as error:
        raise ValueError(f"date must be YYYY-MM-DD: {value!r}") from error


def rank_query(given: TopCitedInput, client) -> tuple[TopCitedOutput, list[dict]]:
    term = clean_term(given.term)
    start = parse_date(given.start_date)
    end = parse_date(given.end_date)
    if start > end:
        raise ValueError("start_date is after end_date")
    pmids = search_pmids(client, term, start, end)
    papers = citation_rows(client, pmids)
    winner = choose_top(papers)
    output = TopCitedOutput(pmid=winner["pmid"], citation_count=winner["citation_count"], papers_considered=len(papers))
    return output, papers


def search_pmids(client, term: str, start: date, end: date) -> list[str]:
    body = client.get_json(
        ESEARCH_URL,
        ncbi_params(
            {
                "db": "pubmed",
                "term": term,
                "datetype": "pdat",
                "mindate": start.strftime("%Y/%m/%d"),
                "maxdate": end.strftime("%Y/%m/%d"),
                "retmode": "json",
                "retmax": str(MAX_PAPERS),
                "retstart": "0",
            }
        ),
    )
    if body.get("error"):
        raise RuntimeError(f"ESearch error: {body['error']}")
    result = body.get("esearchresult")
    if not isinstance(result, dict):
        raise TypeError("ESearch returned no esearchresult")
    if result.get("ERROR") or result.get("errorlist"):
        raise RuntimeError(f"ESearch error: {result.get('ERROR') or result.get('errorlist')}")
    try:
        count = int(result.get("count"))
    except (TypeError, ValueError) as error:
        raise RuntimeError("ESearch returned no count") from error
    if count == 0:
        raise RuntimeError("PubMed returned no papers for that query and date window")
    if count > MAX_PAPERS:
        raise RuntimeError(f"PubMed returned {count} papers, above the limit of {MAX_PAPERS}")
    idlist = result.get("idlist")
    if not isinstance(idlist, list) or len(idlist) != count:
        raise RuntimeError("ESearch id list does not cover every hit")
    pmids = []
    seen = set()
    for raw in idlist:
        pmid = as_pmid(raw)
        if pmid in seen:
            raise RuntimeError(f"ESearch repeated pmid {pmid}")
        seen.add(pmid)
        pmids.append(pmid)
    return pmids


def citation_rows(client, pmids: list[str]) -> list[dict]:
    counts = {}
    requested = set(pmids)
    for start in range(0, len(pmids), ICITE_BATCH):
        batch = pmids[start : start + ICITE_BATCH]
        body = client.get_json(ICITE_URL, {"pmids": ",".join(batch), "fl": "pmid,citation_count"})
        data = body.get("data")
        if not isinstance(data, list):
            raise TypeError("iCite returned no data list")
        for row in data:
            if not isinstance(row, dict) or "pmid" not in row:
                raise TypeError("iCite returned a row without a pmid")
            pmid = as_pmid(row["pmid"])
            if pmid not in requested:
                continue
            counts[pmid] = as_count(row.get("citation_count"))
    return [{"pmid": pmid, "citation_count": counts.get(pmid, 0)} for pmid in pmids]


def ncbi_params(extra: dict[str, str]) -> dict[str, str]:
    params = {"tool": TOOL_NAME, **extra}
    email = os.environ.get("NCBI_EMAIL", "").strip()
    api_key = os.environ.get("NCBI_API_KEY", "").strip()
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    return params


def as_pmid(raw) -> str:
    if isinstance(raw, bool) or not isinstance(raw, int | str):
        raise TypeError(f"invalid pmid: {raw!r}")
    text = str(raw).strip()
    if PMID.fullmatch(text) is None:
        raise RuntimeError(f"invalid pmid: {raw!r}")
    return text


def as_count(raw) -> int:
    if raw is None:
        return 0
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise TypeError(f"invalid citation_count: {raw!r}")
    if raw < 0:
        raise RuntimeError(f"invalid citation_count: {raw!r}")
    return raw
