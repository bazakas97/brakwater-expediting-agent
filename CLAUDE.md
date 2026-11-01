# Rules for this project

## Every session
- Read PROJECT_BRIEF.md at the start of every session.

## How we work
- I am learning. Work in small steps and stop after each step.
- Before writing code, explain the plan in 3-5 lines and wait for my OK.
- After every change, explain in plain English what you changed and why, file by file.
- One feature per step. Prefer simple, readable code over clever code.
- Reuse the existing code in the kit (keelson_client, expediting, export) before writing new code.
- No framework unless I ask. We will add LangGraph later, on purpose.

## LLM vs code
- The LLM only does language work (read memos, classify, draft).
- Anything exact (dates, flags, who receives an email, money) is plain, tested code.

## Safety
- Keys only from environment variables. Never read, print or write keys or .env files.
- Never send emails or write to the ERP. The system only suggests, a human approves.
