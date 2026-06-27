import asyncio
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

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


def render(template_name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_jinja_env.get_template(template_name).render(**ctx))


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


def _guild_channels(bot) -> list[dict]:
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "channels": [{"id": str(c.id), "name": c.name} for c in g.text_channels],
        }
        for g in bot.guilds
    ]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _=Depends(verify)):
    bot = _get_bot()
    groups = cfg.get_groups()
    channel_map = {str(ch.id): ch.name for g in bot.guilds for ch in g.text_channels}
    return render("index.html", request=request, groups=groups, channel_map=channel_map)


@app.get("/groups/new", response_class=HTMLResponse)
async def group_new_form(request: Request, _=Depends(verify)):
    bot = _get_bot()
    group = cfg.new_group()
    return render("group_form.html",
        request=request,
        group=group,
        guilds_channels=_guild_channels(bot),
        is_new=True,
    )


@app.get("/groups/{group_id}/edit", response_class=HTMLResponse)
async def group_edit_form(group_id: str, request: Request, _=Depends(verify)):
    group = cfg.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404)
    bot = _get_bot()
    return render("group_form.html",
        request=request,
        group=group,
        guilds_channels=_guild_channels(bot),
        is_new=False,
    )


@app.post("/groups/save")
async def group_save(
    request: Request,
    _=Depends(verify),
    group_id: str = Form(...),
    name: str = Form(...),
    guild_id: str = Form(...),
    output_channel_id: str = Form(...),
    schedule_day: str = Form("monday"),
    schedule_hour: int = Form(9),
    schedule_minute: int = Form(0),
):
    form = await request.form()
    target_ids = form.getlist("target_channel_ids")

    group = cfg.get_group(group_id) or cfg.new_group()
    group.update({
        "id": group_id,
        "name": name,
        "guild_id": int(guild_id),
        "target_channel_ids": [int(i) for i in target_ids],
        "output_channel_id": int(output_channel_id),
        "schedule_day": schedule_day,
        "schedule_hour": schedule_hour,
        "schedule_minute": schedule_minute,
    })
    cfg.save_group(group)

    from bot.client import reschedule_all
    reschedule_all()

    return RedirectResponse("/?saved=1", status_code=303)


@app.post("/groups/{group_id}/delete")
async def group_delete(group_id: str, _=Depends(verify)):
    cfg.delete_group(group_id)
    from bot.client import reschedule_all
    reschedule_all()
    return RedirectResponse("/?deleted=1", status_code=303)


@app.post("/groups/{group_id}/run")
async def group_run(group_id: str, _=Depends(verify)):
    group = cfg.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404)
    from bot.client import run_summary_for_group
    asyncio.create_task(run_summary_for_group(group))
    return RedirectResponse("/?ran=1", status_code=303)
