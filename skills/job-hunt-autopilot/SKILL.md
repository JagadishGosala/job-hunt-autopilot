---
name: job-hunt-autopilot
description: Find, rank, tailor resumes for and apply to jobs across portals (Naukri, Instahyre, hirist.tech, foundit, LinkedIn, company careers sites) with Claude in Chrome. First run asks for the resume and preferences; form answers are saved to an answer bank and Claude's memory and reused. Use for "apply for jobs", "run my job search", "find jobs and apply", "set up job autopilot", or answering pending application questions.
---

# Job Hunt Autopilot

A job-search pipeline that runs for **whoever installed it**. It finds openings, ranks them honestly against the candidate's real resume, tailors a resume per job without inventing anything, asks the candidate to approve, then applies in their own signed-in Chrome. Every new screening question is asked once, saved, and reused afterwards.

Nothing in this skill is about a specific person. All personal data is collected at setup and lives in the candidate's own **store** (see below). Never copy one candidate's data into another candidate's store.

## Step 0, every run: find the store and load the profile

The **store** is a set of files under the prefix `job-hunt/`. Look for it in this order and use the first that has `job-hunt/settings.json`:

1. **Project docs.** If the Projects tool is available, `project_read` `job-hunt/settings.json`. This is the recommended store, and the only one that works for scheduled runs without the computer.
2. **Memory pointer.** Read the memory file `/areas/job-hunt.md` (inside the Project's memory folder when the session is bound to a Project). Its `store:` line says where the store is.
3. **A connected local folder.** If the `device_*` tools are available, look for `job-hunt/settings.json` in each connected folder.

**If no store is found, this is the first run.** Read `references/setup.md` and run setup before anything else, even if the user asked for something else ("apply for jobs"). Tell them in one line that you need a few details first.

Then load `settings.json`, `master-resume.json` and `answer-bank.json`, and set up the workspace:

`<skill-dir>` below means the folder this SKILL.md is in.

```bash
mkdir -p /home/claude/job-hunt/work
cp <skill-dir>/scripts/*.py /home/claude/job-hunt/
# then write settings.json, master-resume.json, spec-master.json and answer-bank.json from the store into /home/claude/job-hunt/
python3 -c "import playwright" 2>/dev/null || { pip install --break-system-packages playwright && python3 -m playwright install chromium; }
which pdftotext >/dev/null || apt-get install -y poppler-utils
```

All later commands (`python3 resume_tool.py ...`, `python3 scout_filter.py ...`) run from `/home/claude/job-hunt`.

`references/storage-and-memory.md` describes every file in the store, how to read and write each backend, and exactly what goes to memory. Read it before the first write of a run.

## Modes

Pick the mode from the request. If unclear and someone is present, ask; if the run is unattended (a scheduled task), use the mode named in the prompt.

| Mode | Trigger | What happens |
|---|---|---|
| `setup` | First run; "update my job profile/resume/preferences" | `references/setup.md` |
| `discover` | "find jobs", morning scheduled run | Scout → Ranker → Tailor ⇄ Validator. Ends with a numbered shortlist waiting for approval. |
| `approve` | "approve 1, 3, 5", "reject 2", "show my shortlist" | Update job stages from the candidate's reply. |
| `apply` | "apply to approved jobs", evening scheduled run | Applier on approved jobs, within the daily cap per portal. |
| `answer` | The candidate replies with answers to open questions | Save answers (store + memory), then resume those drafts if Chrome is reachable. |
| `full` | "run my job search", "apply for jobs" with someone present | `discover`, then ask for approval in the chat, then `apply`. |
| `status` | "how is my job search going" | Counts per stage and per portal, open questions, last run. |

## The pipeline

The work is split into five roles. Their full instructions are in `references/agents/`:

- **Scout** (`scout.md`): pulls listings, applies the hard filters in code, writes new jobs as `found`.
- **Ranker** (`ranker.md`): triages, researches the company, scores 0–100 against the resume, writes `ranked` or `skipped`.
- **Tailor** (`tailor.md`): builds a tailored resume spec from the master resume only, renders and lints it.
- **Validator** (`validator.md`): an independent review panel that never sees the Tailor's reasoning; pass or fail with fixes.
- **Applier** (`applier.md`): fills and submits approved applications, answers questions from the profile and the answer bank, and freezes anything new as a draft question.

**How to run the roles:**

- If the `Agent` tool is available, run each role as a subagent (`subagent_type: "general-purpose"`, `model: "sonnet"` to keep cost down). Its prompt is: "Read `<skill-dir>/references/agents/<role>.md` and follow it exactly", plus the store location, the workspace path `/home/claude/job-hunt`, and the concrete inputs (job ids, round number, feedback). Run up to 3 Tailor or 3 Validator calls in parallel, in one message.
- The Validator must be a **fresh** agent every round and gets only the job, the rendered resume and the previous `must_fix` list. Never pass it the Tailor's change log.
- Without the `Agent` tool, do the roles yourself one after another. Before each Validator pass, set aside the Tailor's notes and judge only the files.

### Job stages

`reserve` → `found` → `ranked` → `tailoring` ⇄ `validating` → `ready` | `needs_review` → (candidate) `approved` | `rejected` → `applying` → `applied` | `blocked` | `draft_waiting_answer`. `skipped` can happen at any point.

- **Profile-resume portals** (`settings.portals[].resume == "profile"`, typically Naukri, hirist.tech, foundit): the portal already holds the resume. The Ranker's score is the only gate, and these go straight from `ranked` to `ready`.
- **Tailored portals** (Instahyre, company sites, anything that takes an upload) go through the Tailor ⇄ Validator loop:

```
round = 1; feedback = none
loop:
  Tailor(job, round, feedback) -> spec, PDF, text, lint
  if lint fails after the Tailor's own 3 retries -> needs_review; next job
  Validator(job, round, previous must_fix only) -> scorecard
  if verdict == pass -> ready; break
  if round == 3      -> needs_review (notes = top must_fix); break
  feedback = must_fix + should_fix; round += 1
```

### discover

1. Scout. Respect `settings.limits.target_per_portal` and `max_jobs_waiting`.
2. Ranker, in batches of up to 8 `found` jobs.
3. **Top-up:** for each portal below its target, promote `reserve` jobs (best `pool_rank` first) to `found` and rank again. Stop when the target is reached or the reserve is empty.
4. Tailor ⇄ Validator loop for tailored-portal jobs, highest score first.
5. **Present the shortlist** (all `ready` and `needs_review` jobs) as a numbered list: company, title, portal, location, score, one-line fit, main gap, and the link. If someone is present, ask for approval with AskUserQuestion (multi-select, in groups of up to 4) or ask them to reply "approve 1, 3, 5". If unattended, send the list with `SendUserMessage` and say they can reply in that chat or in any chat with this skill ("approve 1, 3, 5").
6. Save the numbered list to `shortlist.json` in the store, so a later "approve 1, 3" maps to the right jobs.
7. Write the run log. Once a week (check the last housekeeping date in `jobs.json`), do the housekeeping in `schemas.md`.

### approve

Map the numbers in the reply to job ids using the last presented shortlist (`shortlist.json` in the store). Set `approved` or `rejected`. The candidate may also approve a `skipped` or `needs_review` job by name; set `approved` with `override: true`. Approving one batch never pre-approves the next.

### apply

Run the Applier (`references/agents/applier.md`) on every `approved` job and every `draft_waiting_answer` job whose questions are now all answered. **Apply only to jobs the candidate approved.** This mode needs Claude in Chrome, so the candidate's computer must be on with Chrome open. If Chrome isn't reachable, say so and stop. Don't mark anything as failed. Uploading a tailored resume also needs `settings.output_folder`: Chrome can only upload files that are on the candidate's computer.

At the end, present every open question in one numbered message: company, role, the exact question, field type and options, and character limit. The candidate can answer by replying.

### answer

For each answer the candidate gives:

1. Add it to `answer-bank.json` in their exact words (schema in `references/schemas.md`). Mark it `reusable: true` unless they say it is for that one company.
2. Mirror it to memory as described in `references/storage-and-memory.md`, if they allowed memory at setup.
3. Mark the matching question `answered`.

Then, if Chrome is reachable, resume those drafts with the Applier. Otherwise the next apply run picks them up.

## Rules that always hold

- **Honesty.** A resume may select, reorder, shorten and echo the JD's wording for what the master resume already says. It never adds a skill, number, scope or responsibility. A form answer comes from the profile, the master resume or the candidate's own saved answers. Anything else is frozen as a question, never guessed.
- **Never answer "No"** to a preference question on the candidate's behalf unless they have given that answer before.
- **Never** enter passwords, OTPs or security codes, create accounts on external applicant systems, solve CAPTCHAs, or grant OAuth/SSO consent. Leave the tab filled, mark the job `blocked` with the exact action needed, and move on.
- **Consents:** tick only the kinds of consent listed in `settings.consents.auto_accept`. Ask about anything else.
- **Human pace:** wait 60–120 s between submissions. On any "unusual activity" or bot check, stop that portal for the day and tell the candidate.
- **Excluded employers** (`settings.excluded_employers`) are dropped at every stage.
- **Secrets:** never store passwords, OTPs, tokens or ID numbers anywhere, in the store or in memory.
- Keep your own messages short. End every run with a 3-line summary: found / ranked / ready / needs review / applied / drafted / blocked.

## Scheduling

To run it on a schedule (for example, discover at 9 AM and apply at 7 PM on weekdays), see `references/scheduling.md`. Setup offers this at the end.
