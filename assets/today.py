import datetime
import os

import requests
from dateutil import relativedelta
from lxml import etree

HEADERS = {"authorization": "token " + os.environ["ACCESS_TOKEN"]}
USER_NAME = os.environ["USER_NAME"]

# Nicolaas started freelancing in 2022; exact day isn't tracked anywhere, so
# this uses Jan 1 as a stand-in. Update if a more precise date is known.
FREELANCE_START = datetime.datetime(2022, 1, 1)


def simple_request(name, query, variables):
    request = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    if request.status_code == 200:
        return request
    raise Exception(name, "failed with", request.status_code, request.text)


def uptime_string():
    diff = relativedelta.relativedelta(datetime.datetime.today(), FREELANCE_START)

    def plural(n):
        return "s" if n != 1 else ""

    return "{} year{}, {} month{}, {} day{}".format(
        diff.years, plural(diff.years),
        diff.months, plural(diff.months),
        diff.days, plural(diff.days),
    )


def repos_and_stars():
    query = """
    query ($login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: [OWNER], isFork: false) {
                totalCount
                edges { node { stargazers { totalCount } } }
                pageInfo { endCursor hasNextPage }
            }
        }
    }"""
    total_repos = 0
    total_stars = 0
    cursor = None
    while True:
        request = simple_request("repos_and_stars", query, {"login": USER_NAME, "cursor": cursor})
        repositories = request.json()["data"]["user"]["repositories"]
        total_repos = repositories["totalCount"]
        total_stars += sum(
            edge["node"]["stargazers"]["totalCount"]
            for edge in repositories["edges"]
            if edge["node"] is not None
        )
        if not repositories["pageInfo"]["hasNextPage"]:
            break
        cursor = repositories["pageInfo"]["endCursor"]
    return total_repos, total_stars


def follower_count():
    query = """
    query ($login: String!) {
        user(login: $login) { followers { totalCount } }
    }"""
    request = simple_request("follower_count", query, {"login": USER_NAME})
    return int(request.json()["data"]["user"]["followers"]["totalCount"])


def contributions_past_year():
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=365)
    query = """
    query ($login: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
                contributionCalendar { totalContributions }
            }
        }
    }"""
    variables = {
        "login": USER_NAME,
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    request = simple_request("contributions_past_year", query, variables)
    return int(
        request.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    )


def find_and_replace(root, element_id, new_text):
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = new_text


def update_svg(filename, uptime, repos, stars, followers, contributions):
    tree = etree.parse(filename)
    root = tree.getroot()
    find_and_replace(root, "uptime_data", uptime)
    find_and_replace(root, "repo_data", "{:,}".format(repos))
    find_and_replace(root, "star_data", "{:,}".format(stars))
    find_and_replace(root, "follower_data", "{:,}".format(followers))
    find_and_replace(root, "contrib_data", "{:,}".format(contributions))
    tree.write(filename, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    uptime = uptime_string()
    repos, stars = repos_and_stars()
    followers = follower_count()
    contributions = contributions_past_year()

    print("Uptime:", uptime)
    print("Repos:", repos, "Stars:", stars)
    print("Followers:", followers)
    print("Contributions (past year):", contributions)

    update_svg(os.path.join(os.path.dirname(__file__), "dark_mode.svg"), uptime, repos, stars, followers, contributions)
    update_svg(os.path.join(os.path.dirname(__file__), "light_mode.svg"), uptime, repos, stars, followers, contributions)
