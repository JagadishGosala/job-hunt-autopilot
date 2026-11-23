# First-run setup

Goal: turn the candidate's resume and a few answers into four files in their store: `settings.json`, `master-resume.json`, `answer-bank.json` and `jobs.json`. After setup, every later run works without asking these again.

Run setup on the first run, and again when the candidate asks to update their resume or preferences (then only change what they mention).

## 0. Reuse what you already know

Before asking anything, check what's already known about the candidate: the memory file `areas/job-hunt.md`, other memory about their job, role and location, and anything they said earlier in this conversation. Pre-fill those answers and ask the candidate to **confirm** them rather than retype them. Never assume a pre-filled answer is current without confirmation.

## 1. Get the resume (required)

Ask the candidate to attach their resume (PDF or DOCX) in the chat. If they have a LinkedIn PDF export or a longer CV, ask for that too: more source material means better tailoring.

Read the file. Then build `master-resume.json` exactly in the shape of `templates/master-resume.example.json`:

- **Transcribe; don't improve.** Copy each bullet as a `fact` with a short `id` (for example `acme-latency`) and the original wording. Keep every number exactly as written. Don't merge, embellish or invent.
- Group facts under each employer, in reverse-chronological order, and add each project as a project.
- `skills`: grouped as on the resume. Add a skill only if the resume names it.
- `title_lines`: 2–4 headline titles the candidate could honestly use, built from their real titles and target roles. Confirm them with the candidate.
- `summary_master`: their resume summary, verbatim. If they have none, write 2–3 lines made only of facts in the file and ask them to approve it.
- `essence_fact_ids`: the 3–4 facts that are the core of their story. Propose them and let the candidate confirm.
- `common_jd_asks_not_in_resume` and `gap_patterns`: leave empty. The Ranker and Validator add to them as real gaps show up (ask the candidate before adding).
- `screening_years`: leave empty. It fills from their answers.

Show the candidate a short summary: employers, number of facts, skills, and the title lines. Ask them to correct anything wrong before saving.

## 2. Ask for preferences

Use AskUserQuestion for anything with discrete options. Ask open questions in plain text, a few at a time, and don't interrogate. Defaults are in brackets; offer them.

**Target**
- Target roles or titles (for example "backend engineer, full-stack engineer, tech lead").
- Years of total experience. Confirm what the resume implies.
- Locations: cities they'll work in, and remote / hybrid / onsite. Ask about any cities to rule out.
- Title words to avoid (for example "intern, QA, manager") and stacks they don't want (for example "Java-only, .NET").

**Compensation and availability.** These answer the most common screening questions; the candidate may skip any.
- Current and expected compensation, with currency and unit (for example "15 LPA", "USD 120k").
- Notice period, earliest joining date, and last working day if serving notice.
- Work authorisation or visa status, only if their target market asks for it.

**Standing answers to common questions**
- Willing to relocate? Available for in-person interviews? Shift or travel flexibility? [ask; never assume Yes]
- Links to include: LinkedIn, GitHub, portfolio.

**Where and how**
- Portals, from: Naukri, Instahyre, hirist.tech, foundit, LinkedIn, Wellfound, Cutshort, company careers sites, and others. For each portal, ask whether it should use the resume already on their portal profile (`profile`) or a tailored upload (`tailored`). Defaults: `profile` for Naukri, hirist.tech and foundit; `tailored` for the rest.
- Excluded employers: always their current employer; ask about others.
- Jobs to prepare per portal per run [10], and the daily application cap per portal [10].
- Consents they pre-approve on forms [privacy-notice receipt; "materials are my own work"]. Demographic questions default to "prefer not to say".
- Tracker: a Google Sheet URL to log to, "create one", or "none" [none].
- A folder on their computer for resumes and run logs (needs the Claude desktop app) [none].
- **Memory:** "Should I also save your application answers to Claude's memory, so any chat can reuse them?" [Yes]

## 3. Choose the store

1. **Project docs** if the session is in a claude.ai Project and the Projects tool is available. Recommend this; scheduled runs need it.
2. Otherwise, **a connected folder** on their computer (`<folder>/job-hunt/`).
3. Otherwise, warn that the files will only last for this session. Suggest creating a Project, adding this skill, and running setup there.

## 4. Check the tools

Check these once and tell the candidate plainly what's missing. Don't stop setup for an optional one.

- **Claude in Chrome** (needed to apply): load the tools and call `tabs_context_mcp`. Ask them to sign in to each portal in Chrome.
- **Apify connector** (recommended for searching job boards cheaply; it bills the candidate's Apify account): `SearchMcpRegistry` for "apify". If it's missing, offer it with `SuggestConnectors`. Without Apify, the Scout searches in the browser instead, which is slower.
- **Google Sheets** (only if they want a tracker).
- **Desktop app folder** (only if they want local files).

## 5. Save

1. Write `settings.json` in the shape of `templates/settings.example.json`, the `master-resume.json` you built, `answer-bank.json` (copy `templates/answer-bank.empty.json`, then add each standing answer from step 2 as an entry with `answered_by: "candidate"`), and `jobs.json` as `{"jobs": {}}`.
2. Generate the Scout's search queries from their roles and locations into `settings.search` (see the example).
3. **Memory:** write `areas/job-hunt.md` as described in `storage-and-memory.md`. Saving it is part of what the candidate asked for at setup, so do it now. If a save is refused (pay, for example, can be a protected detail), tell them in one line; the store still has it.
4. Render their untailored resume once to check the tools work:

   ```
   python3 scripts/resume_tool.py master master-resume.json work/spec-master.json
   python3 scripts/resume_tool.py render master-resume.json work/spec-master.json work/master
   ```

   Save `spec-master.json` to the store and send them the PDF. If it differs visibly from their own resume, that's fine: this layout is ATS-friendly. Their own file stays the default for `profile` portals.

## 6. Finish

Summarise in 5 lines or fewer: the store location, portals, targets, caps, and what's still missing (for example "Apify not connected; I'll search in the browser"). Then offer:

- run `discover` now, and
- schedule it (`scheduling.md`).
