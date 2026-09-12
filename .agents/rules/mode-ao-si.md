---
description: Strict behavioral guardrails for AO (Audit Only) and SI (Start Implementation) modes.
---

# AO / SI Mode Protocol

The user uses two specific keywords to strictly control your ability to make changes: **AO** and **SI**.

## AO (Audit Only) Mode
When the user types `AO` or `Audit Only`:
1. **ENTER AUDIT MODE IMMEDIATELY.**
2. **STRICTLY NO CODE CHANGES:** You are absolutely forbidden from using any tool that modifies files (e.g., `write_to_file`, `replace_file_content`, `multi_replace_file_content`) or running any terminal commands that alter state.
3. **READ-ONLY TOOLS ONLY:** You may only use tools to read files, search directories, query information, or create artifacts. 
4. **NO IMPLEMENTATION:** This is a brainstorming and investigation session. Do not jump to implementation, do not write scripts to fix things, and do not proactively edit code.
5. Remain in Audit Only mode across all subsequent turns until the user explicitly issues the `SI` command.

## SI (Start Implementation) Mode
When the user types `SI` or `Start Implementation`:
1. **EXIT AUDIT MODE.**
2. You are now authorized to make code changes, run modifying terminal commands, and implement the solutions discussed during the AO session.
