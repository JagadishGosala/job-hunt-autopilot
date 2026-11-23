#!/usr/bin/env python3
"""Resume tool for job-hunt-autopilot: build, render and lint resumes from a master resume.

  python3 resume_tool.py master  MASTER.json OUT_SPEC.json         # baseline spec from master
  python3 resume_tool.py render  MASTER.json SPEC.json OUT_DIR     # PDF + extracted text + lint report
  python3 resume_tool.py lint    MASTER.json SPEC.json             # lint only (prints JSON)

The master resume is the single source of truth. A spec may select, reorder, shorten and re-word facts,
but the linter rejects numbers, skills, employers or gap terms that are not in the master.
Rendering needs Playwright (Chromium) and poppler-utils (pdftotext, pdfinfo).
"""
import json, re, sys, os, html, subprocess

NUM_RE = re.compile(r"(?<![\w])[~>]?\d[\d.,]*(?:\s?[KMkm]\b|%|x\b|\+)*(?:\s?[–-]\s?\d+)?")


def norm_num(s):
    s = s.replace("~", "").replace(" ", "").replace("-", "–").lower()
    return s.rstrip(",.")


def nums(text):
    return {norm_num(m.group(0)) for m in NUM_RE.finditer(text or "")}


def fact_index(master):
    idx = {}
    for e in master["experience"]:
        for g in e["groups"]:
            for f in g["facts"]:
                idx[f["id"]] = (e["id"], f)
    for p in master.get("projects", []):
        for f in p["facts"]:
            idx[f["id"]] = (p["id"], f)
    return idx


def master_skills(master):
    out = set()
    for items in master["skills"].values():
        for it in items:
            out.add(it.lower())
            out.add(re.sub(r"\s*\(.*\)", "", it).lower())
    return out


def master_to_spec(master):
    titles = master.get("title_lines", {})
    first_title = next(iter(titles.values()), "") if titles else ""
    return {
        "job_id": "master",
        "title_line": first_title,
        "summary": {"text": master["summary_master"], "fact_ids": list(master.get("essence_fact_ids", []))},
        "skills": master["skills"],
        "experience": [{"id": e["id"], "groups": [{"heading": g.get("heading"), "bullets": [{"fact_id": f["id"], "text": f["text"]} for f in g["facts"]]} for g in e["groups"]]} for e in master["experience"]],
        "projects": [{"id": p["id"], "bullets": [{"fact_id": f["id"], "text": f["text"]} for f in p["facts"]]} for p in master.get("projects", [])],
        "education": True,
    }


