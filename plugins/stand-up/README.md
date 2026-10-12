# stand-up

A [Claude Code](https://claude.com/claude-code) plugin that gives a stand-up update for the session you're in.

```
/stand-up:stand-up
/stand-up:stand-up for slack
/stand-up:stand-up just the API work
```

The update has three sections: **Done**, **Next** and **Blockers**.

Claude builds it mainly from the conversation. It also reads the git state of the repos the session touched: the current branch, uncommitted changes, commits not yet on the base branch, and the open PR with its checks. Those reads catch work that has scrolled out of context and correct the session's own claims. If the session says a check passed but it's now failing, the update says so.

The command only reads. It never commits, pushes or edits anything, and the read-only `git` and `gh` commands it uses are pre-approved, so it runs without permission prompts.

Only verified work is listed as done. Work that's written but unchecked goes under Next, and every blocker says what it's waiting on.

You can also just ask "where are we?" or "give me a stand-up", and Claude will use the skill.

## Install

```
/plugin marketplace add stretch0/claude-plugins
/plugin install stand-up@stretch0
```

## Requirements

`git` for the repository checks, and the [GitHub CLI](https://cli.github.com/) (`gh`) for PR status. Without either, the update comes from the conversation alone.
