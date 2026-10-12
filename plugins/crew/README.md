# crew

A [Claude Code](https://claude.com/claude-code) plugin: a small crew of agents for your coding sessions.

| Command | What it does |
| --- | --- |
| `/crew:review` | Adversarial find-then-refute code review of your branch or a PR |
| `/crew:babysit` | One pass over a PR: fix CI, answer and resolve review threads, rebase conflicts |
| `/crew:verify` | Check in a real browser that the change meets its acceptance criteria and designs |
| `/crew:status` | Merge readiness of the session's open PRs: draft, conflicts, behind base, CI, reviews, unresolved threads |
| `/crew:open` | Open the session's unmerged PRs in your browser |
| `/crew:standup` | Catch up on a session after a break, or a Done / Next / Blockers update for your team |

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

## /crew:verify

```
/crew:verify            # this branch's changes
/crew:verify 412        # a PR's changes
/crew:verify the modal  # focus on one part
```

1. **Understand.** Claude reads the diff, then gathers the acceptance criteria (ACs) and designs from the conversation, the PR description, linked tickets and spec files in the repo. It turns them into a checklist: for each AC, the page, the action and what you should see. If a design is referenced but it can't see it, it asks you for it instead of guessing.
2. **Start the app.** It uses the app if it's already running. Otherwise it works out how to start it from the project's docs and scripts, and runs the server in the background.
3. **Verify.** It drives a browser through each checklist item, takes a screenshot and checks that each one actually rendered. It compares against the AC and the design, and checks the console and network log for errors.
4. **Report.** You get a **Pass** or **Needs work** verdict, then a table with one row per AC (how it was checked, the result and the evidence), design differences, console errors, anything it couldn't verify, and how to stop the app.

**Browsers, in order of preference:**
1. Your connected Chrome (Claude in Chrome), which reuses your existing sign-ins
2. The built-in browser
3. A dev browser such as Playwright or `dev-browser`

If the app needs a sign-in the browser doesn't have, it looks for a development sign-in in the project docs, or asks you to sign in. It never types credentials itself.

**Env files in worktrees.** A git worktree starts without the git-ignored `.env` files, and Claude's guardrails stop it copying them directly. The bundled `copy-env.sh` copies them from your main checkout into the worktree, given paths relative to the repo root:

```
copy-env.sh .                  # the root's .env and .env.* files
copy-env.sh apps/web apps/api  # nested folders
copy-env.sh apps/web/.env.dev  # one file
```

It skips `.example`, `.sample` and `.template` files, keeps files already in the worktree unless you pass `--overwrite`, refuses paths outside the repo, and prints file names only. Claude runs it for you during `/crew:verify`, and you can run it yourself from the plugin folder.

It only verifies. It never fixes what it finds, and it leaves the app running so you can look for yourself. Only you can start it; Claude won't run it on its own.

## /crew:status

```
/crew:status          # the PRs this session worked on, plus the current branch's
/crew:status 412 415  # specific PRs (numbers or URLs)
/crew:status mine     # every open PR you authored in this repo
```

Each PR gets a card that leads with a verdict, either **Ready to merge** or **Not ready** followed by every blocker, and then the detail:

```
### #412 Add retry with backoff to the export worker
**Not ready:** 1 failing check(s); 2 review thread(s) without a reply from you.

- Link: https://github.com/acme/app/pull/412
- PR: open, `feat/retry` into `main`, +120 -30 across 6 file(s), updated 2h ago
- Merge: no conflicts, 3 commit(s) behind `main`
- CI: 21 passed, 1 failed, 0 running (failing: Test (Python))
- Reviews: approved by alice; waiting on bob
- Threads: 3 unresolved, 2 without a reply from you, 1 on outdated code
- Labels: feature
- Closes: #398
```

Merged PRs are left out and listed in a one-line footer, unless you name one explicitly. Each card has a plain Link line you can click even where the title link doesn't render.

It also covers draft state, auto-merge, changes requested, and branch protection blocks. A bundled script gathers the data with three read-only GitHub calls per PR, so the cards come out the same every time and run without permission prompts. After the cards, Claude adds at most two lines: anything from the session that explains a card, and the one action that would unblock the most.

## /crew:open

```
/crew:open            # the PRs this session worked on
/crew:open 412        # a specific PR
/crew:open mine       # every open PR you authored in this repo
```

Opens each PR in your default browser with `gh pr view --web`, and lists the URLs in case the browser didn't open. It skips merged PRs unless you name one explicitly. Above 5 PRs it asks which ones you want instead of opening them all.

## /crew:standup

```
/crew:standup
/crew:standup for slack
/crew:standup just the API work
```

Use it when you come back to a session after a while and can't remember where you were. It opens with a **Picking up** block:

```
**Picking up**
Goal: add retry with backoff to the export worker (PR #412)
You stopped: slice 2 of 3, tests for the backoff cap were failing
Waiting on you: should retries give up after 5 tries or 2 minutes?
Since you left: CI on #412 finished (1 failing), Copilot left a review, main is 6 commits ahead
```

Then come **Done**, **Next** and **Blockers**. The first item under Next is the concrete place to start. With an audience such as `for slack`, it drops the Picking up block and gives a team update ready to paste.

The update is built mainly from the conversation. It also reads the git state of the repos the session touched: the branch, uncommitted changes, commits not yet on the base branch, and the open PR with its checks. Those reads catch work that has scrolled out of context and correct the session where git disagrees. Only verified work is listed as done, and every blocker says what it's waiting on. It only reads, and its `git` and `gh` commands run without permission prompts.

You can also just ask "where was I?", "catch me up" or "where are we?" and Claude will use it.

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
