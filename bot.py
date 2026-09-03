import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import json
from dotenv import load_dotenv
from scraper import MojangScraper, JobTracker, Job

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3600"))
KEYWORDS_FILE = "keywords.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scraper = MojangScraper()
tracker = JobTracker()


def load_keywords() -> list:
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, "r") as f:
            return json.load(f)
    return []


def save_keywords(keywords: list):
    with open(KEYWORDS_FILE, "w") as f:
        json.dump(keywords, f, indent=2)


def job_embed(job: Job) -> discord.Embed:
    embed = discord.Embed(
        title=job.title,
        url=job.url,
        color=discord.Color.green()
    )
    embed.add_field(name="Location", value=job.location, inline=True)
    if job.department:
        embed.add_field(name="Department", value=job.department, inline=True)
    embed.set_footer(text="Mojang Studios")
    return embed


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")

    if not check_jobs.is_running():
        check_jobs.start()


@tasks(seconds=CHECK_INTERVAL)
async def check_jobs():
    await bot.wait_until_ready()

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("[Bot] Channel not found!")
        return

    keywords = load_keywords()
    jobs = scraper.fetch_all()
    new_jobs = [j for j in jobs if tracker.is_new(j)]

    if keywords:
        new_jobs = [j for j in new_jobs if j.matches_keywords(keywords)]

    if new_jobs:
        for job in new_jobs:
            embed = job_embed(job)
            await channel.send(f"New Mojang opening: **{job.title}**", embed=embed)
            tracker.mark_seen(job)
        print(f"[Bot] Sent {len(new_jobs)} new job alerts")
    else:
        print(f"[Bot] No new jobs found (checked {len(jobs)} total)")


@bot.tree.command(name="check", description="Manually check for new Mojang jobs")
async def check(interaction: discord.Interaction):
    await interaction.response.defer()

    keywords = load_keywords()
    jobs = scraper.fetch_all()
    new_jobs = [j for j in jobs if tracker.is_new(j)]

    if keywords:
        new_jobs = [j for j in new_jobs if j.matches_keywords(keywords)]

    if not new_jobs:
        await interaction.followup.send(
            f"No new jobs found. Tracking {len(tracker.seen)} known jobs."
        )
        return

    embeds = [job_embed(j) for j in new_jobs[:10]]
    await interaction.followup.send(
        f"Found {len(new_jobs)} new jobs:", embeds=embeds
    )

    for job in new_jobs:
        tracker.mark_seen(job)


@bot.tree.command(name="list", description="List all current Mojang openings")
async def list_jobs(interaction: discord.Interaction):
    await interaction.response.defer()

    keywords = load_keywords()
    jobs = scraper.fetch_all()

    if keywords:
        jobs = [j for j in jobs if j.matches_keywords(keywords)]

    if not jobs:
        await interaction.followup.send("No jobs found matching your filters.")
        return

    embeds = [job_embed(j) for j in jobs[:10]]
    await interaction.followup.send(
        f"Showing {len(jobs)} Mojang jobs" + (f" (filtered by: {', '.join(keywords)})" if keywords else "") + ":",
        embeds=embeds
    )


@bot.tree.command(name="filter", description="Add or remove keyword filters")
@app_commands.describe(
    action="Add or remove",
    keyword="The keyword to filter by"
)
@app_commands.choices(action=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="clear", value="clear"),
    app_commands.Choice(name="list", value="list"),
])
async def filter_jobs(interaction: discord.Interaction, action: str, keyword: str = ""):
    keywords = load_keywords()

    if action == "add" and keyword:
        if keyword.lower() not in [k.lower() for k in keywords]:
            keywords.append(keyword)
            save_keywords(keywords)
            await interaction.response.send_message(f"Added filter: **{keyword}**")
        else:
            await interaction.response.send_message(f"Filter **{keyword}** already exists.")

    elif action == "remove" and keyword:
        keywords = [k for k in keywords if k.lower() != keyword.lower()]
        save_keywords(keywords)
        await interaction.response.send_message(f"Removed filter: **{keyword}**")

    elif action == "clear":
        save_keywords([])
        await interaction.response.send_message("All filters cleared.")

    elif action == "list":
        if keywords:
            await interaction.response.send_message(
                f"Active filters: **{', '.join(keywords)}**"
            )
        else:
            await interaction.response.send_message("No filters set. All jobs will be shown.")


@bot.tree.command(name="all", description="Show all jobs without filters")
async def all_jobs(interaction: discord.Interaction):
    await interaction.response.defer()

    jobs = scraper.fetch_all()

    if not jobs:
        await interaction.followup.send("No jobs found.")
        return

    embeds = [job_embed(j) for j in jobs[:10]]
    await interaction.followup.send(
        f"All {len(jobs)} Mojang openings:", embeds=embeds
    )


@bot.tree.command(name="help_jobs", description="Show all available commands")
async def help_jobs(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Mojang Job Alert Bot",
        description="Monitor Mojang Studios job openings",
        color=discord.Color.blue()
    )
    commands_list = [
        ("/check", "Manually check for new jobs"),
        ("/list", "List current openings (respects filters)"),
        ("/all", "Show all jobs, ignore filters"),
        ("/filter add <keyword>", "Add a keyword filter (e.g., 'community')"),
        ("/filter remove <keyword>", "Remove a keyword filter"),
        ("/filter clear", "Remove all filters"),
        ("/filter list", "Show active filters"),
    ]
    for name, desc in commands_list:
        embed.add_field(name=name, value=desc, inline=False)
    embed.set_footer(text="Auto-checks run every hour. Use /check for instant check.")
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: Set DISCORD_TOKEN in .env file!")
        exit(1)
    if CHANNEL_ID == 0:
        print("ERROR: Set CHANNEL_ID in .env file!")
        exit(1)
    bot.run(TOKEN)
