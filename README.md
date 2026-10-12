# claude-plugins

[Claude Code](https://claude.com/claude-code) plugins by stretch0.

Add the marketplace once:

```
/plugin marketplace add stretch0/claude-plugins
```

Then install whichever plugins you want:

| Plugin | What it does | Install |
| --- | --- | --- |
| [pr-watch](plugins/pr-watch/README.md) | Keeps Claude responsible for the PRs it pushes. Reports CI, conflict and review-thread status after every push, won't let the session end while a PR is red or has unanswered review threads, and adds `/pr-watch:babysit-pr` to fix CI and work through review comments. | `/plugin install pr-watch@stretch0` |
| [stand-up](plugins/stand-up/README.md) | `/stand-up:stand-up` gives a Done / Next / Blockers update for the current session, checked against the repo's git and PR state. | `/plugin install stand-up@stretch0` |

Plugins install at user scope by default, so they apply to every project you open and nobody else is affected. Pick project scope during install to share a plugin with everyone on a repo.

Pull the latest versions with `/plugin marketplace update stretch0`, then start a new session.

## License

MIT
