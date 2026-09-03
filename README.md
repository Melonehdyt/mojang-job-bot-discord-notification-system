# Mojang Job Alert Bot

Discord bot that monitors Mojang Studios job openings and sends alerts when new positions are posted.

## Setup

### 1. Create a Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it → **Create**
3. Go to **Bot** tab → click **Add Bot**
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Copy the **Bot Token**

### 2. Get Your Channel ID

1. In Discord, go to **User Settings** → **Advanced** → enable **Developer Mode**
2. Right-click the channel where you want alerts → **Copy Channel ID**

### 3. Install & Run

```bash
cd mojang-job-bot
pip install -r requirements.txt
```

Create `.env` file (copy from `.env.example`):
```
DISCORD_TOKEN=your_bot_token_here
CHANNEL_ID=your_channel_id_here
CHECK_INTERVAL=3600
```

Run the bot:
```bash
python bot.py
```

### 4. Invite Bot to Server

1. Go to **OAuth2** → **URL Generator** in the developer portal
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: **Send Messages**, **Embed Links**
4. Copy the generated URL → open in browser → add to your server

## Commands

| Command | Description |
|---------|-------------|
| `/check` | Manually check for new jobs |
| `/list` | List current openings (respects filters) |
| `/all` | Show all jobs, ignore filters |
| `/filter add <keyword>` | Add a keyword filter |
| `/filter remove <keyword>` | Remove a keyword filter |
| `/filter clear` | Remove all filters |
| `/filter list` | Show active filters |
| `/help_jobs` | Show all commands |

## Examples

Filter for community roles:
```
/filter add community
/filter add moderation
```

Filter for engineering:
```
/filter add java
/filter add engineer
```

## How It Works

- Bot checks Mojang's job boards every hour (configurable)
- Sends Discord embed alerts for new positions
- Tracks seen jobs in `seen_jobs.json` to avoid duplicates
- Keyword filters let you focus on relevant roles

## Data Sources

- Greenhouse API (official Mojang job board)
- Greenhouse web page
- HubMub job aggregator
