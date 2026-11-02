"""Calendar and query checks. No clock: leap years are arithmetic."""

import re

PMID = re.compile(r"^[1-9][0-9]{0,8}$")
DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
MAX_TERM = 2000


def query_problem(value):
    """A (kind, message) pair, or None when the query can be ranked."""
    if value.term.strip() == "":
        return ("missing", "term is empty")
    if len(value.term.strip()) > MAX_TERM:
        return ("malformed", "term is longer than 2000 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value.term):
        return ("malformed", "term contains a control character")
    for label, raw in (("start_date", value.start_date), ("end_date", value.end_date)):
        problem = date_problem(raw)
        if problem == "missing":
            return ("missing", f"{label} is empty")
        if problem == "malformed":
            return ("malformed", f"{label} must be a calendar date YYYY-MM-DD")
    if value.start_date > value.end_date:
        return ("wrong", "start_date is after end_date")
    return None


def output_problem(output):
    """A (kind, message) pair, or None when the three fields can name a paper."""
    if output.pmid.strip() == "":
        return ("missing", "pmid is empty")
    if PMID.fullmatch(output.pmid) is None:
        return ("malformed", "pmid is not a PubMed id")
    if type(output.citation_count) is not int or output.citation_count < 0:
        return ("malformed", "citation_count must be zero or greater")
    if type(output.papers_considered) is not int or output.papers_considered < 1:
        return ("malformed", "papers_considered must be at least 1")
    return None


def date_problem(value):
    if value.strip() == "":
        return "missing"
    match = DATE.fullmatch(value)
    if match is None:
        return "malformed"
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if year < 1800 or month < 1 or month > 12 or day < 1 or day > month_length(year, month):
        return "malformed"
    return None


def month_length(year, month):
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return 29 if leap else 28
