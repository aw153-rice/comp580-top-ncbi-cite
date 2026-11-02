"""Tool tests. The HTTP client is a fake, so nothing here opens a socket."""

import json
from pathlib import Path

import httpx
import pytest
from slimconfig import build_output

from contract import TopCitedInput
from plugin.client import ESEARCH_URL, ICITE_URL, HttpxClient, set_client
from plugin.pin import pin_top_cited
from plugin.query import MAX_PAPERS
from plugin.top_cited import top_cited_pubmed

QUERY = {"term": "crispr", "start_date": "2020-01-01", "end_date": "2020-01-31"}


class FakeClient:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def get_json(self, url, params):
        self.calls.append((url, dict(params)))
        return self.handler(url, params)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    holder = {}

    def install(handler):
        client = FakeClient(handler)
        holder["client"] = client
        set_client(client)
        return client

    yield install
    set_client(None)


def given(**overrides):
    payload = {**QUERY, **overrides}
    return build_output(payload, TopCitedInput)


def esearch(pmids):
    return {"esearchresult": {"count": str(len(pmids)), "idlist": list(pmids)}}


def icite(rows):
    return {"data": rows}


def scripted(*bodies):
    pending = list(bodies)

    def handler(url, params):
        if not pending:
            raise AssertionError(f"unexpected call {url} {params}")
        body = pending.pop(0)
        if isinstance(body, Exception):
            raise body
        return body

    return handler


def test_ranks_the_higher_count_and_writes_rows(fake, tmp_path: Path):
    rows = [{"pmid": 100, "citation_count": 4}, {"pmid": 250, "citation_count": 9}]
    client = fake(scripted(esearch(["100", "250"]), icite(rows)))
    output = top_cited_pubmed(given(), tmp_path)
    assert output.pmid == "250"
    assert output.citation_count == 9
    assert output.papers_considered == 2
    saved = json.loads((tmp_path / "ranking.json").read_text(encoding="utf-8"))
    assert saved["papers"] == [{"pmid": "100", "citation_count": 4}, {"pmid": "250", "citation_count": 9}]
    assert client.calls[0][0] == ESEARCH_URL
    assert client.calls[0][1]["datetype"] == "pdat"
    assert client.calls[0][1]["mindate"] == "2020/01/01"
    assert client.calls[0][1]["maxdate"] == "2020/01/31"
    assert client.calls[0][1]["term"] == "crispr"
    assert client.calls[0][1]["tool"] == "top-ncbi-cite"
    assert client.calls[1][0] == ICITE_URL
    assert client.calls[1][1]["fl"] == "pmid,citation_count"


def test_tie_selects_the_lower_pmid(fake, tmp_path: Path):
    fake(scripted(esearch(["250", "100"]), icite([{"pmid": "250", "citation_count": 4}, {"pmid": "100", "citation_count": 4}])))
    output = top_cited_pubmed(given(), tmp_path)
    assert (output.pmid, output.citation_count) == ("100", 4)


def test_a_pmid_icite_omits_scores_zero(fake, tmp_path: Path):
    fake(scripted(esearch(["10", "11"]), icite([{"pmid": 10, "citation_count": 1}])))
    output = top_cited_pubmed(given(), tmp_path)
    assert output.pmid == "10"
    assert output.papers_considered == 2
    saved = json.loads((tmp_path / "ranking.json").read_text(encoding="utf-8"))
    assert saved["papers"][1] == {"pmid": "11", "citation_count": 0}


def test_one_day_window_and_a_zero_count(fake, tmp_path: Path):
    fake(scripted(esearch(["5"]), icite([])))
    output = top_cited_pubmed(given(start_date="2020-02-29", end_date="2020-02-29"), tmp_path)
    assert (output.pmid, output.citation_count, output.papers_considered) == ("5", 0, 1)


def test_pin_does_not_write_a_file(fake, tmp_path: Path):
    fake(scripted(esearch(["5"]), icite([{"pmid": 5, "citation_count": 2}])))
    output = pin_top_cited(given(), tmp_path)
    assert output.pmid == "5"
    assert list(tmp_path.iterdir()) == []


