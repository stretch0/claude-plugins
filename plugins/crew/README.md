# crew

A [Claude Code](https://claude.com/claude-code) plugin: a small crew of agents for your coding sessions.

| Command | What it does |
| --- | --- |
| `/crew:review` | Adversarial find-then-refute code review of your branch or a PR |
| `/crew:babysit` | One pass over a PR: fix CI, answer and resolve review threads, rebase conflicts |
| `/crew:standup` | Done / Next / Blockers update for the current session |

It also adds **PR-watching hooks** that keep Claude responsible for the PRs it pushes.

None of it ever merges a PR or enables auto-merge. That stays with you.

## Install

```
/plugin marketplace add stretch0/claude-plugins
/plugin install crew@stretch0
```

This installs at **user scope** by default, so it applies to every project you open and nobody else is affected. Pick project scope during install to share it with everyone on a repo.

## /crew:review

```
/crew:review          # this branch against its base, including uncommitted changes
/crew:review 123      # PR #123, without checking it out
/crew:review develop  # this branch against another base
```

1. **Find.** Six finder subagents (on Sonnet) review the diff in parallel. Each one looks through a single lens: correctness, simplicity and reuse, blast radius, test coverage, security, or architecture and design. Each lens gets its own reviewer so that a blind spot in one doesn't hide issues from the others.
2. **Refute.** An Opus refuter tries to disprove every finding against the real code. It reads the whole file, the callers and the project config. Findings that are speculative, already handled, or deliberate are dropped.
3. **Report.** The survivors are listed by severity (blocking, major, minor). Each is marked `confirmed` when the refuter traced it conclusively, or `plausible` when the trace depends on something it couldn't see. Refuted findings get one line each with the reason, so you can overrule a refutation you disagree with.

The subagents start with a fresh context and haven't seen the work being reviewed. Every agent is read-only, and the command never edits code or comments on a PR. `blocking` is kept for fatal flaws: the change breaks in production, corrupts existing data, or opens a security hole.

A review runs six Sonnet finders plus one Opus refuter per file with findings, so it costs noticeably more than a single-pass review. Only you can start it; Claude won't run it on its own. Above about 60 changed files it warns you and suggests narrowing the scope.

## /crew:babysit and the PR-watching hooks

**After every `git push` or `gh pr create`**, a hook reads the PR's CI, merge state and review threads, and tells Claude what to do next. If checks are pending, Claude starts a background `gh pr checks --watch`, which wakes it when they finish. If checks fail, the branch conflicts, or review threads are waiting on a reply, Claude is told to deal with it in the same turn.

**When Claude tries to end the session**, a stop hook checks every PR the session pushed. If any has failing CI, a merge conflict, or review threads waiting on a reply, the session continues instead of stopping. It forces one continuation at most, so a problem Claude can't fix won't trap you.

A review thread counts as waiting when it's unresolved and its last comment isn't from the account `gh` is logged in as. A thread Claude already answered and left open for the reviewer doesn't count. A comment you leave on your own PR from the same account doesn't count either.

**`/crew:babysit [PR number]`** makes one pass. It fixes failing CI (at most 3 attempts per failure type), replies to and resolves review threads, rebases conflicts, and reports "merge-ready" when everything is clear. It escalates design questions, security findings and deployment failures to you instead of guessing.

The hooks only look when Claude pushes or tries to stop. A review that arrives after the session has gone idle won't wake it. To keep working through review feedback while you do something else, loop the command:

```
/loop 10m /crew:babysit 123
```

## /crew:standup

```
/crew:standup
/crew:standup for slack
/crew:standup just the API work
```

The update is built mainly from the conversation. It also reads the git state of the repos the session touched: the branch, uncommitted changes, commits not yet on the base branch, and the open PR with its checks. Those reads catch work that has scrolled out of context and correct the session where git disagrees. Only verified work is listed as done, and every blocker says what it's waiting on. It only reads, and its `git` and `gh` commands run without permission prompts.

You can also just ask "where are we?" and Claude will use it.

## Configuration

| Environment variable | Default | Effect |
| --- | --- | --- |
| `CREW_PR_WATCH` | `1` | Set to `0` to turn the PR-watching hooks off. The commands stay available. Useful in a repo that ships its own PR hooks. |
| `CREW_REQUIRE_SIGNED` | unset | Set to `1` to also check that GitHub verified the pushed commit's signature, and tell Claude to fix it when it didn't. |

Set them in your shell, under `env` in `~/.claude/settings.json`, or for one repo only under `env` in that repo's `.claude/settings.local.json`.

## Requirements

- `git`, `bash` and `python3` on your `PATH`
- [GitHub CLI](https://cli.github.com/) (`gh`), logged in to an account that can read the repo, for anything involving PRs

## How the hooks work

`hooks/post-push-pr-status.sh` runs after each Bash call and returns immediately unless the command is a `git push` or `gh pr create`. It treats a newline as a command separator, so a `gh pr create` on its own line after a heredoc still counts. On a match, it records the branch in a per-session file under `$TMPDIR` and returns the PR status to Claude as extra context.

`hooks/stop-pr-gate.sh` runs when Claude tries to stop. It reads that per-session file, looks up each PR, and blocks the stop if any open PR is red, conflicting, or has review threads waiting on a reply. Pending checks never block, because the background watcher already handles them. Entries expire after 48 hours, and closed or merged PRs are dropped.

`hooks/awaiting_review_threads.py` is the thread counter both hooks share. It makes one GraphQL call per PR.
