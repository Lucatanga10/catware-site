# LIRIS Super Bot - single file
# Combines: General (welcome + anti-spam/phish), Giveaways, Tickets
# Usage: set DISCORD_TOKEN in environment, then: python super_bot.py

import os
import re
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Deque, Any, Set
import contextlib
import random
import io
import html

import sys
import types
# Safe stub for audioop on Python 3.13 where stdlib audioop is removed.
# discord.py may import audio-related modules even if voice is unused.
try:
    import audioop  # type: ignore
except Exception:
    sys.modules['audioop'] = types.ModuleType('audioop')

import discord
from discord import app_commands
from discord.ext import commands

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda: None  # type: ignore

# ---------- Config ----------
load_dotenv()
TOKEN = os.getenv("", "")
GUILD_ID: int | None = 1416381671883669640  # or None for global sync
GREEN = 0x23A55A
# Hosting config: bind to env HOST/PORT for PaaS (e.g., Render). Default to 0.0.0.0:8080
SITE_HOST = os.getenv("HOST", "0.0.0.0")
try:
    SITE_PORT = int(os.getenv("PORT", "8080"))
except ValueError:
    SITE_PORT = 8080
# Optional public URL override (e.g., https://your-domain.com); otherwise computed per-request
SITE_PUBLIC_URL = os.getenv("SITE_PUBLIC_URL", "").strip()
SITE_URL = f"http://{SITE_HOST}:{SITE_PORT}"
SERVE_SITE = True  # se True, ospita ./site come sito statico

# ---------- Bot ----------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)
_site_runner = None  # aiohttp runner

# Optional web server (aiohttp) for static green site
try:
    from aiohttp import web
except Exception:
    web = None  # type: ignore
try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # type: ignore

async def start_site_server():
    global _site_runner
    if not SERVE_SITE or web is None:
        return
    app = web.Application()
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
    os.makedirs(static_dir, exist_ok=True)
    # Root should serve index.html directly
    async def index_handler(_):
        return web.FileResponse(os.path.join(static_dir, "index.html"))
    app.router.add_get("/", index_handler)
    # Static fallback for all assets and deep links
    app.router.add_static("/", static_dir, show_index=False)

    # API: Stripe Checkout
    async def api_checkout(request: 'web.Request'):
        if stripe is None:
            return web.json_response({"error": "Stripe not installed. Run: pip install stripe"}, status=400)
        secret = os.getenv("STRIPE_SECRET_KEY", "")
        if not secret:
            return web.json_response({"error": "Missing STRIPE_SECRET_KEY env var."}, status=400)
        stripe.api_key = secret
        try:
            data = await request.json()
            items = data.get("items", [])
            currency = str(data.get("currency", "eur")).lower()
            if not (len(currency) == 3 and currency.isalpha()):
                currency = "eur"
            line_items = []
            for it in items:
                name = str(it.get("name", "Item"))
                price = float(it.get("price", 0))
                qty = int(it.get("quantity", 1))
                if price <= 0 or qty <= 0:
                    continue
                line_items.append({
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": name},
                        "unit_amount": int(round(price * 100)),
                    },
                    "quantity": qty,
                })
            if not line_items:
                return web.json_response({"error": "Empty cart"}, status=400)
            # Determine public base URL: prefer env override, else request origin
            if SITE_PUBLIC_URL:
                base = SITE_PUBLIC_URL.rstrip('/')
            else:
                try:
                    base = f"{request.scheme}://{request.host}"
                except Exception:
                    base = SITE_URL.rstrip('/')
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                success_url=f"{base}/checkout.html?status=success",
                cancel_url=f"{base}/cart.html?status=cancel",
            )
            return web.json_response({"url": session.url})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    app.router.add_post('/api/checkout', api_checkout)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, SITE_HOST, SITE_PORT)
    await site.start()
    _site_runner = runner
    print(f"[super-bot] Sito servito su {SITE_URL}")

# ---------- General: welcome + anti-spam/phish ----------
SUSPICIOUS_TLDS = {".ru", ".cn", ".tk", ".ml", ".ga", ".cf"}
PHISH_RE = re.compile(r"nitro\s*free|steam\s*giveaway|discord\s*gifts?|http[s]?://[^\s]*discord(?:-|)nitro", re.I)
URL_RE = re.compile(r"https?://[^\s]+", re.I)

class GeneralMem:
    def __init__(self) -> None:
        self.welcome_channel_id: Dict[int, int] = {}
        self.welcome_message: Dict[int, str] = {}
        self.brand_name: Dict[int, str] = defaultdict(lambda: "LIRIS")
        self.msg_times: Dict[tuple[int, int], Deque[float]] = defaultdict(lambda: deque(maxlen=10))
        self.whitelist: Dict[int, set[str]] = defaultdict(set)
        self.security_log_channel_id: Dict[int, int] = {}
        # Anti-raid
        self.raid_threshold: Dict[int, int] = defaultdict(lambda: 5)
        self.raid_window_sec: Dict[int, int] = defaultdict(lambda: 20)
        self.raid_slowmode_sec: Dict[int, int] = defaultdict(lambda: 10)
        self.join_times: Dict[int, Deque[float]] = defaultdict(lambda: deque(maxlen=50))
        # Welcome media
        self.welcome_banners: Dict[int, Set[str]] = defaultdict(set)

