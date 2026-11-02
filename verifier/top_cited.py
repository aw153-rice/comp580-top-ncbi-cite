"""Checks for top_cited_pubmed and the top-cited-paper task."""

from .checks import result
from .fields import output_problem, query_problem
from .rows import load_papers, matches_rows


def verify_input(value):
    problem = query_problem(value)
    if problem:
        return result(False, problem[1])
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    problem = query_problem(input_value) or output_problem(output_value)
    if problem:
        return result(False, problem[1])
    kind, payload = load_papers(workspace)
    if kind != "ok":
        return result(False, payload)
    if output_value.papers_considered != len(payload):
        return result(False, "papers_considered does not match the rows in ranking.json")
    if not matches_rows(output_value, payload):
        return result(False, "output is not the top-cited paper in ranking.json")
    return result(True, "output matches the ranked rows")


def verify_task(arguments, output, reference, workspace):
    problem = query_problem(arguments) or output_problem(output)
    if problem:
        return result(False, problem[1])
    if reference is None:
        return result(False, "reference is missing")
    same = (
        output.pmid == reference.pmid
        and output.citation_count == reference.citation_count
        and output.papers_considered == reference.papers_considered
    )
    if not same:
        return result(False, "output does not match the reference")
    kind, payload = load_papers(workspace)
    if kind != "ok":
        return result(False, payload)
    if not matches_rows(output, payload):
        return result(False, "ranking.json does not support the output")
    return result(True, "output matches the reference")
