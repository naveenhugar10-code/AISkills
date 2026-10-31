---
name: create-skill
description: Scaffold a new Claude Code skill in this repo. Use when the user runs /create-skill or asks to create, add, or scaffold a new skill (a SKILL.md with frontmatter, instructions, and optional supporting files).
argument-hint: "[skill-name] [short description of what it should do]"
---

# Create a new skill

Create a new skill under `.claude/skills/<skill-name>/` in this repository.

Arguments passed by the user: `$ARGUMENTS`

## 1. Gather requirements

From the arguments and conversation, work out:

- **Name** — lowercase, hyphen-separated, max 64 chars (e.g. `review-sql`). It becomes the `/name` slash command.
- **Purpose** — what the skill does and the concrete outcome it produces.
- **Trigger** — when Claude should use it (phrases, file types, situations).
- **Inputs** — whether it takes arguments (`$ARGUMENTS`, or `$0`, `$1` for positional ones).
- **Supporting files** — scripts, templates, or reference docs it needs.

Ask the user only for what you cannot reasonably infer. If the name is missing, propose one.

Check that `.claude/skills/<skill-name>/` does not already exist. If it does, ask whether to update it instead.

## 2. Write `SKILL.md`

Create `.claude/skills/<skill-name>/SKILL.md` with this structure:

```markdown
---
name: <skill-name>
description: <What it does, then "Use when ..." with concrete triggers. One or two sentences, third person.>
argument-hint: "[optional hint shown in autocomplete]"   # omit if no arguments
allowed-tools: Read, Grep, Glob                           # optional: tools pre-approved while the skill runs
disable-model-invocation: true                            # optional: only run when the user types /<skill-name>
---

# <Title>

<One-paragraph overview of the goal.>

## Steps

1. ...
2. ...

## Output

<What the result should look like.>
```

Guidelines:

- **The description is the trigger.** Claude decides when to load a skill from its `description`, so state both *what* it does and *when* to use it, with keywords a user would actually say.
- **Be concise.** Write instructions for a capable model; skip what Claude already knows. Keep `SKILL.md` under ~500 lines.
- **Be concrete.** Prefer numbered steps, exact commands, file paths, and an example of the expected output.
- **Progressive disclosure.** Put long reference material in separate files (e.g. `reference.md`, `templates/`, `scripts/`) and link to them from `SKILL.md` by relative path so they are read only when needed.
- **Scripts over prose** for deterministic work: add a script in `scripts/` and tell Claude to run it.
- Use `disable-model-invocation: true` for skills with side effects (deploys, commits, sending messages) so they only run when explicitly invoked.
- Only set `allowed-tools` when the skill clearly needs a fixed tool set.

## 3. Add supporting files (if any)

```
.claude/skills/<skill-name>/
├── SKILL.md          # required
├── reference.md      # optional detailed docs
├── templates/        # optional templates
└── scripts/          # optional helper scripts (make executable)
```

## 4. Validate

- Frontmatter is valid YAML between `---` lines, and `name` matches the directory name.
- `description` is specific and includes "Use when ...".
- Every file referenced from `SKILL.md` exists.
- Scripts are executable (`chmod +x`) and run.

## 5. Report

Tell the user the skill's path, how to invoke it (`/<skill-name> ...`), and a one-line summary of what it does. Mention that a new skill directory may need a session restart to appear if it is not picked up immediately.
