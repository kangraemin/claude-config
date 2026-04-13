---
name: readme-craft
description: Create or rewrite README.md files that look like they belong to a 50k-star repo. Use this skill whenever the user wants to write a README, improve a README, make documentation more readable, or mentions anything about README quality, project documentation landing pages, or GitHub project presentation. Also trigger when the user says their README is too long, hard to read, or looks amateur.
---

# README Craft

Write READMEs that read like a landing page, not a manual.

This skill is built on patterns extracted from 12 of GitHub's most-starred repos (React, Vue, Next.js, Supabase, Tailwind, Deno, uv, Ollama, shadcn/ui, Bootstrap, VS Code, PocketBase). The goal: someone landing on the repo for the first time should understand what the project does in 10 seconds, and know how to install it in 30.

## Core Philosophy

The README is a **landing page**, not documentation. It answers exactly five questions:

1. What is this?
2. What does it look like?
3. How do I install it?
4. Where do I learn more?
5. How do I contribute?

Everything else belongs in `/docs`, a wiki, or a docs site. If a section doesn't answer one of these five questions, it probably doesn't belong in the README.

## Structure

Follow this order. Skip sections that don't apply, but never reorder.

```
[Hero Block]
  centered logo (dark/light variants if available)
  project name as H1
  one-sentence tagline (under 15 words)
  badge row

[Screenshot or GIF — optional but powerful]

[What It Does — only if the tagline isn't enough]
  3-5 bullet points, each one sentence

[Quick Start / Installation]
  platform-specific one-liners

[Usage — optional]
  ONE code example, under 10 lines

[Documentation link]

[Community links]

[Contributing link]

[License — one line]
```

## Writing Rules

These rules exist because readers scan, they don't read. Every decision below optimizes for scannability.

### Sentence length
- Cap at 20 words per sentence. If it's longer, split it.
- One idea per sentence. Never chain with "and" or "which".

### Paragraphs
- Maximum 2-3 sentences before a visual break (bullet list, code block, heading, or blank line).
- If you're writing a 4th sentence in a row, stop — convert to bullets.

### Bullet points
- Start each bullet with a **bold key phrase**, then a short explanation.
- **Good:** `**Hot reload** — see changes instantly without restarting`
- **Bad:** `This tool supports hot reload which means you can see changes instantly without having to restart the development server`

### Headings
- Use `##` for main sections. `###` sparingly for subsections.
- Heading text should be 2-4 words. Not sentences.
- No heading should be followed by another heading — always put content between them.

### Tables over prose
- When comparing 3+ items with 2+ attributes, use a table.
- Feature lists, platform support, command references — all tables.

### Code blocks
- Always specify the language for syntax highlighting.
- Show the shortest possible working example.
- If a command produces output, show the output too.
- Never exceed 10 lines in a single code block.

### Links over content
- Don't explain what the docs site covers. Just link to it.
- **Good:** `See the [documentation](https://docs.example.com) for guides and API reference.`
- **Bad:** `Our documentation site contains comprehensive guides covering installation, configuration, deployment, API reference, and troubleshooting.`

## Hero Block Template

```markdown
<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
  <img src="assets/logo-light.svg" width="200" alt="Project Name">
</picture>

# Project Name

**One-sentence tagline that explains what this does.**

[![License](badge-url)](link) [![Version](badge-url)](link) [![CI](badge-url)](link)

</div>
```

If no dark/light logo variants exist, use a simple `<img>` tag. If no logo exists at all, skip straight to the H1 + tagline + badges.

## Anti-Patterns

Avoid these — they make READMEs feel amateur or overwhelming:

- **Wall of text** — any section longer than 5 lines without a visual break
- **Table of Contents for short READMEs** — if the README is under 100 lines, a TOC adds clutter
- **Changelogs in README** — belongs in CHANGELOG.md
- **Listing every feature** — pick the top 3-5, link to docs for the rest
- **Tutorial-style content** — "First, do X. Then, do Y. Next..." belongs in docs
- **Exclamation marks** — confident projects don't shout
- **Emoji overload** — zero or minimal. Badges provide the color.
- **"Why use this?"** section that's longer than the install section

## Rewriting Existing READMEs

When improving an existing README rather than creating from scratch:

1. Read the current README fully
2. Identify which content answers the 5 core questions
3. Move everything else to a `docs/` suggestion or cut it
4. Restructure remaining content into the standard order above
5. Rewrite every paragraph into bullet points or short sentences
6. Present before/after line counts — a good rewrite usually cuts 40-60%

Preserve the project's unique voice and any specialized sections that genuinely belong (e.g., a security notice for a crypto project, or a compatibility matrix for a cross-platform tool). Don't strip personality — strip verbosity.

## Checklist

Before finishing, verify:

- [ ] Tagline is under 15 words
- [ ] No paragraph exceeds 3 sentences
- [ ] Every bullet starts with a bold key phrase
- [ ] Code examples are under 10 lines each
- [ ] Total README is under 150 lines (aim for 50-100)
- [ ] Every section either answers a core question or provides a link
- [ ] No wall of text anywhere
