---
name: review
description: Run an adversarial find-then-refute review of the current branch, a PR, or the diff against a ref. Six lens-specific finder subagents look for defects, an Opus refuter tries to disprove each finding, and only the survivors are reported. Use when the user asks for an adversarial review, a deep review, or a review "like CI".
argument-hint: "[PR number | base ref]  (blank = this branch against its base)"
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(git symbolic-ref:*), Bash(git ls-files:*), Bash(git fetch:*), Bash(gh pr view:*)
---

Review a code change in three stages: **scope, find, refute**. Then report.
This command only reports. Never edit code, commit, push, or comment on a PR
while running it; what to fix is the user's call.

## 1. Scope

Work out exactly which change to review from `$ARGUMENTS`:

- **Blank**: this branch against its base. Find the base branch with
  `gh pr view --json baseRefName` (the open PR's base), else
  `git symbolic-ref --short refs/remotes/origin/HEAD`, else `origin/main`.
  Take `BASE=$(git merge-base <base> HEAD)`. The diff command is
  `git diff <BASE>`, which covers committed and uncommitted changes to
  tracked files. Also list untracked files with
  `git ls-files --others --exclude-standard`; they are new files and are in
  scope. File contents come from the working tree.
- **A PR number**: `git fetch origin pull/<n>/head` and take
  `HEAD_SHA=$(git rev-parse FETCH_HEAD)`. Get the base from
  `gh pr view <n> --json baseRefName`, fetch it, and take the merge base of
  the two. The diff command is `git diff <BASE> <HEAD_SHA>`. File contents
  come from `git show <HEAD_SHA>:<path>`, because the working tree may be on
  a different branch.
- **Anything else**: treat it as a base ref. The diff command is
  `git diff $(git merge-base <ref> HEAD)`, with untracked files included as
  above.

Use the resolved SHA (not a branch name) in every command you hand to a
subagent, so all of them review the same change.

Get the changed-file list with the same diff plus `--stat`. If nothing
changed, say so and stop. If more than about 60 files changed, tell the user
the review will be shallow at that size and suggest narrowing it, then
carry on unless they stop you.

Check for project guidance: `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, or
a docs folder on conventions. Pass the paths you find to every subagent.

## 2. Find

Launch one `crew:review-finder` subagent per lens below, **all six in
one message** so they run in parallel. Give each one:

- its lens name and description, copied exactly
- the diff command, the changed-file list, any untracked files, and how to
  read file contents (working tree, or `git show <HEAD_SHA>:<path>`)
- the project guidance paths
- the instruction to return its findings in the JSON format from its agent
  definition

The lenses:

1. **correctness**: Does the change do what it claims? Hunt for real bugs:
   logic errors, null, empty and boundary mishandling, race conditions,
   wrong error handling, broken invariants, off-by-one.
2. **simplicity-and-reuse**: Over-engineering, dead code, or a parallel
   implementation of something that already exists. Should this reuse or
   extend an existing helper, pattern or contract instead of adding a new
   one alongside it? Search the codebase before claiming nothing exists.
3. **blast-radius**: Shared contracts, public APIs, data models, schemas and
   migrations. Does the change break existing callers or persisted data with
   no migration or rollback path? Find the callers before claiming they
   break.
4. **test-coverage**: Is each behavioural change covered by a test at the
   right level? Are new branches, error paths and edge cases exercised? Does
   any test assert the wrong thing, or pass whether or not the code works?
5. **security**: Hardcoded secrets, injection (SQL, NoSQL, command,
   template), path traversal, broken authentication or authorisation,
   sensitive data in logs or errors, unsafe deserialisation, SSRF.
6. **architecture-and-design**: Design judgment, not mechanics. Don't
   re-flag what a linter or formatter in this repo already enforces. Is the
   chosen pattern the simplest right fit, or is there a more idiomatic
   approach? Are responsibilities in the right place and abstractions at the
   right level? Do the types model the domain rather than passing strings
   and primitives around? For each new module or public function, ask: is
   its interface nearly as large as its code, and does one design decision
   (a format, a rule, an order of steps) now live in two places? Raise those
   as `minor`, never `blocking`.

When all six return, parse each one's JSON block. If one returns nothing
parsable, note which lens failed in the report rather than retrying silently.

Merge duplicates: findings on the same file within a few lines that describe
the same defect become one finding. Keep the highest severity and list every
lens that raised it. Give each finding an id (F1, F2, ...).

## 3. Refute

With no findings, skip to the report.

Otherwise, group the findings by file and launch one
`crew:review-refuter` subagent per group (split any group above 8
findings), **all in one message**. Give each one the diff command, how to
read file contents, the project guidance paths, and its findings in full
(id, severity, file, line, issue, evidence, suggestion).

Keep findings whose verdict is `confirmed` or `plausible`, at the severity
the refuter returned. Drop the `refuted` ones, but remember them for the
report.

## 4. Report

Start with one line of scope and one of counts, for example:

> Reviewed `feat/retry` against `main` at 3f2a91c, 14 files.
> 11 raised, 7 refuted, 4 survived.

Then the survivors, grouped under **Blocking**, **Major** and **Minor**
(skip empty groups). For each:

- `confirmed` or `plausible`, the lens(es), and `path:line` as a clickable
  reference
- the issue in one sentence
- the evidence: the refuter's reasoning, plus the finder's where it adds
  something
- the suggested fix, when there is one

End with a short **Refuted** list: one line per refuted finding with the
reason it fell. It shows what was checked and lets the user overrule a
refutation they disagree with.

If nothing survived, say so in one line, followed by the Refuted list.

Do not offer to fix anything in the same reply unless the user asks.
