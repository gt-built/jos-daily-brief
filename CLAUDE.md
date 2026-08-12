# CLAUDE.md

## Role
Act as the senior technical architect and planning partner for this project.

## Main responsibility
Use Claude Code primarily for:
- understanding the codebase
- architecture decisions
- debugging strategy
- refactoring plans
- task breakdowns

## Working style
- First make a short plan.
- Ask before making large changes.
- Prefer small, reviewable steps.
- Do not implement more than one feature at a time.
- Keep context compact.

## Output format
For each task, provide:
1. Diagnosis
2. Proposed approach
3. Files likely involved
4. Risks
5. Next concrete implementation step

## Usage control
- Avoid reading the whole repository.
- Use targeted file inspection.
- Do not generate full files unless needed.

## Architecture (current state)
- Production runs in Docker on a Proxmox VM named "docker" (192.168.1.107),
  repo checked out at `~/jos-daily-brief`. The Raspberry Pi this project
  originally ran on is retired; Pi-specific instructions in the README are
  historical only.
- `docker-compose.yml` has two services:
  - `daily-brief` — the actual brief. `docker compose run --rm daily-brief
    [--text|--print]`. Bind-mounts `./config`, `./cache`, `./output`; USB
    printer passthrough via `devices: /dev/usb/lp0`.
  - `google-login` — one-off/occasional Google OAuth re-auth. Runs with
    `network_mode: host` (required — see "Known gotchas" below).
- Scheduling: system-level systemd timer on the VM, not in this repo's
  runtime — `deploy/docker/jos-daily-brief.service` + `.timer`, installed at
  `/etc/systemd/system/`, fires daily at 06:30 (`Persistent=true` catches
  missed runs). Check with `systemctl list-timers jos-daily-brief.timer` /
  `journalctl -u jos-daily-brief.service` (needs sudo for stdout on the VM).
- Secrets live only in `.env` on the VM (`chmod 600`), edited directly there
  via `nano` — never pasted into chat, never committed.

## Known gotchas
- NIEUWS source history: GDELT (`daily_brief/news.py`) rate-limits to 1
  request/5s and returned 429s too often for a reliable daily run; Reddit
  (`daily_brief/reddit_news.py`) is blocked by Reddit's own app-registration
  policy. Current default is `daily_brief/tweakers_news.py` (Tweakers RSS,
  keyword-filtered, no auth needed). All three modules stay in the repo;
  only one is wired up in `brief.py` at a time.
- `InstalledAppFlow.run_local_server()` (Google login) binds to `localhost`
  inside the container. Docker's port-publish NAT delivers traffic to the
  container's real interface, not loopback, so a published port silently
  resets every connection. Fix is `network_mode: host` (the `google-login`
  service), not `host="0.0.0.0"` — that binds correctly but then also gets
  baked into the advertised `redirect_uri`, breaking the browser redirect.
- Printer is an Epson TM-T88-family unit (576-dot/72mm print head) reached
  via USB passthrough: Proxmox host → VM → container. Paper is 78mm, leaving
  only ~3mm slack per side — a right-edge print cutoff (teletekst page
  numbers) was compensated in software via `MARGIN_RIGHT` in
  `daily_brief/renderer.py` (larger than the left `MARGIN`) rather than by
  re-centering the roll — a pragmatic buffer, not a confirmed root-cause fix.
- Vacation/pause printing without touching the timer: set
  `DAILY_BRIEF_PAUSE_FROM` / `DAILY_BRIEF_PAUSE_UNTIL` (ISO dates, inclusive)
  in `.env` on the VM. `--print` no-ops in that range; `--text` still works.