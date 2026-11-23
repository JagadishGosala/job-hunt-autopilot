# Releasing a new version

Each `v*` tag pushed to GitHub runs `.github/workflows/release.yml`. The workflow checks that the scripts compile, builds `job-hunt-autopilot.zip` with `tools/package.py`, and attaches it to a GitHub release with auto-generated notes.

## Steps

1. **Bump the version** in `.claude-plugin/plugin.json`, using [semantic versioning](https://semver.org):
   - patch (`1.0.1`) for fixes and wording changes
   - minor (`1.1.0`) for new features or portals
   - major (`2.0.0`) when the store's file formats change in a way older setups can't read
2. **Check the package builds:**
   ```
   python tools/package.py
   ```
3. **Commit and push the change:**
   ```
   git add -A
   git commit -m "Release v1.0.1: <what changed>"
   git push
   ```
4. **Tag the commit and push the tag.** This starts the release:
   ```
   git tag -a v1.0.1 -m "v1.0.1"
   git push origin v1.0.1
   ```
5. **Check the release:** open the repo's **Actions** tab to watch the workflow, then **Releases** to confirm `job-hunt-autopilot.zip` is attached. Edit the generated notes if they need a clearer summary for users.

The tag must match the version in `plugin.json`, with a `v` in front.

## If the workflow fails

- **Before anyone has downloaded it,** delete the tag and the release, fix the problem, and tag again:
  ```
  git tag -d v1.0.1
  git push origin :refs/tags/v1.0.1
  ```
- **Run it by hand:** Actions → *Release skill zip* → *Run workflow*. A manual run uploads the zip as a workflow artifact but doesn't create a release.

## Changing file formats

The skill reads files the user already has in their store (`settings.json`, `master-resume.json`, `answer-bank.json`, `jobs.json`). If you rename or restructure a field:
- add a short migration note to `references/schemas.md`, and
- make the skill fill in or convert the field when it's missing, so existing users don't need to run setup again.
