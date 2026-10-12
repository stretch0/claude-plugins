---
name: status
description: Show the GitHub status of the PRs from this session, covering whether each is ready to merge, draft state, conflicts, how far behind its base it is, failing CI, reviews, and unresolved review threads. Use when the user asks for PR status, "is it green?", "can I merge?", or "what's left on the PR?".
argument-hint: "[PR numbers or URLs | mine]  (blank = this session's PRs)"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/pr_status.py:*), Bash(gh pr list:*), Bash(git branch:*), Bash(git rev-parse:*)
---

Show a status card for each relevant PR. This command only reads. Never
push, comment, merge, or change a PR while running it.

## 1. Work out which PRs

From `$ARGUMENTS`:

- **PR numbers or URLs**: use exactly those.
- **`mine`**: every open PR you authored in this repo, from
  `gh pr list --author @me --state open --json url --jq '.[].url'`.
- **Blank**: the PRs this session worked on. Go back through the
  conversation for PRs that were created, pushed to, reviewed, or discussed,
  and use their URLs. Add the current branch's PR if it has one. If the
  session touched no PRs, use only the current branch's PR.

Prefer full URLs, so PRs from other repos the session touched resolve
correctly. A bare number resolves against the current directory's repo.

## 2. Get the status

Run, with every PR in one call:

```
python3 ${CLAUDE_SKILL_DIR}/pr_status.py <url-or-number> [...]
```

With no arguments it reports the current branch's PR.

## 3. Report

Show the script's output as it is. Its cards already lead with a verdict and
list every blocker, so don't restate them. Then add at most two lines:

- If something in the session explains a card (a fix already pushed for the
  failing check, a reply already drafted), say so.
- If one action would unblock the most, name it. For example, run
  `/crew:babysit 412` for failing CI or unanswered threads, or update the
  branch when it's behind a base that requires it.

Never offer to merge.
