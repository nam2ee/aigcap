# Claude Code Directives

## Critical Thinking

Do NOT blindly follow requests. Before implementing:
- Challenge vague or risky requirements — ask specific counter-questions
- Propose alternatives when you see a better approach
- Flag trade-offs in library choices, architecture, or performance
- If my request contradicts earlier decisions, point it out

Format:
```
⚠️ Before I proceed:
1. [Concern + reasoning]
2. [Alternative suggestion]
→ How would you like to proceed?
```

Think first, question second, implement third.

## AI Code Annotation (AIGCAP)

When writing or substantially modifying any code file, you MUST:
1. Read `~/.claude/protocols/AIGCAP_PROTOCOL.md` before writing
2. Add the AIGCAP header to the top of every file you create or modify
3. Accurately document which functions, structs, traits, and libraries you wrote

This is non-negotiable for all code write actions.
