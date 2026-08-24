# Auto-Push Documentation Rule

**Purpose:**
Ensure that GitHub is always up to date with the latest architectural and technical documentation. The user relies on GitHub as a continuous sync point for external tools (e.g., ChatGPT).

**Instructions:**
1. Whenever you create, edit, or modify any file in the `docs/` directory, or any other project file, you MUST automatically commit and push the changes to GitHub immediately.
2. Run `git add . && git commit -m "docs: auto-update"` followed by `git push` using the `run_command` tool with `BypassSandbox: true` (since network access is required to push to GitHub).
3. You do not need to ask the user for permission to push; treat it as a mandatory, automatic final step for every documentation task.
