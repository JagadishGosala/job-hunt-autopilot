# Scheduling

Offer this at the end of setup, or when the candidate asks to run the pipeline automatically.

**Requirements:**
- The store must be **project docs**. A scheduled run starts a fresh session and can't see a session-only store.
- **Apply** runs also need the candidate's computer on, with Chrome open and signed in to the portals.

**Suggested plan** (ask before creating; adjust times to their time zone):

| Scheduled task | When | Prompt |
|---|---|---|
| Job hunt: find and tailor | weekdays, morning | `Run the job-hunt-autopilot skill in discover mode. The store is project docs under job-hunt/. This run is unattended: never wait on questions; log them and move on. End by sending the numbered shortlist.` |
| Job hunt: apply to approved jobs | weekdays, evening | `Run the job-hunt-autopilot skill in apply mode. The store is project docs under job-hunt/. Apply only to approved jobs. Freeze any new question as a draft and end by sending the numbered list of open questions.` |

**How to create them:** use the session's scheduling tool (load it with ToolSearch, for example `create_trigger`). Before creating, list the existing scheduled tasks so you don't duplicate one.

- Give each task its own name.
- Write the cron expression in the candidate's time zone, with a minute that isn't `:00`.
- Set `requires_local_device: true` on the apply task.
- Store the returned ids in `settings.schedule`.
- Tell the candidate in one line whether runs will ask for approval or run automatically, as the tool result reports.

Call them "scheduled tasks" when talking to the candidate.

**Pausing:** when the candidate accepts an offer or wants a break, disable both tasks with `update_trigger` (`enabled: false`) rather than deleting them.
