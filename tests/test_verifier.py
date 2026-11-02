"""Verifier cases: correct, wrong, missing, malformed, and boundary."""

import json
from pathlib import Path

from slimconfig import build_output

import verifier
from contract import TopCitedInput, TopCitedOutput

QUERY = {"term": "crispr", "start_date": "2020-01-01", "end_date": "2020-01-31"}
WINNER = {"pmid": "100", "citation_count": 4, "papers_considered": 2}
ROWS = [
    {"pmid": "250", "citation_count": 4},
    {"pmid": "100", "citation_count": 4},
]


def given(**overrides):
    return build_output({**QUERY, **overrides}, TopCitedInput)


def made(**overrides):
    return build_output({**WINNER, **overrides}, TopCitedOutput)


def write_rows(workspace: Path, papers, **overrides) -> None:
    winner = made(**overrides)
    payload = {
        "papers": papers,
        "pmid": winner.pmid,
        "citation_count": winner.citation_count,
        "papers_considered": len(papers),
    }
    (workspace / "ranking.json").write_text(json.dumps(payload), encoding="utf-8")


def test_verify_input_accepts_a_query():
    verdict = verifier.verify_input("top_cited_pubmed", given())
    assert verdict["valid"] is True
    assert verifier.verify_input("pin_top_cited", given())["valid"] is True


def test_verify_input_rejects_an_end_before_the_start():
    verdict = verifier.verify_input("top_cited_pubmed", given(start_date="2020-03-01", end_date="2020-01-01"))
    assert verdict["valid"] is False
    assert "after end_date" in verdict["message"]


def test_verify_input_rejects_a_missing_term():
    verdict = verifier.verify_input("pin_top_cited", given(term="   "))
    assert verdict["valid"] is False
    assert "empty" in verdict["message"]


def test_verify_input_rejects_a_missing_date():
    verdict = verifier.verify_input("top_cited_pubmed", given(end_date=""))
    assert verdict["valid"] is False
    assert "empty" in verdict["message"]


def test_verify_input_rejects_a_malformed_date():
    verdict = verifier.verify_input("top_cited_pubmed", given(start_date="2020/01/01"))
    assert verdict["valid"] is False
    assert "YYYY-MM-DD" in verdict["message"]
    leap = verifier.verify_input("top_cited_pubmed", given(end_date="2019-02-29"))
    assert leap["valid"] is False


def test_verify_input_accepts_a_one_day_leap_day():
    verdict = verifier.verify_input("top_cited_pubmed", given(start_date="2020-02-29", end_date="2020-02-29"))
    assert verdict["valid"] is True


def test_verify_output_accepts_the_lower_pmid_on_a_tie(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("top_cited_pubmed", given(), made(), str(tmp_path))
    assert verdict["valid"] is True


def test_verify_output_rejects_the_higher_pmid_on_a_tie(tmp_path: Path):
    write_rows(tmp_path, ROWS, pmid="250")
    verdict = verifier.verify_output("top_cited_pubmed", given(), made(pmid="250"), str(tmp_path))
    assert verdict["valid"] is False
    assert "top-cited" in verdict["message"]


def test_verify_output_rejects_a_missing_file(tmp_path: Path):
    verdict = verifier.verify_output("top_cited_pubmed", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "missing" in verdict["message"]


def test_verify_output_rejects_a_malformed_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    for pmid in ("0123", "abc", "1" * 10):
        verdict = verifier.verify_output("top_cited_pubmed", given(), made(pmid=pmid), str(tmp_path))
        assert verdict["valid"] is False
        assert "pmid" in verdict["message"]
    negative = verifier.verify_output("top_cited_pubmed", given(), made(citation_count=-1), str(tmp_path))
    assert negative["valid"] is False
    assert "citation_count" in negative["message"]
    empty_set = verifier.verify_output("top_cited_pubmed", given(), made(papers_considered=0), str(tmp_path))
    assert empty_set["valid"] is False
    assert "papers_considered" in empty_set["message"]


def test_verify_output_rejects_a_malformed_file(tmp_path: Path):
    (tmp_path / "ranking.json").write_text("{", encoding="utf-8")
    verdict = verifier.verify_output("top_cited_pubmed", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "JSON" in verdict["message"]


def test_verify_output_rejects_a_row_count_mismatch(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("top_cited_pubmed", given(), made(papers_considered=1), str(tmp_path))
    assert verdict["valid"] is False
    assert "papers_considered" in verdict["message"]


def test_verify_output_rejects_an_empty_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("top_cited_pubmed", given(), made(pmid=""), str(tmp_path))
    assert verdict["valid"] is False
    assert "empty" in verdict["message"]


def test_verify_output_accepts_a_single_uncited_paper(tmp_path: Path):
    papers = [{"pmid": "5", "citation_count": 0}]
    write_rows(tmp_path, papers, pmid="5", citation_count=0, papers_considered=1)
    output = made(pmid="5", citation_count=0, papers_considered=1)
    arguments = given(start_date="2020-02-29", end_date="2020-02-29")
    verdict = verifier.verify_output("top_cited_pubmed", arguments, output, str(tmp_path))
    assert verdict["valid"] is True


def test_pin_output_does_not_need_a_file(tmp_path: Path):
    verdict = verifier.verify_output("pin_top_cited", given(), made(), str(tmp_path))
    assert verdict["valid"] is True


def test_verify_task_accepts_an_exact_reference(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    output = made()
    verdict = verifier.verify_task("top-cited-paper", given(), output, output, str(tmp_path))
    assert verdict["valid"] is True
    assert verdict["score"] == 1.0


def test_verify_task_rejects_a_different_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("top-cited-paper", given(), made(pmid="250"), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "reference" in verdict["message"]


def test_verify_task_rejects_a_different_count(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task(
        "top-cited-paper",
        given(),
        made(citation_count=9),
        made(),
        str(tmp_path),
    )
    assert verdict["valid"] is False
    assert "reference" in verdict["message"]


def test_verify_task_rejects_a_missing_reference(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("top-cited-paper", given(), made(), None, str(tmp_path))
    assert verdict["valid"] is False
    assert "missing" in verdict["message"]


def test_verify_task_rejects_a_malformed_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("top-cited-paper", given(), made(pmid="12a"), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "pmid" in verdict["message"]


def test_verify_task_accepts_a_zero_citation_boundary(tmp_path: Path):
    papers = [{"pmid": "5", "citation_count": 0}]
    write_rows(tmp_path, papers, pmid="5", citation_count=0, papers_considered=1)
    output = made(pmid="5", citation_count=0, papers_considered=1)
    arguments = given(start_date="2020-02-29", end_date="2020-02-29")
    verdict = verifier.verify_task("top-cited-paper", arguments, output, output, str(tmp_path))
    assert verdict["valid"] is True


def test_verify_task_rejects_a_file_that_disagrees_with_the_reference(tmp_path: Path):
    write_rows(tmp_path, [{"pmid": "100", "citation_count": 1}, {"pmid": "250", "citation_count": 9}])
    output = made()
    verdict = verifier.verify_task("top-cited-paper", given(), output, output, str(tmp_path))
    assert verdict["valid"] is False
    assert "ranking.json" in verdict["message"]