mem_g = GeneralMem()


def looks_suspicious(guild: discord.Guild, content: str) -> bool:
    for m in URL_RE.findall(content):
        host = re.sub(r"^https?://", "", m).split("/")[0].lower()
        if any(host.endswith(w) for w in mem_g.whitelist[guild.id]):
            return False
        if any(host.endswith(t) for t in SUSPICIOUS_TLDS):
            return True
    return bool(PHISH_RE.search(content))


class GeneralCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):  # type: ignore[override]
        ch_id = mem_g.welcome_channel_id.get(member.guild.id)
        if not ch_id:
            return
        ch = member.guild.get_channel(ch_id)
        if not isinstance(ch, discord.TextChannel):
            return
        brand = mem_g.brand_name[member.guild.id]
        e = discord.Embed(color=GREEN)
        e.title = f"Welcome {member.display_name}!"
        e.description = f"to {brand}!"
        try:
            e.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass
        msg = mem_g.welcome_message.get(member.guild.id)
        if msg:
            e.add_field(name="Message", value=msg, inline=False)
        # Optional banner image
        banners = mem_g.welcome_banners.get(member.guild.id)
        if banners:
            try:
                e.set_image(url=random.choice(list(banners)))
            except Exception:
                pass
        try:
            await ch.send(content=member.mention, embed=e)
        except discord.HTTPException:
            pass

        # Anti-raid: track joins and apply slowmode if threshold exceeded
        dq = mem_g.join_times[member.guild.id]
        now = datetime.now().timestamp()
        dq.append(now)
        window = mem_g.raid_window_sec[member.guild.id]
        threshold = mem_g.raid_threshold[member.guild.id]
        slowmode = mem_g.raid_slowmode_sec[member.guild.id]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= threshold:
            for tch in member.guild.text_channels:
                with contextlib.suppress(Exception):
                    await tch.edit(slowmode_delay=slowmode)
            log_id = mem_g.security_log_channel_id.get(member.guild.id)
            lch = member.guild.get_channel(log_id) if log_id else None
            if isinstance(lch, discord.TextChannel):
                emb = discord.Embed(title="Lockdown anti-raid", description=f"Join > {threshold} negli ultimi {window}s. Slowmode {slowmode}s attivata.", color=GREEN)
                emb.timestamp = datetime.now(timezone.utc)
                with contextlib.suppress(discord.HTTPException):
                    await lch.send(embed=emb)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot or not msg.guild:
            return
        now = datetime.now().timestamp()
        key = (msg.guild.id, msg.author.id)
        dq = mem_g.msg_times[key]
        dq.append(now)
        mem_g.msg_times[key] = deque([t for t in dq if now - t <= 5], maxlen=10)
        if len(mem_g.msg_times[key]) >= 5:
            with contextlib.suppress(discord.HTTPException):
                await msg.delete()
            with contextlib.suppress(discord.HTTPException):
                await msg.channel.send(f"{msg.author.mention} per favore, non spammare.", delete_after=5)
            return
        if looks_suspicious(msg.guild, msg.content):
            with contextlib.suppress(discord.HTTPException):
                await msg.delete()
            ch_id = mem_g.security_log_channel_id.get(msg.guild.id)
            ch = msg.guild.get_channel(ch_id) if ch_id else None
            if isinstance(ch, discord.TextChannel):
                e = discord.Embed(title="Messaggio sospetto rimosso", description=msg.content[:1000], color=GREEN)
                e.add_field(name="Autore", value=f"{msg.author} ({msg.author.id})")
                e.add_field(name="Canale", value=msg.channel.mention)
                e.timestamp = datetime.now(timezone.utc)
                with contextlib.suppress(discord.HTTPException):
                    await ch.send(embed=e)

    @app_commands.command(name="welcome_setup", description="Imposta canale (e messaggio) di benvenuto")
    @app_commands.describe(channel="Canale benvenuto", message="Messaggio opzionale")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_setup(self, itx: discord.Interaction, channel: discord.TextChannel, message: Optional[str] = None):
        assert itx.guild is not None
        mem_g.welcome_channel_id[itx.guild.id] = channel.id
        if message:
            mem_g.welcome_message[itx.guild.id] = message
        e = discord.Embed(title="Welcome configurato", description=f"Canale: {channel.mention}\nMessaggio: {message or '—'}", color=GREEN)
        await itx.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="brand_welcome", description="Imposta nome brand per welcome")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def brand_welcome(self, itx: discord.Interaction, name: str):
        assert itx.guild is not None
        mem_g.brand_name[itx.guild.id] = name
        await itx.response.send_message(f"Brand impostato a: {name}", ephemeral=True)

    @app_commands.command(name="security_setup", description="Imposta canale log sicurezza")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def security_setup(self, itx: discord.Interaction, log_channel: discord.TextChannel):
        assert itx.guild is not None
        mem_g.security_log_channel_id[itx.guild.id] = log_channel.id
        await itx.response.send_message(f"Log canale: {log_channel.mention}", ephemeral=True)

    @app_commands.command(name="antiraid_setup", description="Configura anti-raid (soglia, finestra, slowmode)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def antiraid_setup(self, itx: discord.Interaction, threshold: int = 5, window: int = 20, slowmode: int = 10):
        assert itx.guild is not None
        mem_g.raid_threshold[itx.guild.id] = int(threshold)
        mem_g.raid_window_sec[itx.guild.id] = int(window)
        mem_g.raid_slowmode_sec[itx.guild.id] = int(slowmode)
        e = discord.Embed(title="Anti-raid configurato", description=f"Soglia: {threshold}\nFinestra: {window}s\nSlowmode: {slowmode}s", color=GREEN)
        await itx.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="lockdown", description="Abilita/Disabilita slowmode globale")
    @app_commands.describe(state="on/off")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def lockdown(self, itx: discord.Interaction, state: str):
        assert itx.guild is not None
        state = state.lower().strip()
        if state not in {"on", "off"}:
            return await itx.response.send_message("Usa on/off.", ephemeral=True)
        delay = mem_g.raid_slowmode_sec[itx.guild.id] if state == "on" else 0
        count = 0
        for ch in itx.guild.text_channels:
            with contextlib.suppress(Exception):
                await ch.edit(slowmode_delay=delay)
                count += 1
        e = discord.Embed(title="Lockdown", description=f"Stato: {state.upper()} — Canali aggiornati: {count}", color=GREEN)
        await itx.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="whitelist_domain", description="Gestisci whitelist domini consentiti")
    @app_commands.describe(action="add/remove", domain="es. example.com")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist_domain(self, itx: discord.Interaction, action: str, domain: str):
        assert itx.guild is not None
        action = action.lower().strip()
        domain = domain.lower().strip()
        if action not in {"add", "remove"}:
            return await itx.response.send_message("Azione non valida.", ephemeral=True)
        if action == "add":
            mem_g.whitelist[itx.guild.id].add(domain)
        else:
            mem_g.whitelist[itx.guild.id].discard(domain)
        await itx.response.send_message(f"Whitelist {action}: {domain}", ephemeral=True)

    @app_commands.command(name="security_status", description="Mostra stato sicurezza")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def security_status(self, itx: discord.Interaction):
        assert itx.guild is not None
        wl = ", ".join(sorted(mem_g.whitelist[itx.guild.id])) or "—"
        e = discord.Embed(
            title="Sicurezza",
            description=(
                f"Whitelist: {wl}\n"
                f"Soglia anti-raid: {mem_g.raid_threshold[itx.guild.id]} in {mem_g.raid_window_sec[itx.guild.id]}s\n"
                f"Slowmode: {mem_g.raid_slowmode_sec[itx.guild.id]}s"
            ),
            color=GREEN,
        )
        await itx.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="welcome_media", description="Gestisci GIF/immagini per il welcome")
    @app_commands.describe(action="add/remove", url="URL immagine/GIF")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_media(self, itx: discord.Interaction, action: str, url: str):
        assert itx.guild is not None
        action = action.lower().strip()
        if action not in {"add", "remove"}:
            return await itx.response.send_message("Usa add/remove.", ephemeral=True)
        if action == "add":
            mem_g.welcome_banners[itx.guild.id].add(url)
        else:
            mem_g.welcome_banners[itx.guild.id].discard(url)
        urls = ", ".join(mem_g.welcome_banners[itx.guild.id]) or "—"
        e = discord.Embed(title="Welcome media", description=f"Azione: {action}\nLista: {urls}", color=GREEN)
        await itx.response.send_message(embed=e, ephemeral=True)

