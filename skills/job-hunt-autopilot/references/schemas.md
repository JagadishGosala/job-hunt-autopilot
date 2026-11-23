# Schemas

Timestamps are ISO-8601 UTC. Files are JSON unless noted.

## settings.json

See `templates/settings.example.json` for a full example. Its fields:

- `candidate`: `{name, email, phone, links: {linkedin, github, portfolio}}`
- `targets`: `{roles[], years_experience, locations_ok[], locations_blocked[], work_modes[], title_include_regex, title_exclude_regex, stack_exclude_regex, stack_ok_regex}`. The regexes are generated at setup from the candidate's answers; `scout_filter.py` uses them.
- `compensation`: `{currency, unit, current, expected}`, each optional.
- `availability`: `{notice_period, notice_field_fallback, earliest_joining, last_working_day}`
- `standing_answers`: `{relocate, in_person_interviews, shifts, travel}`, each `"yes"`, `"no"` or `null` (unknown, so ask).
- `portals[]`: `{name, resume: "profile"|"tailored", enabled, source_rank}`. `source_rank` is used when the same job shows up on two portals (higher wins).
- `excluded_employers[]`
- `limits`: `{target_per_portal, fetch_per_portal, max_jobs_waiting, cap_per_portal}`
- `consents`: `{auto_accept[], demographics: "decline"}`
- `search`: `{keywords[], locations[], posted_within_days}`
- `tracker_sheet_url` (or `null`), `output_folder` (or `null`), `memory: {enabled, file}`, `store: {backend, location}`
- `schedule`: `{discover_task_id, apply_task_id}`, filled in when scheduled.

## jobs.json

```json
{"run_lock": null, "jobs": {"<job_id>": {
  "stage": "found",
  "company": "", "title": "", "portal": "", "url": "", "location": "", "mode": "",
  "experience_ask": "", "jd_summary": "", "found_at": "", "pool_rank": 1, "notes": "",
  "score": 0, "fit": [], "gaps": [], "must_haves": [], "nice_to_haves": [], "suggestions": [],
  "company_brief": "", "resume_variant": "profile|<title_lines key>",
  "round": 0, "resume_doc": "job-hunt/tailored/<job_id>.json",
  "validation": {"baseline_overall": 0, "rounds": [{"round": 1, "verdict": "pass|fail", "overall": 0, "truthfulness_gate": "pass|fail", "must_fix": [], "should_fix": [], "one_line_verdict": ""}]},
  "override": false,
  "resume_file": "", "apply_route": "", "applied_at": "", "confirmation": "",
  "auto_answers": [{"question": "", "answer": "", "bank_ids": []}],
  "blocked_reason": "",
  "updated_at": ""
}}}
```

**`job_id`:** a lowercase, hyphenated slug of portal + company + title + the portal's own job id, at most 120 characters. The same posting always gives the same id; that's how duplicates are skipped.

**Housekeeping (once a week):**
- Delete jobs at `applied`, `skipped`, `rejected` or `blocked` that are older than 30 days. `history.csv` keeps the record.
- Delete `reserve` jobs older than 7 days.

## questions.json

```json
{"questions": {"<job_id>--<n>": {
  "job_id": "", "company": "", "title": "", "portal": "", "url": "",
  "question": "exact wording", "field_type": "text|textarea|select|radio|checkbox|number|date|file",
  "options": [], "char_limit": null, "required": true, "context": "section heading or hint text",
  "status": "open|answered|saved", "answer": null, "reusable": true,
  "asked_at": "", "answered_at": null
}}}
```

## answer-bank.json

```json
{
  "voice": {"notes": [], "derived_from": [], "updated_at": ""},
  "answers": [{
    "id": "qa-<slug>", "intent": "reason for job change",
    "question_variants": ["exact wordings seen"],
    "answer": "the candidate's exact words", "answer_type": "text|choice|number|yes-no|date",
    "reusable": true, "company_specific": false,
    "first_seen": {"company": "", "title": "", "portal": "", "date": ""},
    "answered_by": "candidate", "times_reused": 0, "last_used": ""
  }]
}
```

- Only the candidate's own answers go in (`answered_by: "candidate"`). Composed or adapted answers are logged in the run log and on the job's `auto_answers`, never added to the bank.
- `voice.notes` describes how the candidate writes, derived only from their own written answers: sentence length, how they open, words they use, punctuation, typical length.

## master-resume.json

See `templates/master-resume.example.json`. Required fields:
- `contact`: `name`, `email`, plus optional `phone`, `linkedin`, `portfolio`, `location`, `work_modes`, `notice`
- `summary_master`, `title_lines` (an object)
- `skills` (an object of lists)
- `experience[]`: `{id, company, title, dates, descriptor, groups[]: {heading, facts[]: {id, text, tags[]}}}`
- `projects[]`: `{id, name, role, link, facts[]}`
- `education[]`, `essence_fact_ids[]`

Optional fields:
- `common_jd_asks_not_in_resume[]` and `gap_patterns[]` (regexes the linter treats as claims not in the resume)
- `screening_years{}`, `defend_notes{}`
- `format: {max_pages}`

## Tailored spec (Tailor output, `resume_tool.py` input)

```json
{"job_id": "", "title_line": "",
 "summary": {"text": "", "fact_ids": []},
 "skills": {"Category": ["Master item", {"text": "Re-worded item", "source": "Master item"}]},
 "experience": [{"id": "<experience id>", "groups": [{"heading": "", "bullets": [{"fact_id": "", "text": ""}]}]}],
 "projects": [{"id": "<project id>", "bullets": [{"fact_id": "", "text": ""}]}],
 "education": true}
```

## history.csv

`date,portal,company,title,location,stage,score,resume_used,url,notes`
