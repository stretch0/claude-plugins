# adversarial-review

A [Claude Code](https://claude.com/claude-code) plugin that runs a find-then-refute code review in your local session.

```
/adversarial-review:review          # this branch against its base, including uncommitted changes
/adversarial-review:review 123      # PR #123, without checking it out
/adversarial-review:review develop  # this branch against another base
```

## How it works

1. **Find.** Six finder subagents (on Sonnet) review the diff in parallel. Each one looks through a single lens: correctness, simplicity and reuse, blast radius, test coverage, security, or architecture and design. Each lens gets its own reviewer so that a blind spot in one doesn't hide issues from the others.
2. **Refute.** An Opus refuter tries to disprove every finding against the real code. It reads the whole file, the callers and the project config. Findings that are speculative, already handled, or deliberate are dropped.
3. **Report.** The survivors are listed by severity (blocking, major, minor). Each is marked `confirmed` when the refuter traced it conclusively, or `plausible` when the trace depends on something it couldn't see. Refuted findings get one line each with the reason, so you can overrule a refutation you disagree with.

The subagents start with a fresh context and haven't seen the work being reviewed. Every agent is read-only. The command never edits code, commits or comments on a PR.

`blocking` is kept for fatal flaws: the change breaks in production, corrupts existing data, or opens a security hole. Style and naming points are always `minor`.

## Cost

A review runs six Sonnet finders plus one Opus refuter per file with findings. On a typical PR that's a few minutes and noticeably more tokens than a single-pass review, so it's meant for changes worth a second look. Above about 60 changed files it warns you and suggests narrowing the scope.

## Install

```
/plugin marketplace add stretch0/claude-plugins
/plugin install adversarial-review@stretch0
```

## Requirements

`git`. For PR numbers, the [GitHub CLI](https://cli.github.com/) (`gh`) is also needed, logged in to an account that can read the repo.
