# Operational Modes & Control Directives

The assistant must strictly respect the following user control modes and acronym triggers across all interactions:

## 1. CM : Chat Mode
- **Trigger:** `CM` or explicit user request for "Chat Mode".
- **Behavior:** Pure chatbox mode. 
- **Constraints:** 
  - Do NOT make any tool calls (no file viewing, searching, command running, or editing).
  - Respond conversationally based strictly on existing context and conversation history.
  - Remain in Chat Mode until user explicitly switches modes.

## 2. AM / AO : Audit Mode
- **Trigger:** `AM`, `AO`, or explicit request for "Audit Mode" / "Audit only".
- **Behavior:** Read-only inspection and investigation mode.
- **Constraints:**
  - Allowed tools: `view_file`, `grep_search`, `list_dir`, read-only `run_command` (e.g. checking logs, ports, processes).
  - Strictly FORBIDDEN: Writing code, modifying files, creating new files, or making system changes.
  - Provide findings, analysis, and architectural reports only.

## 3. IM / SI : Implementation Mode
- **Trigger:** `IM`, `SI`, or "Start Implementation".
- **Behavior:** Active development, coding, and system execution mode.
- **Capabilities:** Write code, modify files, run development tasks, and implement verified technical solutions.
