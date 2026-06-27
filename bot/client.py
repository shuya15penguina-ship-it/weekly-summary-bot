import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot import config as cfg
from bot.summarizer import collect_messages, generate_summary

JST = timezone(timedelta(hours=9))
log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")


async def run_weekly_summary():
    conf = cfg.load()
    guild_id = conf.get("guild_id")
    output_channel_id = conf.get("output_channel_id")
    target_ids = conf.get("target_channel_ids", [])

    if not guild_id or not output_channel_id or not target_ids:
        log.warning("Weekly summary skipped: configuration incomplete.")
        return

    guild = bot.get_guild(int(guild_id))
    output_channel = guild and guild.get_channel(int(output_channel_id))
    if not output_channel:
        log.warning("Output channel not found.")
        return

    since = datetime.now(JST) - timedelta(days=7)
    channels_messages: dict[str, list[str]] = {}
    for ch_id in target_ids:
        channel = guild.get_channel(int(ch_id))
        if isinstance(channel, discord.TextChannel):
            channels_messages[channel.name] = await collect_messages(channel, since)

    await output_channel.send("📊 **週次サマリーを生成中です...**")
    try:
        summary = await generate_summary(channels_messages)
    except Exception as e:
        await output_channel.send(f"⚠️ サマリーの生成に失敗しました: {e}")
        return

    now = datetime.now(JST)
    header = f"# 📅 週次サマリー ({(now - timedelta(days=7)).strftime('%Y/%m/%d')} 〜 {now.strftime('%Y/%m/%d')})"

    for chunk in [header + "\n\n" + summary[i:i+1800] for i in range(0, len(summary), 1800)]:
        await output_channel.send(chunk)


def _reschedule(conf: dict):
    scheduler.remove_all_jobs()
    scheduler.add_job(
        run_weekly_summary,
        CronTrigger(
            day_of_week=conf["schedule_day"][:3].lower(),
            hour=conf["schedule_hour"],
            minute=conf["schedule_minute"],
            timezone="Asia/Tokyo",
        ),
        id="weekly_summary",
    )
    log.info(f"Scheduled: {conf['schedule_day']} {conf['schedule_hour']:02d}:{conf['schedule_minute']:02d} JST")


def reschedule_from_config():
    _reschedule(cfg.load())


@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    conf = cfg.load()
    if not conf.get("guild_id") and bot.guilds:
        conf["guild_id"] = bot.guilds[0].id
        cfg.save(conf)
    _reschedule(conf)
    scheduler.start()
