import os
import json
import requests
from pathlib import Path
from datetime import datetime

TOKEN = os.environ["GH_PAT"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"

# Correct repos
REPOS = [
    {"owner": "rapidsai", "repo": "cucim"},
    {"owner": "AMD-Ecosystem", "repo": "hipCIM"},
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
        try:
            data = run_graphql(query, {"o": owner, "r": repo, "cursor": cursor})
        except RuntimeError as e:
            print(f"[WARN] fetch commits {owner}/{repo}: {e}")
            return []
        repo_obj = data["data"]["repository"]
        ref_obj = repo_obj["ref"]
        if ref_obj is None:
            print(f"[WARN] {owner}/{repo}: ref main not found")
            break
        hist = ref_obj["target"]["history"]
        all_nodes.extend(hist["nodes"])
        if not hist["pageInfo"]["hasNextPage"]:
            break
        cursor = hist["pageInfo"]["endCursor"]

    if all_nodes:
        new_tip = all_nodes[0]["oid"]
        state_file.write_text(new_tip)
    return all_nodes


def paginate_all_issues(owner, repo):
    query = """
    query($o: String!, $r: String!, $cursor: String) {
      repository(owner: $o, name: $r) {
        issues(first:100, after:$cursor, states:[OPEN, CLOSED]) {
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
            labels(first:15) { nodes { name } }
          }
        }
      }
    }
    """
    items = []
    cur = None
    while True:
        res = run_graphql(query, {"o": owner, "r": repo, "cursor": cur})
        chunk = res["data"]["repository"]["issues"]
        items.extend(chunk["nodes"])
        if not chunk["pageInfo"]["hasNextPage"]:
            break
        cur = chunk["pageInfo"]["endCursor"]
    return items


def paginate_all_prs(owner, repo):
    query = """
    query($o: String!, $r: String!, $cursor: String) {
      repository(owner: $o, name: $r) {
        pullRequests(first:100, after:$cursor, states:[OPEN, CLOSED, MERGED]) {
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
            labels(first:15) { nodes { name } }
          }
        }
      }
    }
    """
    items = []
    cur = None
    while True:
        res = run_graphql(query, {"o": owner, "r": repo, "cursor": cur})
        chunk = res["data"]["repository"]["pullRequests"]
        items.extend(chunk["nodes"])
        if not chunk["pageInfo"]["hasNextPage"]:
            break
        cur = chunk["pageInfo"]["endCursor"]
    return items


def fetch_issues_and_prs(owner, repo, state_file: Path):
    since_str = "2020-01-01T00:00:00Z"
    if state_file.exists():
        since_str = state_file.read_text().strip()
    since_dt = datetime.fromisoformat(since_str.replace("Z", "+00:00"))

    raw_issues = paginate_all_issues(owner, repo)
    raw_prs = paginate_all_prs(owner, repo)

    def filter_by_time(records):
        out = []
        for rec in records:
            t = datetime.fromisoformat(rec["createdAt"].replace("Z", "+00:00"))
            if t >= since_dt:
                out.append(rec)
        return out

    filtered_issues = filter_by_time(raw_issues)
    filtered_prs = filter_by_time(raw_prs)

    now_iso = datetime.utcnow().isoformat() + "Z"
    state_file.write_text(now_iso)
    return filtered_issues, filtered_prs


for entry in REPOS:
    owner = entry["owner"]
    repo = entry["repo"]
    prefix = repo

    tip_path = STATE_DIR / f"{prefix}_tip.txt"
    since_path = STATE_DIR / f"{prefix}_since.txt"

    print(f"==== Fetching {owner}/{repo} ====")
    commits = fetch_commits(owner, repo, tip_path)
    issues, prs = fetch_issues_and_prs(owner, repo, since_path)

    with open(out_dir / f"{prefix}_commits.json", "w", encoding="utf-8") as f:
        json.dump(commits, f, ensure_ascii=False, indent=2)
    with open(out_dir / f"{prefix}_prs.json", "w", encoding="utf-8") as f:
        json.dump(prs, f, ensure_ascii=False, indent=2)
    with open(out_dir / f"{prefix}_issues.json", "w", encoding="utf-8") as f:
        json.dump(issues, f, ensure_ascii=False, indent=2)

print("fetch completed successfully")
