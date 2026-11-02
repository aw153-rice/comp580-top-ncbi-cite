"""Offline ranking cases shared by the plugin and the verifier."""

import pytest

from plugin.rank import choose_top as plugin_choose
from verifier.rank import choose_top as verifier_choose

TIED = [
    {"pmid": "250", "citation_count": 4},
    {"pmid": "100", "citation_count": 4},
]
HIGHER = [
    {"pmid": "10", "citation_count": 1},
    {"pmid": "20", "citation_count": 5},
]
ZERO = [{"pmid": "5", "citation_count": 0}]
THREE = [
    {"pmid": "9", "citation_count": 3},
    {"pmid": "8", "citation_count": 3},
    {"pmid": "7", "citation_count": 2},
]


@pytest.mark.parametrize("papers", [TIED, HIGHER, ZERO, THREE])
def test_rankers_agree(papers):
    assert plugin_choose(papers) == verifier_choose(papers)


def test_tie_selects_the_lower_pmid():
    assert plugin_choose(TIED) == {"pmid": "100", "citation_count": 4}


def test_empty_rows_raise():
    with pytest.raises(ValueError, match="no papers"):
        plugin_choose([])
    with pytest.raises(ValueError, match="no papers"):
        verifier_choose([])
