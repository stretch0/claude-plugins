---
name: standup
description: Give a stand-up update for the current session covering what's been done, what's next, and any blockers. Use when the user asks for a stand-up, status update, progress summary, or "where are we?".
argument-hint: "[optional focus or audience, e.g. \"for slack\" or \"just the API work\"]"
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git symbolic-ref:*), Bash(gh pr view:*), Bash(gh pr checks:*), Bash(gh pr list:*)
---

Write a short stand-up update for the work in this session. The session is
the main source. The repository fills in what has scrolled out of context
and confirms what the session claims.

This skill only reads. Never commit, push, edit files, or change a PR while
running it.

## 1. Read the session

Go back through the conversation and collect:

- what the user asked for, including requests that changed along the way
- what was finished, and how you know it's finished (tests passed, PR opened,
  the user confirmed)
- what was started but not finished
- what is waiting on someone or something: a decision, a review, access,
  a failing check, an external service

## 2. Check the repository

Skip this step if the working directory is not a git repository. Run the
commands in the working directory and in any other repo or worktree the
session changed.

- `git branch --show-current` and `git status --short` for the branch and
  any uncommitted work
- the commits on this branch: find the base with
  `gh pr view --json baseRefName` or `git symbolic-ref refs/remotes/origin/HEAD`,
  then run `git log --oneline <base>..HEAD`
- the open PR for the branch, if `gh` is available:
  `gh pr view --json number,url,state,reviewDecision,mergeable` and
  `gh pr checks`

When the repository and the session disagree, trust the repository and say
so. For example, a commit the session called pushed that isn't on the
remote, or a check the session called green that is now failing.

## 3. Write the update

Use exactly these three headings, in this order:

**Done**
**Next**
**Blockers**

Rules:

- One bullet per item, one or two plain sentences each. Lead with the
  outcome rather than the activity: "Login now rejects expired tokens", not
  "Worked on auth".
- Name concrete things: the PR number and link, the file, the failing check.
- Only list something under Done if it was verified. Work that's written
  but unverified goes under Next, phrased as what's left ("Run the
  integration tests on the retry change").
- Every blocker names what it is waiting on and, where you know it, who can
  unblock it. With no blockers, write "None".
- Uncommitted changes, unpushed commits, failing checks, and review threads
  waiting on a reply always appear, under Next or Blockers.
- Keep the whole update under about 15 bullets. Merge small items rather
  than listing every step.
- No preamble and no sign-off. Start at the first heading.

If `$ARGUMENTS` names an audience or a focus, apply it. For example, "for
slack" means a version ready to paste, with no repo-internal paths. A focus
such as "just the API work" means leaving out the unrelated items.
