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
- GDELT (`daily_brief/news.py`) rate-limits to 1 request/5s and returns a
  plain-text body explaining that on 429 — don't hammer it with rapid manual
  test runs while debugging; space retries out.
- `InstalledAppFlow.run_local_server()` (Google login) binds to `localhost`
  inside the container. Docker's port-publish NAT delivers traffic to the
  container's real interface, not loopback, so a published port silently
  resets every connection. Fix is `network_mode: host` (the `google-login`
  service), not `host="0.0.0.0"` — that binds correctly but then also gets
  baked into the advertised `redirect_uri`, breaking the browser redirect.
- Printer is an Epson TM-T88-family unit (576-dot/72mm print head) reached
  via USB passthrough: Proxmox host → VM → container. Paper is 78mm, leaving
  only ~3mm slack per side — a right-edge print cutoff was traced to
  physical roll alignment under the head, not a code/width issue.
- Vacation/pause printing without touching the timer: set
  `DAILY_BRIEF_PAUSE_FROM` / `DAILY_BRIEF_PAUSE_UNTIL` (ISO dates, inclusive)
  in `.env` on the VM. `--print` no-ops in that range; `--text` still works.