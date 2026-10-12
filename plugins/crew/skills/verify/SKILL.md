---
name: verify
description: Visually verify that the changes on this branch work and match their acceptance criteria and designs. Starts the app if needed, drives a browser (the user's connected Chrome first, so existing sign-ins are reused), checks each criterion, and reports a pass or needs-work verdict with evidence.
argument-hint: "[PR number | what to focus on]  (blank = this branch's changes)"
disable-model-invocation: true
allowed-tools: Bash(bash ${CLAUDE_SKILL_DIR}/copy-env.sh:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(git symbolic-ref:*), Bash(git worktree list:*), Bash(gh pr view:*)
---

Check, in a real browser, that the change does what it was meant to do and
looks the way it was meant to look. Work in four stages: **understand,
start, verify, report**. Don't fix anything while verifying. Report what you
found, and let the user decide what to change.

## 1. Understand the change

Build a picture of what should now be true, from every source available:

- **The diff.** Find the base (the open PR's `baseRefName`, else
  `origin/HEAD`) and read `git diff $(git merge-base <base> HEAD)`, plus
  `git status` for uncommitted work. If `$ARGUMENTS` is a PR number, use that
  PR's diff and description instead.
- **Acceptance criteria (ACs).** Look in the conversation first, then in the
  PR description, any ticket or issue it links, and plan or spec files in the
  repo that mention this branch or feature. Use the ACs word for word. If
  there are none, derive the expected behaviour from the diff and the
  conversation, and say in the report that you did.
- **Designs.** Images or files shared in the conversation, design links in
  the PR or ticket, and mockups or screenshots committed with the change. If
  a design is referenced but you can't see it, ask the user for it before
  judging the visuals, rather than guessing.
- **Project guidance.** `CLAUDE.md`, `AGENTS.md`, `README`, and any docs on
  running or testing the app.

Turn this into a checklist. Each item names an AC (or a design point), where
to see it (a page or route), what to do (click, type, submit), and what you
expect to see. Include at least one check that existing behaviour next to
the change still works.

If nothing in the change is visible in a browser (a backend-only or
library change), say so. Then verify it the closest way the project allows,
such as calling the endpoint or running the command, or stop and tell the
user that a browser check doesn't apply.

## 2. Start the app

First check whether it's already running: try the expected local URL. If it
responds with this branch's code, use it.

Otherwise work out how to start it, in this order: a project skill or
command for running the app, `CLAUDE.md` and other agent docs, the README,
then `package.json` scripts, a `Makefile`, `docker-compose` files or
`Procfile`s. Start long-running servers as background tasks so the session
stays free, then wait until the URL responds.

**Env files in a worktree.** Env files are git-ignored, so a git worktree
starts without them, and copying them directly is blocked. Use the bundled
script, which copies them from the main checkout into this worktree:

```
bash ${CLAUDE_SKILL_DIR}/copy-env.sh .                 # root .env files
bash ${CLAUDE_SKILL_DIR}/copy-env.sh apps/web apps/api # nested ones
bash ${CLAUDE_SKILL_DIR}/copy-env.sh apps/web/.env.dev # one file
```

Pass the directory or file relative to the repo root; `.` means the root.
It copies `.env` and `.env.*` (skipping `.example`, `.sample` and
`.template` files), keeps files already in the worktree unless you add
`--overwrite`, and prints file names only. Never print, read out, or quote
the contents of an env file.

If the app won't start after a couple of attempts, stop and report what you
tried and the error, rather than reworking the project's setup.

## 3. Verify in a browser

Pick the browser in this order, and say in the report which one you used:

1. **The user's connected Chrome** (`mcp__claude-in-chrome__*` tools). This
   is the preferred option, because it reuses the user's existing sign-ins.
   Load its tools, check the open tabs, and work in a new tab. Never take
   over a tab the user is using.
2. **The built-in browser** (`mcp__Claude_Browser__*`), if the session has
   one.
3. **A dev browser**, such as the Playwright MCP tools (`mcp__playwright__*`)
   or a `dev-browser` CLI if one is installed. Use it when nothing above is
   available.

If tools are deferred, load them with one ToolSearch call before use.

**Signing in.** If the app needs a sign-in the browser doesn't already
have, check the project docs for a development sign-in or bypass. Otherwise,
ask the user to sign in in that browser and tell you when they're done.
Never type real credentials yourself, and never read them from env files.

For each checklist item:

- Go to the page, do the action, and take a screenshot. Look at every
  screenshot you take to confirm it rendered: not blank, not an error
  screen, not a loading spinner.
- Compare it with the AC, and with the design where there is one: layout,
  copy, spacing, colour, and states such as empty, loading, error and
  disabled. Note concrete differences ("the button is left-aligned; the
  design has it right-aligned"), not impressions.
- Check the browser console for errors and the network log for failed
  requests during the flow.
- For a multi-step flow in the connected Chrome, record a GIF with a
  meaningful file name when that's useful evidence.

Avoid anything destructive or outward-facing during checks: deleting real
data, sending emails or messages, making payments. If an AC can only be
proved that way, mark it as not verified and say why.

## 4. Report

Start with the verdict line: **Pass** (every AC verified, no major design
differences, no console errors in the flows) or **Needs work**. Then:

| AC or design point | How it was checked | Result | Evidence |
| --- | --- | --- | --- |

Use one row per checklist item. Result is pass, fail, or not verified (with
the reason). Evidence is the screenshot or GIF name and what it shows.

After the table, list:

- **Design differences**, most visible first
- **Console errors and failed requests**, with the page they appeared on
- **What wasn't verified**, and what would be needed to verify it
- **How the app was run**: the browser used, the URL, the command, and
  whether it's still running and how to stop it. Leave anything you started
  running unless the user asks you to stop it, because they may want to look
  for themselves.