def test_batches_icite_at_200(fake, tmp_path: Path):
    pmids = [str(number) for number in range(1, 202)]
    client = fake(
        scripted(
            esearch(pmids),
            icite([{"pmid": number, "citation_count": 1} for number in range(1, 201)]),
            icite([{"pmid": 201, "citation_count": 8}]),
        )
    )
    output = top_cited_pubmed(given(), tmp_path)
    assert output.pmid == "201"
    assert output.papers_considered == 201
    assert len(client.calls) == 3
    assert len(client.calls[1][1]["pmids"].split(",")) == 200
    assert client.calls[2][1]["pmids"] == "201"


def test_sends_optional_credentials(fake, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("NCBI_EMAIL", "reader@example.com")
    monkeypatch.setenv("NCBI_API_KEY", "secret")
    client = fake(scripted(esearch(["8"]), icite([{"pmid": 8, "citation_count": 1}])))
    top_cited_pubmed(given(), tmp_path)
    sent = client.calls[0][1]
    assert sent["email"] == "reader@example.com"
    assert sent["api_key"] == "secret"
    assert "email" not in client.calls[1][1]


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"term": "  "}, "term is empty"),
        ({"start_date": "2020-13-01"}, "YYYY-MM-DD"),
        ({"end_date": "2019-02-29"}, "YYYY-MM-DD"),
        ({"start_date": "2020-02-02", "end_date": "2020-02-01"}, "after end_date"),
        ({"term": "bad\nterm"}, "control character"),
    ],
)
def test_rejects_a_bad_query(fake, tmp_path: Path, overrides, match):
    fake(scripted())
    with pytest.raises(ValueError, match=match):
        top_cited_pubmed(given(**overrides), tmp_path)


def test_raises_when_pubmed_has_no_hits(fake, tmp_path: Path):
    fake(scripted({"esearchresult": {"count": "0", "idlist": []}}))
    with pytest.raises(RuntimeError, match="no papers"):
        top_cited_pubmed(given(), tmp_path)


def test_raises_when_the_result_is_too_broad(fake, tmp_path: Path):
    client = fake(scripted({"esearchresult": {"count": str(MAX_PAPERS + 1), "idlist": []}}))
    with pytest.raises(RuntimeError, match="above the limit"):
        top_cited_pubmed(given(), tmp_path)
    assert len(client.calls) == 1


def test_raises_when_the_id_list_is_short(fake, tmp_path: Path):
    fake(scripted({"esearchresult": {"count": "2", "idlist": ["10"]}}))
    with pytest.raises(RuntimeError, match="does not cover"):
        top_cited_pubmed(given(), tmp_path)


def test_raises_on_a_repeated_pmid(fake, tmp_path: Path):
    fake(scripted({"esearchresult": {"count": "2", "idlist": ["10", "10"]}}))
    with pytest.raises(RuntimeError, match="repeated"):
        top_cited_pubmed(given(), tmp_path)


def test_raises_on_an_esearch_error(fake, tmp_path: Path):
    fake(scripted({"esearchresult": {"ERROR": "search failed"}}))
    with pytest.raises(RuntimeError, match="search failed"):
        top_cited_pubmed(given(), tmp_path)


def test_raises_when_icite_has_no_data_list(fake, tmp_path: Path):
    fake(scripted(esearch(["10"]), {"error": "down"}))
    with pytest.raises(TypeError, match="no data list"):
        top_cited_pubmed(given(), tmp_path)


def test_raises_on_a_negative_citation_count(fake, tmp_path: Path):
    fake(scripted(esearch(["10"]), icite([{"pmid": 10, "citation_count": -1}])))
    with pytest.raises(RuntimeError, match="citation_count"):
        top_cited_pubmed(given(), tmp_path)


def test_http_status_and_non_json_raise():
    def status(_request):
        return httpx.Response(503, text="no")

    client = HttpxClient(transport=httpx.MockTransport(status), pause=0)
    with pytest.raises(RuntimeError, match="HTTP 503"):
        client.get_json(ESEARCH_URL, {})

    def text(_request):
        return httpx.Response(200, text="not-json")

    client = HttpxClient(transport=httpx.MockTransport(text), pause=0)
    with pytest.raises(RuntimeError, match="not JSON"):
        client.get_json(ICITE_URL, {})