# ---------- Giveaways ----------
class JoinView(discord.ui.View):
    def __init__(self, gw_id: int):
        super().__init__(timeout=None)
        self.gw_id = gw_id

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, emoji="🎉", custom_id="gw:join")
    async def join(self, itx: discord.Interaction, button: discord.ui.Button):  # type: ignore[override]
        gw = mem_gw.get(self.gw_id)
        if not gw or gw.get("closed"):
            return await itx.response.send_message("Giveaway non attivo.", ephemeral=True)
        parts: Set[int] = gw.setdefault("participants", set())  # type: ignore[assignment]
        if itx.user.id in parts:
            return await itx.response.send_message("Sei già iscritto.", ephemeral=True)
        parts.add(itx.user.id)
        await itx.response.send_message("Sei dentro! 🍀", ephemeral=True)
        await update_gw_message(bot, self.gw_id)

    @discord.ui.button(label="Esci", style=discord.ButtonStyle.secondary, emoji="🚪", custom_id="gw:leave")
    async def leave(self, itx: discord.Interaction, button: discord.ui.Button):  # type: ignore[override]
        gw = mem_gw.get(self.gw_id)
        if not gw:
            return await itx.response.send_message("Giveaway non attivo.", ephemeral=True)
        parts: Set[int] = gw.setdefault("participants", set())  # type: ignore[assignment]
        if itx.user.id in parts:
            parts.remove(itx.user.id)
            await itx.response.send_message("Hai lasciato il giveaway.", ephemeral=True)
            await update_gw_message(bot, self.gw_id)
        else:
            await itx.response.send_message("Non risulti iscritto.", ephemeral=True)

    @discord.ui.button(label="Partecipanti", style=discord.ButtonStyle.success, emoji="🧑\u200d🤝\u200d🧑", custom_id="gw:list")
    async def show_participants(self, itx: discord.Interaction, button: discord.ui.Button):  # type: ignore[override]
        gw = mem_gw.get(self.gw_id)
        if not gw:
            return await itx.response.send_message("Giveaway non attivo.", ephemeral=True)
        parts: Set[int] = set(gw.get("participants", set()))
        count = len(parts)
        if count == 0:
            return await itx.response.send_message("Nessun partecipante ancora.", ephemeral=True)
        ids = list(parts)[:50]
        mentions = ", ".join(f"<@{i}>" for i in ids)
        more = f"\n… e altri {count-50}" if count > 50 else ""
        await itx.response.send_message(f"Partecipanti ({count}):\n{mentions}{more}", ephemeral=True, allowed_mentions=discord.AllowedMentions(users=False))

