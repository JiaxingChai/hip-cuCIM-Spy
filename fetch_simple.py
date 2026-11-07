import os
import json
import requests
from pathlib import Path
from datetime import datetime

TOKEN = os.environ["GH_PAT"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"

REPOS = [
    {"owner": "rapidsai", "repo": "cucim"},
    {"owner": "rapidsai", "repo": "hipcim"},
]

BASE_DIR = Path(".")
STATE_DIR = BASE_DIR / "sync_state"
ARCHIVE_ROOT = BASE_DIR / "archive"

STATE_DIR.mkdir(exist_ok=True)
ARCHIVE_ROOT.mkdir(exist_ok=True)

run_date = datetime.utcnow().strftime("%Y-%m-%d")
out_dir = ARCHIVE_ROOT / run_date
out_dir.mkdir(exist_ok=True)


def run_graphql(query, variables):
    resp = requests.post(
        GRAPHQL_URL,
        headers=HEADERS,
        json={"query": query, "variables": variables}
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL error: {payload['errors']}")
    return payload


def fetch_commits(owner, repo, state_file: Path):
    last_hash = None
    if state_file.exists():
        last_hash = state_file.read_text().strip()

    query = """
    query($o: String!, $r: String!, $cursor: String) {
      repository(owner: $o, name: $r) {
        ref(qualifiedName: "main") {
          target {
            ... on Commit {
              history(first: 100, after: $cursor) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                nodes {
                  oid
                  messageHeadline
                  message
                  committedDate
                  author {
                    name
                    email
                  }
                  changedFiles
                  additions
                  deletions
                }
              }
            }
          }
        }
      }
    }
    """

    all_nodes = []
    cursor = None
    while True:
        data = run_graphql(query, {"o": owner, "r": repo, "cursor": cursor})
        hist = data["data"]["repository"]["ref"]["target"]["history"]
        all_nodes.extend(hist["nodes"])
        if not hist["pageInfo"]["hasNextPage"]:
            break
        cursor = hist["pageInfo"]["endCursor"]

    if all_nodes:
        new_tip = all_nodes[0]["oid"]
        state_file.write_text(new_tip)

    return all_nodes


def paginate_issues(owner, repo, since):
    query = """
    query($o: String!, $r: String!, $since: String!, $cursor: String) {
      repository(owner: $o, name: $r) {
        issues(
          first: 100
          after: $cursor
          filterBy: { since: $since }
          states: [OPEN, CLOSED]
        ) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            number
            title
            url
            body
            state
            createdAt
            closedAt
            labels(first: 15) {
              nodes {
                name
              }
            }
          }
        }
      }
    }
    """
    items = []
    cur = None
    while True:
        res = run_graphql(query, {"o": owner, "r": repo, "since": since, "cursor": cur})
        chunk = res["data"]["repository"]["issues"]
        items.extend(chunk["nodes"])
        if not chunk["pageInfo"]["hasNextPage"]:
            break
        cur = chunk["pageInfo"]["endCursor"]
    return items


def paginate_prs(owner, repo, since):
    query = """
    query($o: String!, $r: String!, $since: String!, $cursor: String) {
      repository(owner: $o, name: $r) {
        pullRequests(
          first: 100
          after: $cursor
          filterBy: { since: $since }
          states: [OPEN, CLOSED, MERGED]
        ) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            number
            title
            url
            body
            state
            createdAt
            closedAt
            mergedAt
            labels(first: 15) {
              nodes {
                name
              }
            }
          }
        }
      }
    }
    """
    items = []
    cur = None
    while True:
        res = run_graphql(query, {"o": owner, "r": repo, "since": since, "cursor": cur})
        chunk = res["data"]["repository"]["pullRequests"]
        items.extend(chunk["nodes"])
        if not chunk["pageInfo"]["hasNextPage"]:
            break
        cur = chunk["pageInfo"]["endCursor"]
    return items


def fetch_issues_and_prs(owner, repo, state_file: Path):
    since = "2020-01-01T00:00:00Z"
    if state_file.exists():
        since = state_file.read_text().strip()

    now_iso = datetime.utcnow().isoformat() + "Z"
    issues = paginate_issues(owner, repo, since)
    prs = paginate_prs(owner, repo, since)
    state_file.write_text(now_iso)
    return issues, prs


for entry in REPOS:
    owner = entry["owner"]
    repo = entry["repo"]
    prefix = repo

    tip_path = STATE_DIR / f"{prefix}_tip.txt"
    since_path = STATE_DIR / f"{prefix}_since.txt"

    commits = fetch_commits(owner, repo, tip_path)
    issues, prs = fetch_issues_and_prs(owner, repo, since_path)

    with open(out_dir / f"{prefix}_commits.json", "w", encoding="utf-8") as f:
        json.dump(commits, f, ensure_ascii=False, indent=2)
    with open(out_dir / f"{prefix}_prs.json", "w", encoding="utf-8") as f:
        json.dump(prs, f, ensure_ascii=False, indent=2)
    with open(out_dir / f"{prefix}_issues.json", "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)

print("fetch completed")
