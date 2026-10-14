---
name: verify
description: QA the changes on this branch against their ticket. Fetches the acceptance criteria from the ticket and the designs it links (saying plainly when a design can't be reached), traces each requirement to the code, starts the app if needed, tests it in a browser (the user's connected Chrome first, so existing sign-ins are reused), and reports a pass or needs-work verdict with evidence.
argument-hint: "[ticket key | PR number | what to focus on]  (blank = this branch's changes)"
disable-model-invocation: true
allowed-tools: Bash(bash ${CLAUDE_SKILL_DIR}/copy-env.sh:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git merge-base:*), Bash(git rev-parse:*), Bash(git symbolic-ref:*), Bash(git worktree list:*), Bash(git branch:*), Bash(gh pr view:*), Bash(gh issue view:*)
---

Act as the QA engineer on this change. Your job is to find out whether it
does what the ticket asked for and looks the way the designs show, not to
confirm that it works. Work in five stages: **gather, trace, start, test,
report**.

Don't fix anything, and don't edit or comment on the ticket, the PR or the
designs. Report what you found and let the user decide what to change.

## 1. Gather the requirements

Collect every source, and keep a record of what you tried and what happened
for each one. The report starts with that record.

**Find the ticket.** Use `$ARGUMENTS` if it names a ticket key or issue. Otherwise
look for a key such as `ABC-123` or `#123` in the conversation, the branch
name, the PR title and description (`gh pr view`), and the commit messages
since the base.

**Fetch it** with whichever tracker is connected: Jira or Confluence
through Atlassian tools, Linear tools, or `gh issue view` for GitHub issues.
If the tools are deferred, load them with ToolSearch first. Read the
description, the acceptance criteria, the comments (decisions often land
there and override the description), sub-tasks, and linked tickets or spec
pages. Use the ACs word for word. If the tracker isn't connected, or the
connection needs authorising, say so in the report rather than working
around it.

**Find the designs:** links in the ticket, its comments, linked pages, the
PR description and the conversation, plus images attached to the ticket or
shared in the session. For each design:

- **Figma.** Use connected Figma tools if there are any. A `node-id` in the
  link points at a specific frame, so fetch that frame. A link without one
  points at the whole file, so look for the frame that matches this
  feature by its page and frame names. If you can't tell which frame is
  the right one, don't guess. Say so, list the candidates you found, and
  ask the user to point at one.
- **Images and attachments.** Download and look at them where the tools
  allow it.
- **Anything you can't open** (no Figma connection, no access, a dead link,
  a prototype that needs signing in): record it as unreachable, with the
  link and the reason.

When the designs can't be reached, still test the behaviour against the
ACs, but don't claim anything matches a design you haven't seen. Never use
the current UI as a stand-in for the design.

**Also read:** the diff (`git diff $(git merge-base <base> HEAD)` with the
base from the PR, else `origin/HEAD`, plus `git status` for uncommitted
work) and project guidance (`CLAUDE.md`, `AGENTS.md`, the README, docs on
running the app).

If there is no ticket at all, derive the requirements from the PR and the
conversation, and put that at the top of the report: without a ticket,
you can't tell whether the change does what the business asked for.

## 2. Trace requirements to the code

Before opening a browser, check the diff against the requirements in both
directions:

- **Every AC**: find the code that implements it. An AC with no matching
  change is likely missing. Note it now, and confirm it in the browser.
- **Every change in the diff**: find the AC it serves. Behaviour that no AC
  or design asks for is scope creep, or a requirement nobody wrote down.
  Report it either way.
- **Ambiguous or contradictory ACs**, or an AC that conflicts with the
  design: list them as questions for whoever owns the ticket, and say which
  reading you tested against.

Then write the test checklist. Each item names the AC or design point, the
page, the steps, and the expected result. As a QA engineer would, cover:

- the happy path for each AC
- the edge and failure cases each AC implies: empty, too long, invalid
  input, no permission, error from the server
- the states the design shows: empty, loading, error, disabled, hover
- other screen sizes, if the design has them or the page is responsive
- one regression check on the existing behaviour next to the change

If nothing in the change is visible in a browser, say so, and test it the
closest way the project allows, for example by calling the endpoint or
running the command.

## 3. Start the app

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

## 4. Test in a browser

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

- Go to the page, follow the steps, and take a screenshot. Look at every
  screenshot you take to confirm it rendered: not blank, not an error
  screen, not a loading spinner.
- Compare the result with the AC. Where you have the design, put the
  screenshot next to it and compare layout, copy, spacing, colour, icons
  and states. Note concrete differences ("the button is left-aligned; the
  design has it right-aligned"), not impressions. Treat copy differences as
  real differences: the design's wording is usually what was agreed.
- Check the browser console for errors and the network log for failed
  requests during the flow.
- For a multi-step flow in the connected Chrome, record a GIF with a
  meaningful file name when that's useful evidence.

Avoid anything destructive or outward-facing during tests: deleting real
data, sending emails or messages, making payments. If an AC can only be
proved that way, mark it as not tested and say why.

## 5. Report

Open with the **verdict** in one sentence, then the **Sources**, one line
each, so the user knows what the verdict rests on:

- **Ticket:** the key and link, and how many ACs it had, or why it couldn't
  be read
- **Designs:** each link and its status: compared (name the frame),
  unreachable (with the reason), or the right section couldn't be found
  (list the candidates)
- **Other:** spec pages, comments with decisions, the PR description

The verdict is one of:

- **Pass**: every AC met, no meaningful design differences, and no console
  errors in the flows.
- **Needs work**: any AC failed or is missing, there's a visible design
  difference, or there are errors.
- **Incomplete**: something essential couldn't be reached or tested, such
  as the ticket, the designs, or the app itself. Say what's needed to
  finish.

A pass on behaviour with unreachable designs is **Incomplete**, not Pass.
When something failed and something else couldn't be reached, the verdict
is **Needs work**, and the same sentence says what is still unchecked.

Then the results table, one row per checklist item:

| Requirement | Steps | Result | Evidence |
| --- | --- | --- | --- |

Result is pass, fail, or not tested (with the reason). Evidence is the
screenshot or GIF name and what it shows.

After the table:

- **Design differences**, most visible first
- **Requirements gaps**: ACs with no implementation, and changes no AC asked
  for
- **Questions for the ticket owner**: ambiguous or conflicting ACs, and
  which reading you tested
- **Console errors and failed requests**, with the page they appeared on
- **How the app was run**: the browser used, the URL, the command, and
  whether it's still running and how to stop it. Leave anything you started
  running unless the user asks you to stop it, because they may want to look
  for themselves.
