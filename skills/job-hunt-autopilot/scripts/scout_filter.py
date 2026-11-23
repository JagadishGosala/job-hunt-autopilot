#!/usr/bin/env python3
"""Rule-based pre-filter for the Scout. Runs on titles and metadata only, before any job description
is read, so no tokens are spent on jobs that could never fit. All rules come from settings.json.

  python3 scout_filter.py CANDIDATES.json EXISTING_IDS.json SETTINGS.json [NEEDS.json] > kept.json

CANDIDATES.json  list of rows from any portal. Keys are detected loosely:
                 title/jobTitle/position, company/companyName/employer, location/locations/jobLocation,
                 experience/exp/experienceRange or minExperience+maxExperience, url/jobUrl/link/applyUrl,
                 id/jobId/job_id, posted/postedAt/postedDate, portal, plus dataset_id and idx for Apify rows.
EXISTING_IDS.json list of job_ids already in jobs.json.
SETTINGS.json    the candidate's settings (targets, excluded_employers, portals, limits).
NEEDS.json       optional {portal: n}: how many jobs to mark "found" per portal (default target_per_portal).

Output: {"found": [...], "reserve": [...], "dropped": {reason: count}, "total": n}
Each kept row has job_id, portal, pool_rank (1 = best within its portal) and prefilter_score.
"""
import json, re, sys


def rx(pattern, default=None):
    p = pattern or default
    return re.compile(p, re.I) if p else None


def pick(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return ""


def text(v):
    if isinstance(v, list):
        return ", ".join(text(x) for x in v)
    if isinstance(v, dict):
        return " ".join(text(x) for x in v.values())
    return str(v)


def exp_range(d):
    lo, hi = d.get("minExperience"), d.get("maxExperience")
    if isinstance(lo, (int, float)) or isinstance(hi, (int, float)):
        return (lo if lo is not None else 0, hi if hi is not None else 99)
    s = text(pick(d, "experience", "exp", "experienceRange", "experienceRequired", "workExperience"))
    found = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", s)]
    if len(found) >= 2:
        if found[0] == 0 and found[1] == 0:
            return None
        return (found[0], found[1])
    if len(found) == 1:
        return (found[0], found[0] + 3 if "+" in s else found[0])
    return None


def slug(*parts):
    s = "-".join(re.sub(r"[^a-z0-9]+", "-", str(p).lower()).strip("-") for p in parts if p)
    return s[:120].strip("-")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    cands = json.load(open(sys.argv[1], encoding="utf-8"))
    existing = set(json.load(open(sys.argv[2], encoding="utf-8")))
    st = json.load(open(sys.argv[3], encoding="utf-8"))
    needs = json.load(open(sys.argv[4], encoding="utf-8")) if len(sys.argv) > 4 else {}

    t = st.get("targets", {})
    years = t.get("years_experience")
    band = t.get("experience_band", 2)
    include = rx(t.get("title_include_regex"), r"engineer|developer")
    exclude = rx(t.get("title_exclude_regex"), r"\bintern(ship)?\b|trainee")
    stack_bad = rx(t.get("stack_exclude_regex"))
    stack_ok = rx(t.get("stack_ok_regex"))
    loc_ok = rx("|".join(re.escape(x) for x in t.get("locations_ok", [])) or None)
    loc_bad = rx("|".join(re.escape(x) for x in t.get("locations_blocked", [])) or None)
    excluded = [x.lower() for x in st.get("excluded_employers", [])]
    source_rank = {p["name"].lower(): p.get("source_rank", 1) for p in st.get("portals", [])}
    default_need = st.get("limits", {}).get("target_per_portal", 10)

    kept, dropped, seen = [], {}, {}

    def drop(r):
        dropped[r] = dropped.get(r, 0) + 1

    for c in cands:
        title = text(pick(c, "title", "jobTitle", "position", "name"))
        company = text(pick(c, "company", "companyName", "employer", "organization"))
        loc = text(pick(c, "location", "locations", "jobLocation", "place"))
        portal = text(c.get("portal", ""))
        url = text(pick(c, "url", "jobUrl", "link", "applyUrl", "publicUrl", "apply_url"))
        jid_src = text(pick(c, "id", "jobId", "job_id")) or url.rstrip("/").split("/")[-1]
        job_id = slug(portal, company, title, jid_src)
        if not title:
            drop("no title"); continue
        if any(x and x in company.lower() for x in excluded):
            drop("excluded employer"); continue
        if job_id in existing:
            drop("already tracked"); continue
        if stack_bad and stack_bad.search(title) and not (stack_ok and stack_ok.search(title)):
            drop("unwanted stack"); continue
        if exclude and exclude.search(title):
            drop("title excluded"); continue
        if include and not include.search(title):
            drop("title not a target role"); continue
        remote_ok = re.search(r"remote|work from home|wfh|anywhere", loc, re.I) and "remote" in [m.lower() for m in t.get("work_modes", [])]
        if loc and not remote_ok and not (loc_ok and loc_ok.search(loc)) and loc_bad and loc_bad.search(loc):
            drop("location not allowed"); continue
        er = exp_range(c)
        if years is not None and er and (er[0] > years + band or er[1] < years - band):
            drop("experience band doesn't fit"); continue

        score = 3 if (include and include.search(title)) else 1
        score += 2 if (remote_ok or (loc_ok and loc_ok.search(loc or ""))) else 0
        score += source_rank.get(portal.lower(), 1)
        score += 1 if (er and years is not None and er[0] <= years <= er[1]) else 0
        score += 1 if re.search(r"senior|lead|\bsde[\s-]?(2|ii|3|iii)\b", title, re.I) and (years or 0) >= 4 else 0
        row = {"job_id": job_id, "title": title, "company": company, "location": loc, "portal": portal, "url": url,
               "experience": list(er) if er else None, "posted": text(pick(c, "posted", "postedAt", "postedDate", "date")),
               "idx": c.get("idx"), "dataset_id": c.get("dataset_id"), "prefilter_score": score}

        key = (company.lower().strip(), re.sub(r"\W+", " ", title.lower()).strip())
        if key in seen:
            other = seen[key]
            if source_rank.get(portal.lower(), 1) > source_rank.get(other["portal"].lower(), 1):
                kept.remove(other)
                kept.append(row)
                seen[key] = row
            drop("duplicate across portals"); continue
        seen[key] = row
        kept.append(row)

    found, reserve = [], []
    by_portal = {}
    for k in sorted(kept, key=lambda k: -k["prefilter_score"]):
        by_portal.setdefault(k["portal"], []).append(k)
    for portal, rows in by_portal.items():
        n = int(needs.get(portal, default_need))
        for i, r in enumerate(rows, 1):
            r["pool_rank"] = i
            (found if i <= n else reserve).append(r)
    print(json.dumps({"found": found, "reserve": reserve, "dropped": dropped, "total": len(cands)}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
