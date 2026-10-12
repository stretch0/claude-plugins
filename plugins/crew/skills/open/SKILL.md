---
name: open
description: Open the unmerged PRs from this session in the browser. Use when the user asks to open, show, or view the PR(s) in the browser or on GitHub.
argument-hint: "[PR numbers or URLs | mine]  (blank = this session's PRs)"
allowed-tools: Bash(gh pr view:*), Bash(gh pr list:*), Bash(git branch:*), Bash(git rev-parse:*)
---

Open PRs in the user's default browser.

## 1. Work out which PRs

From `$ARGUMENTS`:

- **PR numbers or URLs**: use exactly those.
- **`mine`**: every open PR you authored in this repo, from
  `gh pr list --author @me --state open --json url --jq '.[].url'`.
- **Blank**: the PRs this session worked on. Go back through the
  conversation for PRs that were created, pushed to, reviewed, or discussed,
  and use their URLs. Add the current branch's PR if it has one
  (`gh pr view --json url --jq .url`). If the session touched no PRs, use
  only the current branch's PR.

Prefer full URLs, so PRs from other repos the session touched resolve
correctly.

Skip PRs that are already merged. Check each one with
`gh pr view <url> --json number,title,state,url` before opening it. Keep a
merged PR only when the user named it explicitly.

If that comes to more than 5 PRs, list them and ask which to open rather
than opening a wall of tabs.

## 2. Open them

Run `gh pr view <url> --web` once per PR. It opens the PR in the browser and
changes nothing on GitHub.

If no PR is found, say so in one line and suggest `/crew:open mine` or a PR
number.

## 3. Report

One line per PR opened: the number, the title, and the URL, so the user can
click it if the browser didn't open. If any were skipped as merged, add one
line listing them. If every PR was merged, say so instead of opening
anything.