mem_gw: Dict[int, Dict[str, Any]] = {}
last_gw_by_guild: Dict[int, int] = {}
gw_brand_name: Dict[int, str] = {}
gw_brand_icon: Dict[int, Optional[str]] = {}

def build_giveaway_embed(guild: discord.Guild, gw: Dict[str, Any]) -> discord.Embed:
    end_at: datetime = gw["end_at"]
    prize: str = gw.get("prize", "")
    winners: int = gw.get("winners", 1)
    host_id: int = gw.get("host_id")
    participants = gw.get("participants", set())
    e = discord.Embed(title="🎉 Giveaway", color=GREEN)
    name = gw_brand_name.get(guild.id)
    icon = gw_brand_icon.get(guild.id)
    if name and icon:
        e.set_author(name=name, icon_url=icon)
    elif name:
        e.set_author(name=name)
    e.description = (
        f"Premio: **{prize}**\n"
        f"Vincitori: **{winners}**\n"
        f"Termina {discord.utils.format_dt(end_at, style='R')}\n"
        f"Host: <@{host_id}>\n"
        f"Partecipanti: **{len(participants)}**"
    )
    e.set_footer(text="Premi Join per partecipare")
    return e

async def update_gw_message(bot: commands.Bot, gw_id: int) -> None:
    gw = mem_gw.get(gw_id)
    if not gw:
        return
    ch = bot.get_channel(gw["channel_id"])  # type: ignore[arg-type]
    if not isinstance(ch, discord.TextChannel):
        return
    try:
        msg = await ch.fetch_message(gw_id)
    except discord.NotFound:
        return
    embed = build_giveaway_embed(ch.guild, gw)
    await msg.edit(embed=embed, view=None if gw.get("closed") else JoinView(gw_id))

class GiveawayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gstart", description="Avvia un giveaway")
    @app_commands.describe(prize="Premio", duration="Esempi: 60s, 10m, 2h, 1d", winners="# vincitori", channel="Canale")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def gstart(self, itx: discord.Interaction, prize: str, duration: str, winners: Optional[int] = 1, channel: Optional[discord.TextChannel] = None):
        assert itx.guild is not None
        try:
            seconds = parse_duration(duration)
        except ValueError as e:
            return await itx.response.send_message(str(e), ephemeral=True)
        winners = max(1, int(winners or 1))
        target = channel or itx.channel
        if not isinstance(target, discord.TextChannel):
            return await itx.response.send_message("Specifica un canale valido.", ephemeral=True)
        end_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        e = discord.Embed(title="🎉 Giveaway", color=GREEN)
        e.description = f"Premio: **{prize}**\nVincitori: **{winners}**\nTermina {discord.utils.format_dt(end_at, style='R')}\nHost: {itx.user.mention}"
        e.set_footer(text="Premi Join per partecipare")
        await itx.response.defer(ephemeral=True)
        msg = await target.send(embed=e)
        gw_id = msg.id
        mem_gw[gw_id] = {
            "guild_id": itx.guild.id,
            "channel_id": target.id,
            "end_at": end_at,
            "prize": prize,
            "winners": winners,
            "host_id": itx.user.id,
            "participants": set(),
            "closed": False,
        }
        last_gw_by_guild[itx.guild.id] = gw_id
        await msg.edit(view=JoinView(gw_id))
        await itx.followup.send(f"Giveaway creato in {target.mention}", ephemeral=True)
        asyncio.create_task(self._schedule_end(gw_id))
        # auto update participants count every 2 minutes
        t = asyncio.create_task(self._auto_update_count(gw_id))
        mem_gw[gw_id]["auto_task"] = t

    async def _schedule_end(self, gw_id: int):
        gw = mem_gw.get(gw_id)
        if not gw:
            return
        delay = (gw["end_at"] - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
        await self._end_giveaway(gw_id)

    async def _end_giveaway(self, gw_id: int):
        gw = mem_gw.get(gw_id)
        if not gw:
            return
        # stop auto task
        t: Optional[asyncio.Task] = gw.get("auto_task")  # type: ignore[assignment]
        if t and not t.done():
            t.cancel()
        ch = self.bot.get_channel(gw["channel_id"])  # type: ignore[arg-type]
        if not isinstance(ch, discord.TextChannel):
            return
        try:
            msg = await ch.fetch_message(gw_id)
        except discord.NotFound:
            msg = None
        parts: Set[int] = set(gw.get("participants", set()))
        winners = gw.get("winners", 1)
        prize = gw.get("prize", "")
        if parts:
            chosen = random.sample(list(parts), k=min(winners, len(parts)))
            mentions = " ".join(f"<@{w}>" for w in chosen)
            await ch.send(embed=discord.Embed(title="Giveaway terminato", description=f"Premio: **{prize}**\nVincitore/i: {mentions}", color=GREEN))
            gw["last_winners"] = chosen
        else:
            await ch.send(embed=discord.Embed(title="Giveaway terminato", description=f"Premio: **{prize}**\nNessun partecipante.", color=GREEN))
        gw["closed"] = True
        if msg:
            with contextlib.suppress(discord.HTTPException):
                await msg.edit(view=None)

    async def _auto_update_count(self, gw_id: int):
        while True:
            gw = mem_gw.get(gw_id)
            if not gw or gw.get("closed"):
                return
            await asyncio.sleep(120)
            with contextlib.suppress(Exception):
                await update_gw_message(self.bot, gw_id)

    @app_commands.command(name="gend", description="Termina subito un giveaway (ultimo se vuoto)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def gend(self, itx: discord.Interaction, message_id: Optional[str] = None):
        assert itx.guild is not None
        if message_id is None:
            gw_id = last_gw_by_guild.get(itx.guild.id)
            if not gw_id:
                return await itx.response.send_message("Nessun giveaway trovato.", ephemeral=True)
        else:
            try:
                gw_id = int(message_id)
            except ValueError:
                return await itx.response.send_message("ID non valido.", ephemeral=True)
        await itx.response.defer(ephemeral=True)
        await self._end_giveaway(gw_id)
        await itx.followup.send("Giveaway terminato.", ephemeral=True)

    @app_commands.command(name="greroll", description="Estrai nuovi vincitori da un giveaway chiuso")
    @app_commands.describe(message_id="ID messaggio del giveaway", winners="Numero nuovi vincitori")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greroll(self, itx: discord.Interaction, message_id: str, winners: Optional[int] = None):
        try:
            gw_id = int(message_id)
        except ValueError:
            return await itx.response.send_message("ID non valido.", ephemeral=True)
        gw = mem_gw.get(gw_id)
        if not gw:
            return await itx.response.send_message("Giveaway non trovato.", ephemeral=True)
        parts: Set[int] = set(gw.get("participants", set()))
        if not parts:
            return await itx.response.send_message("Nessun partecipante per il reroll.", ephemeral=True)
        winners_count = int(winners) if winners is not None else int(gw.get("winners", 1))
        winners_count = max(1, winners_count)
        chosen = random.sample(list(parts), k=min(winners_count, len(parts)))
        mentions = " ".join(f"<@{w}>" for w in chosen)
        ch = self.bot.get_channel(gw["channel_id"])  # type: ignore[arg-type]
        if isinstance(ch, discord.TextChannel):
            e = discord.Embed(title="🎉 Reroll", description=f"Premio: **{gw['prize']}**\nVincitore/i: {mentions}", color=GREEN)
            await ch.send(embed=e, allowed_mentions=discord.AllowedMentions(users=True))
        await itx.response.send_message("Reroll completato.", ephemeral=True)

    @app_commands.command(name="brand_setup", description="Imposta brand per gli embed dei giveaway")
    @app_commands.describe(name="Nome brand", icon_url="URL icona (opzionale)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def brand_setup(self, itx: discord.Interaction, name: str, icon_url: Optional[str] = None):
        assert itx.guild is not None
        gw_brand_name[itx.guild.id] = name
        gw_brand_icon[itx.guild.id] = icon_url
        e = discord.Embed(title="Brand aggiornato", description=f"Nome: {name}\nIcona: {icon_url or '—'}", color=GREEN)
        await itx.response.send_message(embed=e, ephemeral=True)

# --- duration parser ---
TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

def parse_duration(s: str) -> int:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    total = 0
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        else:
            if ch not in TIME_UNITS or not num:
                raise ValueError("Formato durata non valido (es: 60s, 10m, 2h, 1d)")
            total += int(num) * TIME_UNITS[ch]
            num = ""
    if num:
        total += int(num)
    if total <= 0:
        raise ValueError("Durata deve essere > 0")
    return total

# ---------- Site Cog (/site) ----------
class SiteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="site", description="Invia il link al sito del server (tema verde)")
    async def site_cmd(self, itx: discord.Interaction):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Apri Sito", style=discord.ButtonStyle.link, url=SITE_URL, emoji="🌐"))
        e = discord.Embed(title="Sito del Server", description=f"Clicca per aprire il sito\nURL: {SITE_URL}", color=GREEN)
        await itx.response.send_message(embed=e, view=view, ephemeral=False)

    @app_commands.command(name="site_setup", description="Imposta l'URL del sito per /site")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def site_setup(self, itx: discord.Interaction, url: str):
        global SITE_URL
        SITE_URL = url
        await itx.response.send_message(f"URL aggiornato: {SITE_URL}", ephemeral=True)

# ---------- Tickets ----------
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _create_ticket(self, itx: discord.Interaction, kind: str):
        assert itx.guild is not None
        staff_role_id = get_conf(itx.guild.id, "staff_role_id")
        category_id = get_conf(itx.guild.id, "tickets_category_id")
        if not staff_role_id or not category_id:
            return await itx.response.send_message("Esegui prima /ticket_setup.", ephemeral=True)
        staff = itx.guild.get_role(int(staff_role_id))
        category = itx.guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel) or not staff:
            return await itx.response.send_message("Configurazione ticket non valida.", ephemeral=True)
        overwrites = {
            itx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            itx.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            staff: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True),
        }
        ch = await itx.guild.create_text_channel(name=f"ticket-{kind}-{itx.user.name}", category=category, overwrites=overwrites, reason="Create ticket")
        e = discord.Embed(title=f"Ticket {kind.upper()}", description=f"Ciao {itx.user.mention}!", color=GREEN)
        view = TicketManageView(opener_id=itx.user.id)
        await ch.send(content=f"{itx.user.mention} {staff.mention}", embed=e, view=view)
        await itx.response.send_message(f"Ticket creato: {ch.mention}", ephemeral=True)
        # stats & logs
        inc_ticket_stat(itx.guild.id, "created", 1)
        await log_ticket_event(itx.guild, "🟢 Ticket creato", f"{ch.mention} — {kind.upper()} — utente: {itx.user.mention}")

    @discord.ui.button(label="Buy", style=discord.ButtonStyle.success, emoji="🛒", custom_id="ticket:create:buy")
    async def create_buy(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        await self._create_ticket(itx, "buy")

    @discord.ui.button(label="Support", style=discord.ButtonStyle.success, emoji="🛠", custom_id="ticket:create:support")
    async def create_support(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        await self._create_ticket(itx, "support")

class TicketManageView(discord.ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="🧰", custom_id="ticket:claim")
    async def claim(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        if not itx.guild or not isinstance(itx.channel, discord.TextChannel):
            return
        srole = staff_role(itx.guild)
        member = itx.user
        if srole and srole not in getattr(member, 'roles', []):
            return await itx.response.send_message("Solo lo staff può claimare.", ephemeral=True)
        topic = itx.channel.topic or ""
        if topic.startswith("CLAIMED:"):
            # unclaim
            await itx.channel.edit(topic=None)
            await itx.response.send_message("✅ Ticket unclaimed.", ephemeral=True)
        else:
            new_topic = f"CLAIMED: {member.display_name} ({member.id})"
            await itx.channel.edit(topic=new_topic)
            await itx.response.send_message(f"✅ Ticket claimato da {member.mention}.", ephemeral=True)
            inc_ticket_stat(itx.guild.id, "claimed", 1)
            await log_ticket_event(itx.guild, "🧰 Ticket claimato", f"{itx.channel.mention} da {member.mention}")

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket:add")
    async def add_user(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        if not itx.guild:
            return
        srole = staff_role(itx.guild)
        if srole and srole not in getattr(itx.user, 'roles', []):
            return await itx.response.send_message("Solo lo staff può aggiungere utenti.", ephemeral=True)
        await itx.response.send_modal(AddRemoveUserModal(add=True))

    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.secondary, emoji="➖", custom_id="ticket:remove")
    async def remove_user(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        if not itx.guild:
            return
        srole = staff_role(itx.guild)
        if srole and srole not in getattr(itx.user, 'roles', []):
            return await itx.response.send_message("Solo lo staff può rimuovere utenti.", ephemeral=True)
        await itx.response.send_modal(AddRemoveUserModal(add=False))

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.primary, emoji="🧾", custom_id="ticket:transcript")
    async def transcript(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        if not isinstance(itx.channel, discord.TextChannel):
            return
        await itx.response.send_message("⏳ Genero il transcript...", ephemeral=True)
        messages = [m async for m in itx.channel.history(limit=500, oldest_first=True)]
        # simple HTML transcript
        rows = []
        for m in messages:
            ts = m.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            author = html.escape(m.author.display_name)
            content = html.escape(m.content or "")
            rows.append(f"<div><b>{author}</b> <small>{ts}</small><div>{content}</div></div>")
        html_doc = """<html><head><meta charset='utf-8'><title>Transcript</title></head><body>{}</body></html>""".format("\n".join(rows))
        file = discord.File(fp=io.BytesIO(html_doc.encode("utf-8")), filename=f"transcript-{itx.channel.name}.html")
        await itx.followup.send(file=file, ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket:close")
    async def close(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        if not itx.guild or not isinstance(itx.channel, discord.TextChannel):
            return
        # conferma
        view = ConfirmCloseView()
        embed = discord.Embed(title="Confermi la chiusura del ticket?", color=GREEN)
        await itx.response.send_message(embed=embed, view=view, ephemeral=True)
        timeout = await view.wait()
        confirmed = getattr(view, "value", False)
        if timeout or not confirmed:
            return
        ch = itx.channel
        # tenta eliminazione
        with contextlib.suppress(discord.HTTPException):
            await ch.delete(reason="Ticket chiuso")
            inc_ticket_stat(itx.guild.id, "closed", 1)
            await log_ticket_event(itx.guild, "🔒 Ticket chiuso", f"Canale eliminato: #{getattr(ch, 'name', '?')}")

# --- simple per-guild config for tickets (in-memory minimal) ---
_ticket_conf: Dict[int, Dict[str, int]] = defaultdict(dict)

def set_conf(gid: int, key: str, value: int) -> None:
    _ticket_conf[gid][key] = value

def get_conf(gid: int, key: str) -> Optional[int]:
    return _ticket_conf.get(gid, {}).get(key)

class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket_setup", description="Imposta ruolo staff e categoria per i ticket")
    async def ticket_setup(self, itx: discord.Interaction, staff_role: discord.Role, category: Optional[discord.CategoryChannel] = None):
        assert itx.guild is not None
        set_conf(itx.guild.id, "staff_role_id", staff_role.id)
        if category is None:
            category = await itx.guild.create_category("Tickets")
        set_conf(itx.guild.id, "tickets_category_id", category.id)
        await itx.response.send_message(f"OK. Staff: {staff_role.mention}, Categoria: {category.mention}", ephemeral=True)

    @app_commands.command(name="ticket_panel", description="Invia il pannello create ticket")
    async def ticket_panel(self, itx: discord.Interaction):
        assert itx.channel and isinstance(itx.channel, discord.TextChannel)
        e = discord.Embed(title="Crea un ticket", description="Scegli il tipo di ticket:", color=GREEN)
        await itx.response.send_message("Pannello inviato", ephemeral=True)
        await itx.channel.send(embed=e, view=TicketPanelView())

    @app_commands.command(name="ticket_logs", description="Imposta il canale dove inviare i log dei ticket")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_logs(self, itx: discord.Interaction, channel: discord.TextChannel):
        assert itx.guild is not None
        set_conf(itx.guild.id, "logs_channel_id", channel.id)
        await itx.response.send_message(f"Canale log: {channel.mention}", ephemeral=True)

    @app_commands.command(name="ticket_stats", description="Mostra statistiche dei ticket per questo server")
    async def ticket_stats(self, itx: discord.Interaction):
        assert itx.guild is not None
        s = get_ticket_stats(itx.guild.id)
        open_count = max(0, s["created"] - s["closed"])
        e = discord.Embed(title="Statistiche Ticket", color=GREEN)
        e.add_field(name="Creati", value=str(s["created"]))
        e.add_field(name="Chiusi", value=str(s["closed"]))
        e.add_field(name="Claimed", value=str(s["claimed"]))
        e.add_field(name="Aperti", value=str(open_count), inline=False)
        await itx.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="staff_panel", description="Mostra pannello staff con azioni utili")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def staff_panel(self, itx: discord.Interaction, public: Optional[bool] = False):
        assert itx.guild is not None
        view = StaffPanelView()
        e = build_ticket_stats_embed(itx.guild.id)
        if public:
            await itx.response.send_message(embed=e, view=view, ephemeral=False)
            with contextlib.suppress(Exception):
                view.message = await itx.original_response()
        else:
            await itx.response.send_message(embed=e, view=view, ephemeral=True)
            with contextlib.suppress(Exception):
                view.message = await itx.original_response()

# -------- Ticket helpers advanced --------
def staff_role(guild: discord.Guild) -> Optional[discord.Role]:
    rid = get_conf(guild.id, "staff_role_id")
    return guild.get_role(int(rid)) if rid else None

def tickets_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    cid = get_conf(guild.id, "tickets_category_id")
    ch = guild.get_channel(int(cid)) if cid else None
    return ch if isinstance(ch, discord.CategoryChannel) else None

async def log_ticket_event(guild: discord.Guild, title: str, description: str) -> None:
    cid = get_conf(guild.id, "logs_channel_id")
    ch = guild.get_channel(int(cid)) if cid else None
    if isinstance(ch, discord.TextChannel):
        with contextlib.suppress(discord.HTTPException):
            e = discord.Embed(title=title, description=description, color=GREEN)
            e.timestamp = datetime.now(timezone.utc)
            await ch.send(embed=e)

_ticket_stats: Dict[int, Dict[str, int]] = defaultdict(lambda: {"created": 0, "closed": 0, "claimed": 0})

def inc_ticket_stat(gid: int, key: str, amount: int = 1):
    s = _ticket_stats[gid]
    s[key] = int(s.get(key, 0)) + amount
    _ticket_stats[gid] = s

def get_ticket_stats(gid: int) -> Dict[str, int]:
    return {k: int(v) for k, v in _ticket_stats[gid].items()}

def build_ticket_stats_embed(gid: int) -> discord.Embed:
    s = get_ticket_stats(gid)
    open_count = max(0, s["created"] - s["closed"])
    e = discord.Embed(title="Statistiche Ticket", color=GREEN)
    e.add_field(name="Creati", value=str(s["created"]))
    e.add_field(name="Chiusi", value=str(s["closed"]))
    e.add_field(name="Claimed", value=str(s["claimed"]))
    e.add_field(name="Aperti", value=str(open_count), inline=False)
    return e

class StaffPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.message: Optional[discord.Message] = None
        self.auto_task: Optional[asyncio.Task] = None

    async def on_timeout(self) -> None:
        if self.auto_task and not self.auto_task.done():
            self.auto_task.cancel()

    @discord.ui.button(label="Aggiorna stats", style=discord.ButtonStyle.success, emoji="📊")
    async def refresh(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        assert itx.guild is not None
        e = build_ticket_stats_embed(itx.guild.id)
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(embed=e, view=self)
        else:
            await itx.response.send_message(embed=e, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="Conferma chiusura", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        await itx.response.defer()
        self.stop()
        self.value = True  # type: ignore[attr-defined]

    @discord.ui.button(label="Annulla", style=discord.ButtonStyle.secondary)
    async def cancel(self, itx: discord.Interaction, _: discord.ui.Button):  # type: ignore[override]
        await itx.response.defer(ephemeral=True)
        self.stop()
        self.value = False  # type: ignore[attr-defined]

class AddRemoveUserModal(discord.ui.Modal, title="Gestisci accesso utente"):
    user_id = discord.ui.TextInput(label="User ID", placeholder="Inserisci l'ID utente", required=True)

    def __init__(self, add: bool):
        super().__init__()
        self.add = add

    async def on_submit(self, itx: discord.Interaction) -> None:  # type: ignore[override]
        assert itx.guild and isinstance(itx.channel, discord.TextChannel)
        try:
            uid = int(self.user_id.value)
        except ValueError:
            return await itx.response.send_message("ID non valido.", ephemeral=True)
        member = itx.guild.get_member(uid)
        if not member:
            return await itx.response.send_message("Utente non trovato nel server.", ephemeral=True)
        if self.add:
            await itx.channel.set_permissions(member, view_channel=True, send_messages=True)
            await itx.response.send_message(f"Aggiunto {member.mention} al ticket.", ephemeral=True)
        else:
            await itx.channel.set_permissions(member, overwrite=None)
            await itx.response.send_message(f"Rimosso {member.mention} dal ticket.", ephemeral=True)

# Extend TicketManageView with Claim/Add/Remove buttons

# ---------- Setup & run ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({getattr(bot.user, 'id', '?')})")

@bot.event
async def setup_hook():  # type: ignore[override]
    await bot.add_cog(GeneralCog(bot))
    await bot.add_cog(GiveawayCog(bot))
    await bot.add_cog(TicketsCog(bot))
    await bot.add_cog(SiteCog(bot))
    await start_site_server()
    # persistent views
    bot.add_view(JoinView(0))
    bot.add_view(TicketPanelView())
    bot.add_view(TicketManageView(0))
    if GUILD_ID:
        g = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=g)
        await bot.tree.sync(guild=g)
    else:
        await bot.tree.sync()

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN non impostato. Aggiungilo all'ambiente.")
    bot.run(TOKEN)
