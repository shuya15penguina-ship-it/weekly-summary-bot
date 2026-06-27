import os
import secrets
from typing import Annotated

import discord
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jinja2 import Environment, FileSystemLoader

from bot import config as cfg

app = FastAPI()
security = HTTPBasic()
_jinja_env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=True,
)


def render(template_name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_jinja_env.get_template(template_name).render(**ctx))

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


def verify(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    ok = secrets.compare_digest(credentials.password.encode(), ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="パスワードが違います",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


def _get_bot():
    from bot.client import bot
    return bot


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _=Depends(verify)):
    bot = _get_bot()
    conf = cfg.load()

    guilds_channels: list[dict] = []
    for guild in bot.guilds:
        channels = [
            {"id": str(ch.id), "name": ch.name}
            for ch in guild.text_channels
        ]
        guilds_channels.append({"id": str(guild.id), "name": guild.name, "channels": channels})

    return render("index.html",
        request=request,
        guilds_channels=guilds_channels,
        conf=conf,
        selected_ids=[str(i) for i in conf.get("target_channel_ids", [])],
        output_channel_id=str(conf.get("output_channel_id") or ""),
        guild_id=str(conf.get("guild_id") or ""),
    )


@app.post("/save")
async def save(
    request: Request,
    _=Depends(verify),
    guild_id: str = Form(...),
    output_channel_id: str = Form(...),
    schedule_day: str = Form("monday"),
    schedule_hour: int = Form(9),
    schedule_minute: int = Form(0),
):
    form = await request.form()
    target_ids = form.getlist("target_channel_ids")

    conf = cfg.load()
    conf["guild_id"] = int(guild_id)
    conf["target_channel_ids"] = [int(i) for i in target_ids]
    conf["output_channel_id"] = int(output_channel_id)
    conf["schedule_day"] = schedule_day
    conf["schedule_hour"] = schedule_hour
    conf["schedule_minute"] = schedule_minute
    cfg.save(conf)

    from bot.client import reschedule_from_config
    reschedule_from_config()

    return RedirectResponse("/?saved=1", status_code=303)


@app.post("/run-now")
async def run_now(_=Depends(verify)):
    from bot.client import run_weekly_summary
    import asyncio
    asyncio.create_task(run_weekly_summary())
    return RedirectResponse("/?ran=1", status_code=303)
