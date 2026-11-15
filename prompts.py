"""The questions we send to Cala, kept in one place.

Each function returns the text to pass to cala.knowledge_search() or
cala.knowledge_query(). Edit the wording here to change what the app asks.
"""


def _investor(name, about):
    """Name the investor, adding a description when the name alone is ambiguous."""
    return "{} ({})".format(name, about) if about else name


def investor_profile(name, about=""):
    """For cala.knowledge_search(): a founder's briefing on one investor."""
    return (
        "Give a founder a short briefing on the investor {name}, a few "
        "sentences per topic. Cover: what kind of investor they are, the stages "
        "and sectors they invest in, typical check size, and where they are based."
    ).format(name=_investor(name, about))


def investor_portfolio(name, about=""):
    """For cala.knowledge_query(): the investor's deals as structured rows."""
    return (
        "List the companies {name} has invested in, with the company name, "
        "sector, funding round type, round amount, and year."
    ).format(name=_investor(name, about))


def worth_a_call(name, about=""):
    """For cala.knowledge_query(): founders who saw the investor when things went badly."""
    return (
        "List companies that {name} invested in that later failed, shut down, "
        "went bankrupt, were sold at a loss, or are struggling (large layoffs, "
        "down rounds). For each give the company name, its founders, what "
        "happened, and the year."
    ).format(name=_investor(name, about))


def company_founders(company):
    """For cala.knowledge_query(): who founded one company."""
    return (
        "Who founded the company {company}? List each founder's name and their "
        "role at the company."
    ).format(company=company)


def find_investors(description):
    """For cala.knowledge_query(): investors matching what a founder is looking for."""
    return (
        "List investors that match this description: {description}. For each "
        "investor give the name, investor type, stage focus, sector focus, "
        "location, and a notable investment."
    ).format(description=description)
