"""Pick the top-cited paper. The verifier's rank.py implements this same rule."""


def choose_top(papers):
    """Return the paper with the highest citation_count; equal counts select the smaller PMID."""
    if not papers:
        raise ValueError("no papers to rank")
    winner = papers[0]
    for paper in papers[1:]:
        higher = paper["citation_count"] > winner["citation_count"]
        tied = paper["citation_count"] == winner["citation_count"] and int(paper["pmid"]) < int(winner["pmid"])
        if higher or tied:
            winner = paper
    return {"pmid": winner["pmid"], "citation_count": winner["citation_count"]}
