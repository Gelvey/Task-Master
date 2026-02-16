# Task-Master AI Agent Instructions

## Big Picture
- This repo has **three clients over one task data model**: desktop Tkinter (`Task-Master.py`), Flask web app (`web_app/`), and Discord bot (`discord_bot/`).
- Core storage path is shared: `users/{username}/tasks` in Firebase Realtime DB. Each client also has local JSON fallback.
- The bot also stores operational metadata under `bot_metadata/*` (task board message IDs, reminder history, forum thread mappings).

## Shared Task Contract (Do Not Drift)
- Task records are keyed by task id/name for backward compatibility; fields are: `name`, `uuid`, `deadline`, `status`, `order`, `description`, `url`, `owner`, `colour`.
- `uuid` is the stable cross-system identifier; preserve/add it when touching migration or rename logic.
- Status values used across UI and services: `To Do`, `In Progress`, `Complete`.
- Priority values (`colour`) are constrained to: `default`, `Important`, `Moderately Important`, `Not Important`.

## Service Boundaries
- `web_app/app.py`: Flask routes + persistence helpers (`load_tasks`, `save_tasks`, `delete_task`) + session/IP whitelist auth.
- `discord_bot/database/firebase_manager.py`: shared database abstraction (Firebase/env credentials/file credentials/local fallback).
- `discord_bot/services/task_service.py`: business operations; triggers board refresh after writes.
- `discord_bot/services/message_updater.py`: persistent task-board message lifecycle in legacy channel mode.
- `discord_bot/services/forum_sync_service.py`: forum-thread sync keyed by task UUID (with legacy key migration fallback).
- `discord_bot/services/reminder_service.py`: 24h reminders + daily overdue notices, persisted dedupe state.

## Critical Runtime Modes
- Discord bot has two mutually exclusive display modes:
  - **Legacy board mode**: `TASK_CHANNEL` set, message board + filter view.
  - **Forum mode**: `TASK_FORUM_CHANNEL` set, one-thread-per-task + optional `DASHBOARD_CHANNEL`.
- Web app has optional single-user mode via `TASKMASTER_USERNAME`; otherwise session login at `/login`.

## Developer Workflows
- Desktop app: `python Task-Master.py`
- Web app: `cd web_app && pip install -r requirements.txt && python app.py`
- Discord bot: `cd discord_bot && pip install -r requirements.txt && python bot.py`
- Railway deploy entrypoint is web app: `railway.json` uses `cd web_app && gunicorn app:app`.
- There is no discovered committed test suite in this repo; validate changes by running the relevant app mode.

## Project-Specific Conventions
- Keep name-keyed task compatibility unless doing a deliberate migration; many paths still assume `task.id == task.name`.
- Reorder operations are **within one priority group only** (`/api/tasks/reorder` and bot DB reorder enforce this).
- In Discord, read-only dashboard behavior is enforced by deleting non-bot messages in dashboard channel.
- Environment-first credentials loading is expected; file-based fallback order matters (especially in `discord_bot`).

## Integration Points to Preserve
- Discord user-to-owner mapping uses env vars: `DISCORD_USER_<discord_id>=OwnerName` plus `OWNERS` and `TASKMASTER_USERNAME`.
- Reminder mentions rely on reverse owner mapping in `Settings.get_discord_user_for_owner`.
- If you change task identity logic, update both web API handlers and bot forum mapping persistence paths.

## Safe Change Checklist
- When changing task schema/validation, update all three clients (`Task-Master.py`, `web_app/app.py`, `discord_bot/database/task_model.py`).
- When changing bot startup/config behavior, verify `discord_bot/config/settings.py` import-time `Settings.load()` side effects.
- Prefer minimal, compatibility-safe migrations (as done for UUID backfill) over destructive key changes.