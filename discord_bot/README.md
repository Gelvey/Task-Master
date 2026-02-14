# Task-Master Discord Bot

Discord bot integration for Task-Master task management system. Provides full task management capabilities through Discord's interactive UI components.

## Features

- **Persistent Task Board**: Single message per channel displaying all tasks, updated in real-time
- **Interactive Modals**: Add and edit tasks through Discord popup forms
- **Button Controls**: Mark tasks complete, in progress, or delete with button clicks
- **Status Filtering**: Filter tasks by status using dropdown menus
- **Priority Levels**: Support for Important, Moderately Important, Not Important priorities
- **Deadline Reminders**: Automatic notifications for upcoming deadlines (24-hour warning)
- **Overdue Alerts**: Daily notifications for overdue tasks
- **Multi-User Support**: Maps Discord users to Task-Master owners via environment variables
- **Shared Database**: Uses same Firebase/local JSON backend as web app and desktop client
- **Persistent Storage**: Message IDs and reminder tracking stored in database (survives bot restarts)
- **Slash Commands**: Modern Discord slash commands for all bot interactions

## Prerequisites

- Python 3.11 or higher
- Discord bot token ([Create one here](https://discord.com/developers/applications))
- Firebase credentials (can be configured locally for the bot) or local storage
- Discord server with admin permissions to add the bot

## Installation

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Enable the following Privileged Gateway Intents:
   - SERVER MEMBERS INTENT
   - MESSAGE CONTENT INTENT
5. Copy the bot token (you'll need this for `.env`)

### 2. Invite Bot to Server

1. In Discord Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Add Reactions
   - Use Slash Commands
4. Copy generated URL and open in browser to invite bot

### 3. Setup Project

```bash
# Navigate to discord_bot directory
cd /path/to/Task-Master/discord_bot

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `TASKMASTER_USERNAME`: Global username for database access (e.g., "gelvey")
   - `OWNERS`: Space-separated list of possible task assignees (e.g., "Circuit Gelvey")
   - `TASK_CHANNELS`: Channel IDs where task boards will display (comma-separated)
   - `REMINDER_CHANNEL`: Channel ID for deadline reminders
   - `DISCORD_USER_*`: Map Discord user IDs to owners from OWNERS list
   - Firebase credentials (see below)

### 4a. Configure Firebase (Local to Bot)

The Discord bot has its own Firebase configuration, independent of the web app. This allows hosting the bot separately.

**Option 1: Environment Variables** (Recommended for production)
- Set all `FIREBASE_*` variables in `.env` file

**Option 2: Credentials File** (Easier for development)
- Place `credentials.json` in the `discord_bot/` directory
- The bot will automatically detect and use it

**Option 3: Shared Credentials** (If bot runs alongside web app)
- The bot will fall back to `../credentials.json` (parent directory)

Priority order: Environment variables → `discord_bot/credentials.json` → `../credentials.json`

### 5. Get Discord IDs

To get channel and user IDs:

1. Enable Developer Mode in Discord: Settings → Advanced → Developer Mode
2. Right-click on channel → Copy ID
3. Right-click on user → Copy ID

### 6. Configure User Mapping

The bot uses three key configuration values:

- **`TASKMASTER_USERNAME`**: The database username/account (e.g., "gelvey") - determines which database path to use (`users/{TASKMASTER_USERNAME}/tasks`)
- **`OWNERS`**: Space-separated list of task assignees (e.g., "Circuit Gelvey") - who can be assigned to complete tasks
- **`DISCORD_USER_*`**: Maps Discord user IDs to owners in the OWNERS list

Example in `.env`:

```env
TASKMASTER_USERNAME=gelvey
OWNERS=Circuit Gelvey
DISCORD_USER_123456789012345678=Circuit
DISCORD_USER_987654321098765432=Gelvey
```

This configuration means:
- All tasks are stored under the "gelvey" database account
- Tasks can be assigned to either "Circuit" or "Gelvey"
- When Discord user 123456789012345678 interacts, they're identified as "Circuit"
- When Discord user 987654321098765432 interacts, they're identified as "Gelvey"

## Running the Bot

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the bot
python bot.py
```

The bot should now:
- Connect to Discord
- Initialize task boards in configured channels
- Sync slash commands
- Load persisted message IDs and reminder tracking from database
- Start listening for interactions

## Usage

### Task Board

The task board is a persistent message that displays all tasks grouped by priority. It updates automatically every minute (configurable).

### Adding Tasks

1. Click **➕ Add Task** button
2. Fill out the modal form:
   - **Task Name**: Required
   - **Deadline**: Optional (format: YYYY-MM-DD HH:MM)
   - **Priority**: Optional (Important, Moderately Important, Not Important, or default)
   - **Description**: Optional
   - **URL**: Optional
3. Click Submit

### Editing Tasks

1. Click **✏️ Edit Task** button
2. Enter the exact task name
3. Update fields in the modal
4. Click Submit

### Deleting Tasks

1. Click **🗑️ Delete Task** button
2. Enter the exact task name
3. Confirm deletion

### Changing Status

1. Click **✅ Mark Complete** or **🔄 Mark In Progress**
2. Enter the task name
3. Task status will update

### Filtering Tasks

Use the dropdown menu at the top of the task board to filter by:
- All Tasks
- To Do
- In Progress
- Complete

### Reminders

The bot automatically checks for tasks with deadlines approaching within 24 hours and sends reminders to the configured reminder channel, mentioning the task owner.

## Commands

- `/help` - Show help information
- `/refresh` - Manually refresh the task board
- `/taskboard` - (Admin only) Create a new task board in current channel

**Note**: All commands use Discord's slash command system. Type `/` in Discord to see available commands.

## Architecture

```
discord_bot/
├── bot.py                 # Main bot entry point
├── config/                # Configuration management
│   └── settings.py
├── database/              # Database layer (Firebase/local)
│   ├── firebase_manager.py
│   └── task_model.py
├── discord_ui/            # Discord UI components
│   ├── embeds.py
│   ├── buttons.py
│   ├── modals.py
│   └── select_menus.py
├── services/              # Business logic
│   ├── task_service.py
│   ├── message_updater.py
│   └── reminder_service.py
└── utils/                 # Utilities
    ├── logger.py
    └── validators.py
```

## Troubleshooting

### Bot doesn't respond

- Check bot has required permissions in the channel
- Verify `TASK_CHANNELS` includes the channel ID
- Check bot is online (green status in Discord)
- Review logs in `discord_bot.log`

### Firebase connection failed

- Verify Firebase credentials in `.env` or `credentials.json`
- Check `FIREBASE_DATABASE_URL` is correct
- Ensure Firebase rules allow read/write access
- Bot can fall back to local JSON storage if Firebase fails

### Task board not updating

- Check bot has "Send Messages" and "Embed Links" permissions
- Verify task board message wasn't deleted
- Try `!refresh` command to force update
- Check `TASK_BOARD_REFRESH_INTERVAL` setting

### User mapping not working

- Verify Discord user IDs are correct (enable Developer Mode)
- Check `.env` format: `DISCORD_USER_<id>=OwnerName`
- Restart bot after changing `.env`

## Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/taskmaster-bot.service`:

```ini
[Unit]
Description=Task-Master Discord Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Task-Master/discord_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable taskmaster-bot
sudo systemctl start taskmaster-bot
sudo systemctl status taskmaster-bot
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

Build and run:
```bash
docker build -t taskmaster-discord-bot .
docker run -d --name taskmaster-bot --env-file .env taskmaster-discord-bot
```

## Contributing

This bot is part of the Task-Master project. Contributions welcome!

## License

Same as Task-Master (MIT License)

## Authors

- Circuit
- Gelvey

## Support

For issues or questions, open an issue in the Task-Master GitHub repository.
