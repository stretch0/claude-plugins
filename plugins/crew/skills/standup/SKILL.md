---
name: standup
description: Give a stand-up update for the current session covering the goal, where the work stopped, what changed since, what's done, what's next, and any blockers. Use when the user asks for a stand-up, status update or progress summary, or comes back to the session and asks "where are we?", "where was I?", "catch me up", or says they're back.
argument-hint: "[optional focus or audience, e.g. \"for slack\" or \"just the API work\"]"
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git symbolic-ref:*), Bash(git fetch:*), Bash(git rev-list:*), Bash(gh pr view:*), Bash(gh pr checks:*), Bash(gh pr list:*)
---

Write a short update on the work in this session. It serves two readers:

- **The user, coming back to the session** after a break and needing to
  pick up where they left off. This is the default.
- **A team**, when `$ARGUMENTS` names an audience such as "for slack".

The session is the main source. The repository fills in what has scrolled
out of context, confirms what the session claims, and shows what changed
while the user was away.

This skill only reads. Never commit, push, edit files, or change a PR while
running it. `git fetch` is allowed because it only updates remote-tracking
refs.

## 1. Read the session

Go back through the conversation and collect:

- the goal: what the user asked for, including requests that changed along
  the way
- where the work stopped: the last thing done or attempted, and the state
  it was left in (mid-way through a step, tests red, waiting on a check)
- any question or decision the session put to the user that was never
  answered
- background work that was started, such as a CI watch, a loop, or a
  long-running command, and whether it has reported back
- what was finished, and how you know it's finished (tests passed, PR
  opened, the user confirmed)
- what was started but not finished
- what is waiting on someone or something: a decision, a review, access,
  a failing check, an external service

## 2. Check the repository

Skip this step if the working directory is not a git repository. Run the
commands in the working directory and in any other repo or worktree the
session changed.

- `git branch --show-current` and `git status --short` for the branch and
  any uncommitted work
- the base: `gh pr view --json baseRefName`, else
  `git symbolic-ref --short refs/remotes/origin/HEAD`
- `git fetch origin <base>`, then `git log --oneline origin/<base>..HEAD`
  for this branch's commits and `git rev-list --count HEAD..origin/<base>`
  for how far the base has moved ahead
- `git log -1 --format=%cI` for when the work was last committed
- the open PR for the branch, if `gh` is available:
  `gh pr view --json number,url,state,reviewDecision,mergeable,reviews,comments`
  and `gh pr checks`

**What changed since the user left** is anything that differs from the last
state the session saw, or that is dated after the last commit: checks that
finished, reviews or comments that arrived, the PR merged or closed, the
base moving ahead. If the session never looked at something, report its
current state instead, without calling it new.

When the repository and the session disagree, trust the repository and say
so. For example, a commit the session called pushed that isn't on the
remote, or a check the session called green that is now failing.

## 3. Write the update

For the user (the default), use these four headings, in this order:

**Picking up**
**Done**
**Next**
**Blockers**

**Picking up** is four labelled lines, each one sentence. Leave out a line
that has nothing to say, except Goal:

- **Goal:** what this session is for, with the PR or ticket if there is one
- **You stopped:** the last step and the state it was left in
- **Waiting on you:** each open question or decision, quoted closely enough
  to answer without scrolling back
- **Since you left:** what changed, per step 2

For a team audience (`for slack` and similar), drop Picking up and use only
**Done**, **Next** and **Blockers**, ready to paste, with no repo-internal
paths.

Rules for every section:

- One bullet per item, one or two plain sentences each. Lead with the
  outcome rather than the activity: "Login now rejects expired tokens", not
  "Worked on auth".
- Name concrete things: the PR number and link, the file, the failing check.
- Only list something under Done if it was verified. Work that's written
  but unverified goes under Next, phrased as what's left ("Run the
  integration tests on the retry change").
- The first item under Next is the concrete place to start: a command to
  run, a file to open, or a question to answer.
- Every blocker names what it is waiting on and, where you know it, who can
  unblock it. With no blockers, write "None".
- Uncommitted changes, unpushed commits, failing checks, and review comments
  waiting on a reply always appear, in Picking up, Next or Blockers.
- Keep Done, Next and Blockers under about 15 bullets together. Merge small
  items rather than listing every step.
- No preamble and no sign-off. Start at the first heading.

A focus in `$ARGUMENTS`, such as "just the API work", means leaving out the
unrelated items.
