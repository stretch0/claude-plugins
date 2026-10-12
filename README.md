# claude-plugins

[Claude Code](https://claude.com/claude-code) plugins by stretch0.

```
/plugin marketplace add stretch0/claude-plugins
/plugin install crew@stretch0
```

| Plugin | What it does |
| --- | --- |
| [crew](plugins/crew/README.md) | `/crew:review` runs an adversarial find-then-refute code review. `/crew:babysit` and the PR-watching hooks keep Claude on the hook for CI and review threads on the PRs it pushes. `/crew:status` shows whether the session's PRs are ready to merge, and `/crew:open` opens them in the browser. `/crew:standup` catches you up on a session after a break, or gives your team a Done / Next / Blockers update. |

Plugins install at user scope by default, so they apply to every project you open and nobody else is affected. Pick project scope during install to share a plugin with everyone on a repo.

Pull the latest version with `/plugin marketplace update stretch0`, then start a new session.

## License

MIT
