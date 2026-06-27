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


async def run_summary_for_group(group: dict):
    guild = bot.get_guild(int(group["guild_id"]))
    output_channel = guild and guild.get_channel(int(group["output_channel_id"]))
    if not output_channel:
        log.warning(f"[{group['name']}] Output channel not found.")
        return

    since = datetime.now(JST) - timedelta(days=7)
    channels_messages: dict[str, list[str]] = {}
    for ch_id in group["target_channel_ids"]:
        channel = guild.get_channel(int(ch_id))
        if isinstance(channel, discord.TextChannel):
            channels_messages[channel.name] = await collect_messages(channel, since)

    await output_channel.send(f"📊 **【{group['name']}】週次サマリーを生成中です...**")
    try:
        summary = await generate_summary(channels_messages)
    except Exception as e:
        await output_channel.send(f"⚠️ サマリーの生成に失敗しました: {e}")
        return

    now = datetime.now(JST)
    header = (
        f"# 📅 【{group['name']}】週次サマリー"
        f" ({(now - timedelta(days=7)).strftime('%Y/%m/%d')} 〜 {now.strftime('%Y/%m/%d')})"
    )
    for chunk in [header + "\n\n" + summary[i:i+1800] for i in range(0, len(summary), 1800)]:
        await output_channel.send(chunk)


def reschedule_all():
    scheduler.remove_all_jobs()
    for group in cfg.get_groups():
        if not group.get("guild_id") or not group.get("output_channel_id"):
            continue
        gid = group["id"]
        scheduler.add_job(
            run_summary_for_group,
            CronTrigger(
                day_of_week=group["schedule_day"][:3].lower(),
                hour=group["schedule_hour"],
                minute=group["schedule_minute"],
                timezone="Asia/Tokyo",
            ),
            args=[group],
            id=gid,
            replace_existing=True,
        )
        log.info(f"Scheduled [{group['name']}]: {group['schedule_day']} {group['schedule_hour']:02d}:{group['schedule_minute']:02d} JST")


@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    reschedule_all()
    scheduler.start()