def lint(master, spec):
    idx = fact_index(master)
    issues = []
    all_master_text = "\n".join([master.get("summary_master", ""), json.dumps(master["skills"], ensure_ascii=False)] + [f["text"] for _, f in idx.values()])
    master_nums = nums(master.get("summary_master", "")).union(*(nums(f["text"]) for _, f in idx.values()))
    used = []
    exp_ids = {e["id"] for e in master["experience"]}
    proj_ids = {p["id"] for p in master.get("projects", [])}

    def check_bullet(owner, b, where):
        fid = b.get("fact_id")
        if fid not in idx:
            issues.append({"severity": "must-fix", "where": where, "issue": f"unknown fact_id {fid!r}"})
            return
        src_owner, f = idx[fid]
        if src_owner != owner:
            issues.append({"severity": "must-fix", "where": where, "issue": f"fact {fid} belongs to {src_owner}, placed under {owner}"})
        extra = nums(b["text"]) - nums(f["text"])
        if extra:
            issues.append({"severity": "must-fix", "where": where, "issue": f"numbers not in source fact {fid}: {sorted(extra)}"})
        used.append(fid)

    for e in spec.get("experience", []):
        if e["id"] not in exp_ids:
            issues.append({"severity": "must-fix", "where": e["id"], "issue": "unknown experience id"})
            continue
        for g in e.get("groups", []):
            for i, b in enumerate(g.get("bullets", [])):
                check_bullet(e["id"], b, f"{e['id']}/{g.get('heading')}/{i+1}")
    for p in spec.get("projects", []):
        if p["id"] not in proj_ids:
            issues.append({"severity": "must-fix", "where": p["id"], "issue": "unknown project id"})
            continue
        for i, b in enumerate(p.get("bullets", [])):
            check_bullet(p["id"], b, f"{p['id']}/{i+1}")

    if len(used) != len(set(used)):
        issues.append({"severity": "should-fix", "where": "bullets", "issue": "same fact used more than once"})
    for exp in exp_ids - {e["id"] for e in spec.get("experience", [])}:
        issues.append({"severity": "must-fix", "where": exp, "issue": "employment entry omitted (creates an unexplained gap)"})

    s = spec.get("summary", {})
    extra = nums(s.get("text", "")) - master_nums
    if extra:
        issues.append({"severity": "must-fix", "where": "summary", "issue": f"numbers not found anywhere in master: {sorted(extra)}"})

    ms = master_skills(master)
    exact = {it.lower(): it for items in master["skills"].values() for it in items}
    base_of = lambda x: re.sub(r"\s*\(.*\)", "", x).strip().lower()
    for cat, items in spec.get("skills", {}).items():
        for it in items:
            if isinstance(it, dict):
                text, src = it.get("text", ""), it.get("source", "")
                if src.lower() not in exact:
                    issues.append({"severity": "must-fix", "where": f"skills/{cat}", "issue": f"re-worded skill {text!r} has source {src!r}, which is not a master skill item"})
                elif base_of(src) not in text.lower():
                    issues.append({"severity": "must-fix", "where": f"skills/{cat}", "issue": f"re-worded skill {text!r} drops its technology name {base_of(src)!r}"})
                if nums(text) - nums(src):
                    issues.append({"severity": "must-fix", "where": f"skills/{cat}", "issue": f"skill wording adds numbers: {text!r}"})
            elif it.lower() not in exact and it.lower() not in ms:
                issues.append({"severity": "must-fix", "where": f"skills/{cat}", "issue": f"skill not in master: {it!r} (use {{text, source}} to re-word an existing skill)"})
            elif it.lower() not in exact and "(" in it:
                issues.append({"severity": "must-fix", "where": f"skills/{cat}", "issue": f"skill {it!r} changes a master item's detail; use {{text, source}}"})

    ess = set(master.get("essence_fact_ids", []))
    present = set(used) | set(s.get("fact_ids", []))
    missing = sorted(ess - present)
    if missing:
        issues.append({"severity": "must-fix", "where": "essence", "issue": f"core story facts missing (need a bullet or summary.fact_ids): {missing}"})
    unknown_sum = [f for f in s.get("fact_ids", []) if f not in idx]
    if unknown_sum:
        issues.append({"severity": "must-fix", "where": "summary", "issue": f"unknown summary fact_ids {unknown_sum}"})

    full_text = spec_plain_text(master, spec)
    for pat in master.get("gap_patterns", []):
        m = re.search(pat, full_text)
        if m and not re.search(pat, all_master_text):
            issues.append({"severity": "must-fix", "where": "anywhere", "issue": f"claims a gap term not in master: {m.group(0)!r}"})
    return {"used_fact_ids": used, "issues": issues}


def skill_text(i):
    return i["text"] if isinstance(i, dict) else i


def spec_plain_text(master, spec):
    parts = [spec.get("title_line", ""), spec.get("summary", {}).get("text", "")]
    for cat, items in spec.get("skills", {}).items():
        parts.append(cat + ": " + ", ".join(skill_text(i) for i in items))
    for e in spec.get("experience", []):
        for g in e.get("groups", []):
            parts.append(g.get("heading") or "")
            parts += [b["text"] for b in g.get("bullets", [])]
    for p in spec.get("projects", []):
        parts += [b["text"] for b in p.get("bullets", [])]
    return "\n".join(parts)


CSS = """
@page { size: A4; margin: 13mm 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: Carlito, Calibri, 'Liberation Sans', Arial, sans-serif; font-size: 10.3pt; line-height: 1.32; color: #111; margin: 0; hyphens: none; }
h1 { font-size: 19pt; letter-spacing: .04em; margin: 0; text-align: center; }
.title { text-align: center; font-size: 11pt; font-weight: 700; margin-top: 1px; color: #1d3b5a; }
.contact { text-align: center; font-size: 9.6pt; margin: 2px 0 6px; }
h2 { font-size: 10.6pt; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid #333; margin: 9px 0 4px; padding-bottom: 1px; }
h3 { font-size: 10pt; margin: 5px 0 1px; font-style: italic; font-weight: 700; }
.role { display: flex; justify-content: space-between; font-weight: 700; margin-top: 4px; }
.desc { font-style: italic; font-size: 9.6pt; color: #333; margin-bottom: 1px; }
ul { margin: 1px 0 2px 15px; padding: 0; }
li { margin: 0 0 2px; }
.skills div { margin: 0 0 1px; }
p { margin: 0; }
"""


