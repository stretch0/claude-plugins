"""Print a status card for each GitHub PR given on the command line.

Usage: python3 pr_status.py [--skip-merged] <PR number | PR URL | branch> [...]

With no PR given it reports the current branch's PR. --skip-merged leaves
merged PRs out of the cards and lists them in one footer line instead.

Run it inside the repository the PRs belong to, or pass full PR URLs. Each
PR costs three read-only GitHub calls: `gh pr view`, one GraphQL query for
review threads, and one compare for how far the branch is behind its base.
A PR that cannot be read gets a one-line error card instead of stopping the
others.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

PR_FIELDS = ",".join(
    [
        "number", "title", "url", "state", "isDraft", "mergeable",
        "mergeStateStatus", "reviewDecision", "reviewRequests", "latestReviews",
        "statusCheckRollup", "headRefName", "headRefOid", "baseRefName",
        "autoMergeRequest", "labels", "additions", "deletions", "changedFiles",
        "updatedAt", "closingIssuesReferences",
    ]
)

THREADS_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  viewer { login }
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          isOutdated
          comments(last: 1) { nodes { author { login } } }
        }
      }
    }
  }
}
"""

PASSING = {"SUCCESS", "NEUTRAL", "SKIPPED"}
PENDING_STATES = {"PENDING", "EXPECTED"}


class GitHubReadError(Exception):
    pass


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise GitHubReadError(result.stderr.strip() or f"gh {args[0]} failed")
    return result.stdout


@dataclass
class Checks:
    passed: int = 0
    pending: int = 0
    failed: list[str] = field(default_factory=list)


@dataclass
class Threads:
    unresolved: int = 0
    awaiting_you: int = 0
    outdated: int = 0


def read_checks(rollup: list[dict]) -> Checks:
    checks = Checks()
    for check in rollup:
        name = check.get("name") or check.get("context") or "?"
        if check.get("__typename") == "StatusContext":
            state = check.get("state", "")
            if state in PENDING_STATES:
                checks.pending += 1
            elif state == "SUCCESS":
                checks.passed += 1
            else:
                checks.failed.append(name)
        elif check.get("status") != "COMPLETED":
            checks.pending += 1
        elif check.get("conclusion") in PASSING:
            checks.passed += 1
        else:
            checks.failed.append(name)
    return checks


def read_threads(owner: str, repo: str, number: int, host: str) -> Threads:
    raw = gh(
        "api", "graphql", "--hostname", host,
        "-f", f"query={THREADS_QUERY}",
        "-f", f"owner={owner}", "-f", f"repo={repo}", "-F", f"number={number}",
    )
    data = json.loads(raw)["data"]
    me = data["viewer"]["login"]
    threads = Threads()
    for thread in data["repository"]["pullRequest"]["reviewThreads"]["nodes"]:
        if thread["isResolved"]:
            continue
        threads.unresolved += 1
        threads.outdated += thread["isOutdated"]
        comments = thread["comments"]["nodes"]
        author = (comments[-1].get("author") or {}).get("login") if comments else None
        threads.awaiting_you += author != me
    return threads


def commits_behind(owner: str, repo: str, base: str, head_sha: str, host: str) -> int | None:
    try:
        raw = gh("api", "--hostname", host, f"repos/{owner}/{repo}/compare/{base}...{head_sha}", "--jq", ".behind_by")
        return int(raw.strip())
    except (GitHubReadError, ValueError):
        return None


