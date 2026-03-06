---
name: learn-from-chat
description: Extract 1-2 memorable lessons from the current conversation and format them as compact TIL (Today I Learned) notes with a daily spaced-repetition quiz reminder. Use when the user asks "what should I remember from this chat", "extract lessons", "generate my daily review", "what did I learn today", "summarize learnings", or finishes a technical conversation wanting to retain knowledge without re-asking AI next time.
---

# Learn From Chat — Convert AI Conversations to Retained Knowledge

## Purpose

Help the user break the loop of over-relying on AI by surfacing 1-2 re-askable lessons as TIL cards, then scheduling a daily spaced-repetition quiz via the `cron` tool.

---

## Instructions

### Step 1: Scan for "re-askable" moments

Analyze the **current conversation** (already in context). Look for where the user didn't know something they should own:

- Commands, flags, or syntax they had to ask about
- Conceptual clarifications ("what is X", "why does Y")
- Debugging steps that revealed a knowledge gap
- Config or boilerplate they had to look up

**Exclude**: deep architecture decisions, one-off project-specific logic, things they clearly already knew.

If nothing qualifies, say so honestly: *"This was an architecture discussion — nothing here needs memorizing. The value was in the reasoning."* Stop here.

---

### Step 2: Pick the 1-2 best lessons

Prefer lessons that are **concrete**, **generalizable**, **ownable**, and **high-recurrence** (likely to come up in future sessions). Hard limit: 2 lessons max.

---

### Step 3: Format as TIL Cards

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 LESSON [N]: [Short Title — 5 words max]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 What to remember:
[1-2 sentences. The actual knowledge. No fluff.]

💻 Example / Command:
[Code snippet, command, or concrete example]

🧠 Memory hook:
[One sentence mnemonic or "why it works this way"]

🔁 Next time, try it yourself:
[The exact thing to attempt before asking AI again]
```

---

### Step 4: Schedule the Daily Quiz via Cron

Use the `cron` tool to schedule a daily spaced-repetition quiz at 9 AM.

**Always use `type='task'`** — this gives the job an isolated thread with no conversation history, so all lesson data must be embedded directly in the message.

Write the `message` as a self-contained instruction to yourself (the agent at fire time), not as text for the user. Keep it short and executable per the cron tool guidelines.

```python
cron(
    action="add",
    type="task",
    cron_expr="0 9 * * *",
    message="""Run a spaced-repetition quiz on these TIL lessons:

LESSON 1: [TITLE]
Knowledge: [WHAT TO REMEMBER — 1-2 sentences]
Example: [CODE OR COMMAND]
Hook: [MNEMONIC]

[LESSON 2 — same format, if applicable]

Steps:
1. Greet briefly: "Good morning! Time for your daily TIL quiz."
2. For each lesson, ask one specific recall question. Do NOT show the answer yet.
   Good: "Write the exact command to kill the process on port 3000."
   Bad: "Do you remember the lsof lesson?"
3. Wait for their response.
4. Score: correct / close / missed — then reveal the answer with the memory hook.
5. If they score 100% two days in a row: "You've got this — type 'cancel my TIL reminder' when confident."
"""
)
```

Key rules for the cron `message`:
- Embed lesson content as **raw data**, not as formatted TIL cards — the agent formats output at fire time
- Must be **self-contained** — the agent has no memory of this conversation when it fires
- **Recall before reveal** — this is what makes it spaced repetition, not just re-reading
- Questions must be **specific and answerable** (exact commands, not vague recall prompts)

After scheduling, confirm to the user:
*"✅ Daily quiz set for 9:00 AM. It'll ask you to recall from scratch — not just re-show the answer. Type 'cancel my TIL reminder' once you've nailed it two days in a row."*

---

## Output Rules

- **Max 2 lessons** — intentional hard limit
- **Be specific** — "`lsof -ti:PORT | xargs kill -9`" not "use lsof to find processes"
- **Memory hook is mandatory** — the part that makes it stick without re-asking
- **Always schedule the cron** — don't ask permission, just do it and report the result

---

### Closing Line

```
📅 Reminder: [TOMORROW'S DATE] at 9:00 AM ✅
💡 [1 sentence on the common pattern across lessons, if any]
```

---

## Example Output

```
📚 Today's Lessons — 2026-03-06

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 LESSON 1: Kill process on a port
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 What to remember:
Use lsof to find the PID listening on a port, then pipe it to kill.

💻 Example / Command:
lsof -ti:3000 | xargs kill -9
# -t = terse (PIDs only)  -i:PORT = filter by port

🧠 Memory hook:
"lsof = list open files. In Unix, network ports ARE files."

🔁 Next time, try it yourself:
Before asking AI, just type: lsof -ti:[PORT] | xargs kill -9

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Reminder: 2026-03-07 at 9:00 AM ✅
💡 Pattern: "type it weekly, own it forever" — CLI muscle memory beats lookup.
```