def render_html(master, spec):
    c = master["contact"]
    e = lambda s: re.sub(r"(\w+(?:-\w+)+)", r"<span style='white-space:nowrap'>\1</span>", html.escape(s or ""))
    out = [f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"]
    out.append(f"<h1>{e(c['name'].upper())}</h1>")
    if spec.get("title_line"):
        out.append(f"<div class='title'>{e(spec['title_line'])}</div>")
    links = [e(c[k]) for k in ("phone", "email", "linkedin", "github") if c.get(k)]
    if c.get("portfolio"):
        href = c["portfolio"] if c["portfolio"].startswith("http") else "https://" + c["portfolio"]
        links.append(f"<a href='{html.escape(href)}' style='color:inherit'>{e(c['portfolio'])}</a>")
    second = " · ".join(x for x in [e(c.get("location")), e(c.get("work_modes")), ("Notice: " + e(c["notice"])) if c.get("notice") else ""] if x)
    out.append(f"<div class='contact'>{' | '.join(links)}" + (f"<br>{second}" if second else "") + "</div>")
    if spec.get("summary", {}).get("text"):
        out.append(f"<h2>Summary</h2><p>{e(spec['summary']['text'])}</p>")
    out.append("<h2>Technical Skills</h2><div class='skills'>")
    for cat, items in spec["skills"].items():
        out.append(f"<div><b>{e(cat)}:</b> {e(', '.join(skill_text(i) for i in items))}</div>")
    out.append("</div><h2>Professional Experience</h2>")
    mexp = {x["id"]: x for x in master["experience"]}
    for ex in spec["experience"]:
        m = mexp[ex["id"]]
        out.append(f"<div class='role'><span>{e(m['company'].upper())} — {e(m['title'])}</span><span>{e(m.get('dates'))}</span></div>")
        if m.get("descriptor"):
            out.append(f"<div class='desc'>{e(m['descriptor'])}</div>")
        for g in ex["groups"]:
            if g.get("heading"):
                out.append(f"<h3>{e(g['heading'])}</h3>")
            out.append("<ul>" + "".join(f"<li>{e(b['text'])}</li>" for b in g["bullets"]) + "</ul>")
    if spec.get("projects"):
        out.append("<h2>Projects</h2>")
        mp = {x["id"]: x for x in master.get("projects", [])}
        for p in spec["projects"]:
            m = mp[p["id"]]
            head = e(m["name"].upper()) + (f" — {e(m['role'])}" if m.get("role") else "")
            out.append(f"<div class='role'><span>{head}</span><span>{e(m.get('link'))}</span></div>")
            out.append("<ul>" + "".join(f"<li>{e(b['text'])}</li>" for b in p["bullets"]) + "</ul>")
    if spec.get("education", True) and master.get("education"):
        out.append("<h2>Education</h2>")
        for ed in master["education"]:
            out.append(f"<div class='role'><span>{e(ed['degree'])} — {e(ed['school'])}</span><span>{e(ed.get('dates'))}</span></div>")
    out.append("</body></html>")
    return "".join(out)


def render(master, spec, out_dir):
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    jid = spec.get("job_id", "resume")
    base = os.path.join(out_dir, jid)
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(render_html(master, spec))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + os.path.abspath(base + ".html"))
        pg.pdf(path=base + ".pdf", format="A4", print_background=True, prefer_css_page_size=True)
        b.close()
    subprocess.run(["pdftotext", "-layout", base + ".pdf", base + ".txt"], check=True)
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", base + ".pdf"], capture_output=True, text=True).stdout).group(1))
    report = lint(master, spec)
    txt = open(base + ".txt", encoding="utf-8").read()
    maxp = master.get("format", {}).get("max_pages", 2)
    report["page_note"] = "one page" if pages == 1 else f"{pages} pages"
    if pages > maxp:
        report["issues"].append({"severity": "must-fix", "where": "layout", "issue": f"{pages} pages (max {maxp})"})
    flat = re.sub(r"\s+", " ", txt)
    lost = []
    for cat, items in spec["skills"].items():
        for it in items:
            key = re.sub(r"\s*\(.*\)", "", skill_text(it))
            if key not in flat:
                lost.append(key)
    for w in set(re.findall(r"\b\w+-\w+\b", spec_plain_text(master, spec))):
        if w not in flat:
            lost.append(w)
    if lost:
        report["issues"].append({"severity": "should-fix", "where": "ats-extraction", "issue": f"terms not extractable intact from PDF: {sorted(set(lost))[:20]}"})
    report.update({"pages": pages, "pdf": base + ".pdf", "text": base + ".txt",
                   "lint_pass": not any(i["severity"] == "must-fix" for i in report["issues"])})
    with open(base + ".lint.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    master = json.load(open(sys.argv[2], encoding="utf-8"))
    if cmd == "master":
        json.dump(master_to_spec(master), open(sys.argv[3], "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("wrote", sys.argv[3])
    elif cmd == "lint":
        print(json.dumps(lint(master, json.load(open(sys.argv[3], encoding="utf-8"))), indent=2, ensure_ascii=False))
    elif cmd == "render":
        print(json.dumps(render(master, json.load(open(sys.argv[3], encoding="utf-8")), sys.argv[4]), indent=2, ensure_ascii=False))
    else:
        print(__doc__)
        sys.exit(1)