def ago(timestamp: str) -> str:
    then = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    minutes = int((datetime.now(timezone.utc) - then).total_seconds() // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    if minutes < 48 * 60:
        return f"{minutes // 60}h ago"
    return f"{minutes // (60 * 24)}d ago"


def describe_reviews(pr: dict) -> str:
    by_state: dict[str, list[str]] = {}
    for review in pr.get("latestReviews") or []:
        login = (review.get("author") or {}).get("login", "?")
        by_state.setdefault(review.get("state", ""), []).append(login)
    parts = []
    if by_state.get("APPROVED"):
        parts.append("approved by " + ", ".join(by_state["APPROVED"]))
    if by_state.get("CHANGES_REQUESTED"):
        parts.append("changes requested by " + ", ".join(by_state["CHANGES_REQUESTED"]))
    requested = [r.get("login") or r.get("name") or r.get("slug") or "?" for r in pr.get("reviewRequests") or []]
    if requested:
        parts.append("waiting on " + ", ".join(requested))
    decision = {"REVIEW_REQUIRED": "review required", "APPROVED": "approved", "CHANGES_REQUESTED": "changes requested"}
    if not parts:
        return decision.get(pr.get("reviewDecision") or "", "no reviews yet")
    return "; ".join(parts)


def blockers(pr: dict, checks: Checks, threads: Threads | None, behind: int | None) -> list[str]:
    found = []
    if pr.get("isDraft"):
        found.append("still a draft")
    if pr.get("mergeable") == "CONFLICTING" or pr.get("mergeStateStatus") == "DIRTY":
        found.append(f"conflicts with `{pr['baseRefName']}`")
    if checks.failed:
        found.append(f"{len(checks.failed)} failing check(s)")
    if pr.get("reviewDecision") == "CHANGES_REQUESTED":
        found.append("changes requested")
    if threads and threads.awaiting_you:
        found.append(f"{threads.awaiting_you} review thread(s) without a reply from you")
    if checks.pending:
        found.append(f"{checks.pending} check(s) still running")
    if pr.get("reviewDecision") == "REVIEW_REQUIRED":
        found.append("needs an approving review")
    if pr.get("mergeStateStatus") == "BEHIND":
        found.append(f"branch is behind `{pr['baseRefName']}` and must be updated")
    if not found and pr.get("mergeStateStatus") == "BLOCKED":
        found.append("blocked by a branch protection rule")
    return found


def verdict(pr: dict, found: list[str]) -> str:
    if pr["state"] == "MERGED":
        return "**Merged.**"
    if pr["state"] == "CLOSED":
        return "**Closed without merging.**"
    if found:
        return "**Not ready:** " + "; ".join(found) + "."
    if pr.get("mergeStateStatus") in ("CLEAN", "HAS_HOOKS", "UNSTABLE"):
        return "**Ready to merge.**"
    return "**Probably ready.** GitHub is still computing mergeability."


def merge_line(pr: dict, behind: int | None) -> str:
    parts = []
    if pr.get("mergeable") == "CONFLICTING":
        parts.append("has conflicts")
    elif pr.get("mergeable") == "MERGEABLE":
        parts.append("no conflicts")
    else:
        parts.append("mergeability still being computed")
    if behind:
        parts.append(f"{behind} commit(s) behind `{pr['baseRefName']}`")
    elif behind == 0:
        parts.append(f"up to date with `{pr['baseRefName']}`")
    if pr.get("autoMergeRequest"):
        parts.append("auto-merge is on")
    return ", ".join(parts)


def fetch_pr(ref: str) -> dict:
    return json.loads(gh("pr", "view", ref, "--json", PR_FIELDS))


def card(pr: dict) -> str:
    url = urlparse(pr["url"])
    owner, repo = url.path.strip("/").split("/")[:2]
    host = url.hostname or "github.com"
    checks = read_checks(pr.get("statusCheckRollup") or [])
    try:
        threads = read_threads(owner, repo, pr["number"], host)
    except (GitHubReadError, KeyError, ValueError):
        threads = None
    behind = None if pr["state"] != "OPEN" else commits_behind(owner, repo, pr["baseRefName"], pr["headRefOid"], host)

    lines = [f"### [#{pr['number']} {pr['title']}]({pr['url']})", verdict(pr, blockers(pr, checks, threads, behind)), ""]
    # A bare URL stays clickable in terminals that don't render markdown links.
    lines.append(f"- **Link:** {pr['url']}")
    draft = " (draft)" if pr.get("isDraft") else ""
    lines.append(
        f"- **PR:** {pr['state'].lower()}{draft}, `{pr['headRefName']}` into `{pr['baseRefName']}`, "
        f"+{pr['additions']} -{pr['deletions']} across {pr['changedFiles']} file(s), updated {ago(pr['updatedAt'])}"
    )
    if pr["state"] == "OPEN":
        lines.append(f"- **Merge:** {merge_line(pr, behind)}")
    ci = f"{checks.passed} passed, {len(checks.failed)} failed, {checks.pending} running"
    if checks.failed:
        ci += " (failing: " + ", ".join(checks.failed) + ")"
    lines.append(f"- **CI:** {ci}" if pr.get("statusCheckRollup") else "- **CI:** no checks reported")
    lines.append(f"- **Reviews:** {describe_reviews(pr)}")
    if threads is None:
        lines.append("- **Threads:** could not be read")
    else:
        detail = f"{threads.unresolved} unresolved, {threads.awaiting_you} without a reply from you"
        if threads.outdated:
            detail += f", {threads.outdated} on outdated code"
        lines.append(f"- **Threads:** {detail}")
    labels = [label["name"] for label in pr.get("labels") or []]
    if labels:
        lines.append("- **Labels:** " + ", ".join(labels))
    issues = [f"#{issue['number']}" for issue in pr.get("closingIssuesReferences") or []]
    if issues:
        lines.append("- **Closes:** " + ", ".join(issues))
    return "\n".join(lines) + "\n"


def current_branch() -> str:
    try:
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    return result.stdout.strip()


def main() -> None:
    args = sys.argv[1:]
    skip_merged = "--skip-merged" in args
    refs = [arg for arg in args if arg != "--skip-merged"] or [current_branch()]
    if refs == [""]:
        print("No PR given, and there is no current branch to look up.")
        return

    cards, merged = [], []
    for ref in refs:
        try:
            pr = fetch_pr(ref)
        except GitHubReadError as error:
            cards.append(f"### {ref}\nCould not read this PR: {error}\n")
            continue
        if skip_merged and pr["state"] == "MERGED":
            merged.append(f"#{pr['number']} {pr['url']}")
        else:
            cards.append(card(pr))

    if not cards:
        cards.append("No open PRs to report.\n")
    if merged:
        cards.append("Already merged, not shown: " + ", ".join(merged))
    print("\n".join(cards))


if __name__ == "__main__":
    main()
