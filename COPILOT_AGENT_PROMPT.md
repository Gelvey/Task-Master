# Copilot Agent Task: Implement Task-Master Discord Bot

## Primary Instruction

**BEFORE DOING ANYTHING ELSE**: Read the complete implementation guide located at:
```
/home/gelvey/github-repos/Task-Master/DISCORD_BOT_IMPLEMENTATION_GUIDE.md
```

This file contains your **complete and detailed instructions** for this task.

---

## Task Overview

Implement a Discord bot integration for the Task-Master application that:
- Creates a persistent task board in Discord channels using a single auto-updating message
- Allows users to interact with tasks via buttons, modals, and select menus (no text commands for task operations)
- Seamlessly integrates with the existing Firebase/local JSON database shared by the web app and desktop client
- Maps Discord users to Task-Master "Owners" via environment variables
- Sends deadline reminders to a separate notification channel

---

## What You Need To Do

1. **Read the implementation guide** (`DISCORD_BOT_IMPLEMENTATION_GUIDE.md`) in its entirety
2. Follow the **10-phase implementation checklist** provided in the guide
3. Create the **complete directory structure** under `discord_bot/` as specified
4. Implement **all components** with the exact code provided in the guide
5. Test the integration to ensure it works with existing Task-Master infrastructure

---

## Key Requirements from Guide

- **Architecture**: Single persistent message task board, modal-based input, button/menu interactions
- **Database**: Use same Firebase backend as web app (`firebase_manager.py`)
- **User Mapping**: Discord User ID → Owner name via `.env` config
- **UI Components**: Rich embeds, buttons, modals, select menus (all code provided in guide)
- **Background Tasks**: Auto-refresh task board every 60 seconds, check reminders every 5 minutes
- **Channels**: Bot operates only in designated task channels, sends reminders to separate channel

---

## Directory Structure Preview

The guide specifies creating:
```
discord_bot/
├── bot.py
├── requirements.txt
├── .env.example
├── .env
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py
│   └── settings.py
├── database/
│   ├── __init__.py
│   ├── firebase_manager.py
│   └── task_model.py
├── discord_ui/
│   ├── __init__.py
│   ├── embeds.py
│   ├── buttons.py
│   ├── modals.py
│   └── select_menus.py
├── services/
│   ├── __init__.py
│   ├── task_service.py
│   ├── message_updater.py
│   └── reminder_service.py
└── utils/
    ├── __init__.py
    ├── logger.py
    └── validators.py
```

---

## Critical Integration Points

**From the guide, ensure you understand:**

1. **Task Schema** - Must match exactly:
   - name, deadline, status, order, description, url, owner, colour
   
2. **Firebase Path** - Use same structure as web app:
   - `users/{username}/tasks/{task_id}`

3. **User Mapping** - Environment variable format:
   - `DISCORD_USER_123456789012345678=OwnerName`

4. **Task Board Updates** - Auto-refresh mechanism that updates existing messages

5. **Reminders** - Check deadlines within 24 hours, mention Discord user in separate channel

---

## Implementation Approach

Follow the **Phase-by-phase checklist** in the guide:
- Phase 1: Setup directory structure and dependencies
- Phase 2: Database layer (task model, Firebase manager)
- Phase 3: Configuration (settings loader)
- Phase 4: Discord UI components (embeds, buttons, modals, menus)
- Phase 5: Services (task service, message updater, reminder service)
- Phase 6: Main bot (bot.py with event handlers)
- Phase 7-10: Testing, integration, documentation, polish

---

## Expected Deliverables

1. ✅ Complete `discord_bot/` directory with all files
2. ✅ Working bot that connects to Discord
3. ✅ Task board displays in configured channels
4. ✅ Users can add/edit/delete tasks via modals and buttons
5. ✅ Tasks sync with web app and desktop client (shared database)
6. ✅ Reminders work for upcoming deadlines
7. ✅ `.env.example` and README.md documentation

---

## Important Notes

- **All code is provided** in the implementation guide - use it as-is
- **Test incrementally** after each phase
- **Ask clarifying questions** if anything in the guide is unclear
- **Maintain compatibility** with existing Task-Master web app and desktop client
- The guide is ~50,000 characters with complete implementation details

---

## Getting Started

```bash
# Step 1: Read the guide
cat DISCORD_BOT_IMPLEMENTATION_GUIDE.md

# Step 2: Follow Phase 1 instructions from the guide
# Create directory structure, install dependencies, etc.
```

---

**BEGIN IMPLEMENTATION BY READING THE FULL GUIDE NOW.**
