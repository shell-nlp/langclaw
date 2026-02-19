---
name: "summarize"
description: "Use this skill when the user asks you to summarize, condense, or give key points from a piece of text, document, URL, or conversation."
---

# Summarize Skill

## Purpose

Produce clear, accurate summaries of any content the user provides or points to.

## When to Use

- User says "summarize", "TL;DR", "give me the key points", "condense this"
- User pastes a long article, document, or code block and wants a digest
- User wants a recap of the current conversation

## Process

1. Identify the content to summarise (pasted text, URL, or conversation)
2. If a URL is given, use the web-search or fetch tool to retrieve the page content
3. Extract the main ideas, key facts, and conclusions
4. Present the summary as:
   - A one-sentence headline
   - 3–7 bullet points covering the main points
   - (Optional) a "Why it matters" sentence if context adds value

## Notes

- Match the summary length to the complexity of the source material
- Preserve technical accuracy — do not simplify to the point of being wrong
- If the content is too long to process in one pass, summarise in sections
