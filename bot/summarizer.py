import os
from datetime import datetime, timedelta, timezone

import anthropic
import discord

JST = timezone(timedelta(hours=9))


async def collect_messages(channel: discord.TextChannel, since: datetime) -> list[str]:
    lines = []
    async for msg in channel.history(after=since, limit=2000, oldest_first=True):
        if msg.author.bot:
            continue
        ts = msg.created_at.astimezone(JST).strftime("%m/%d %H:%M")
        content = msg.content.replace("\n", " ")
        if content:
            lines.append(f"[{ts}] {msg.author.display_name}: {content}")
    return lines


async def generate_summary(channels_messages: dict[str, list[str]]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    sections = []
    for ch_name, lines in channels_messages.items():
        if not lines:
            continue
        sections.append(f"## #{ch_name}\n" + "\n".join(lines))

    if not sections:
        return "今週は対象チャンネルに投稿がありませんでした。"

    prompt = (
        "以下は先週1週間のDiscordチャンネルの投稿履歴です。\n"
        "以下の形式で日本語で要約してください。\n\n"
        "## 📋 振り返り\n"
        "- 主な出来事・議論・決定事項を箇条書きでまとめる\n\n"
        "## 📅 今後の予定\n"
        "- 投稿から読み取れる今後のタスク・イベント・予定を箇条書きでまとめる\n"
        "- 明確な予定が読み取れない場合は「記載なし」とする\n\n"
        "---\n"
        + "\n\n".join(sections)
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
