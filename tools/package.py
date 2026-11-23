#!/usr/bin/env python3
"""Build dist/job-hunt-autopilot.zip for upload at claude.ai (Customize > Skills > Upload a skill).

The zip contains one top-level folder named after the skill, with SKILL.md inside it.
Usage: python tools/package.py
"""
import os, zipfile, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "job-hunt-autopilot"
DIST = ROOT / "dist"
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_EXT = {".pyc", ".zip"}


def main():
    assert (SKILL / "SKILL.md").exists(), f"missing {SKILL / 'SKILL.md'}"
    DIST.mkdir(exist_ok=True)
    out = DIST / "job-hunt-autopilot.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(SKILL):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in sorted(filenames):
                p = pathlib.Path(dirpath) / name
                if p.suffix in SKIP_EXT:
                    continue
                z.write(p, pathlib.Path("job-hunt-autopilot") / p.relative_to(SKILL))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
