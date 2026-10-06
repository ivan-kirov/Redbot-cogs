import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red

try:
    import gspread
    from google.oauth2.service_account import Credentials as GCredentials
except ImportError:  # sheet sync is optional until requirements.txt is installed
    gspread = None
    GCredentials = None

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_HEADER = [
    "Discord ID",
    "Discord Name",
    "Main Class",
    "Main Role",
    "Main Spec",
    "Secondary Class",
    "Secondary Role",
    "Secondary Spec",
    "Last Updated",
]

ROLE_EMOJI = {"Tank": "🛡️", "Healer": "💚", "DPS": "⚔️"}

# class -> [(spec, role), ...]
WOW_DATA = {
    "Druid": [("Balance", "DPS"), ("Feral", "DPS"), ("Guardian", "Tank"), ("Restoration", "Healer")],
    "Hunter": [("Beast Mastery", "DPS"), ("Marksmanship", "DPS"), ("Survival", "DPS")],
    "Mage": [("Arcane", "DPS"), ("Fire", "DPS"), ("Frost", "DPS")],
    "Monk": [("Brewmaster", "Tank"), ("Mistweaver", "Healer"), ("Windwalker", "DPS")],
    "Paladin": [("Holy", "Healer"), ("Protection", "Tank"), ("Retribution", "DPS")],
    "Priest": [("Discipline", "Healer"), ("Holy", "Healer"), ("Shadow", "DPS")],
    "Rogue": [("Assassination", "DPS"), ("Outlaw", "DPS"), ("Subtlety", "DPS")],
    "Shaman": [("Elemental", "DPS"), ("Enhancement", "DPS"), ("Restoration", "Healer")],
    "Warlock": [("Affliction", "DPS"), ("Demonology", "DPS"), ("Destruction", "DPS")],
    "Warrior": [("Arms", "DPS"), ("Fury", "DPS"), ("Protection", "Tank")],
}


def roles_for_class(cls: str):
    seen = []
    for _spec, role in WOW_DATA[cls]:
        if role not in seen:
            seen.append(role)
    return seen


def specs_for_class_role(cls: str, role: str):
    return [spec for spec, r in WOW_DATA[cls] if r == role]


# --------------------------------------------------------------------------- #
# Selection flow (Class -> Role -> Spec), reused for "main" and "secondary"
# --------------------------------------------------------------------------- #


class ClassSelect(discord.ui.Select):
    def __init__(self, parent: "SetupView"):
        options = [discord.SelectOption(label=c) for c in WOW_DATA]
        super().__init__(placeholder="Choose a class...", options=options, custom_id="wowroster_class_select")
        self.setup_view = parent

    async def callback(self, interaction: discord.Interaction):
        self.setup_view.chosen_class = self.values[0]
        self.setup_view.chosen_role = None
        self.setup_view.chosen_spec = None
        await self.setup_view.show_role_step(interaction)


class RoleSelect(discord.ui.Select):
    def __init__(self, parent: "SetupView"):
        options = [
            discord.SelectOption(label=role, emoji=ROLE_EMOJI.get(role))
            for role in roles_for_class(parent.chosen_class)
        ]
        super().__init__(placeholder="Choose a role...", options=options, custom_id="wowroster_role_select")
        self.setup_view = parent

    async def callback(self, interaction: discord.Interaction):
        self.setup_view.chosen_role = self.values[0]
        self.setup_view.chosen_spec = None
        await self.setup_view.show_spec_step(interaction)


class SpecSelect(discord.ui.Select):
    def __init__(self, parent: "SetupView"):
        specs = specs_for_class_role(parent.chosen_class, parent.chosen_role)
        options = [discord.SelectOption(label=s) for s in specs]
        super().__init__(placeholder="Choose a spec...", options=options, custom_id="wowroster_spec_select")
        self.setup_view = parent

    async def callback(self, interaction: discord.Interaction):
        self.setup_view.chosen_spec = self.values[0]
        await self.setup_view.show_confirm_step(interaction)


class BackCancelRow(discord.ui.View):
    """Small helper mixed into each step so the user isn't stuck."""


class SetupView(discord.ui.View):
    """Ephemeral, per-user view driving Class -> Role -> Spec -> Save."""

    def __init__(self, cog: "WowRoster", slot: str, member: discord.Member):
        super().__init__(timeout=180)
        self.cog = cog
        self.slot = slot  # "main" or "secondary"
        self.member = member
        self.chosen_class: Optional[str] = None
        self.chosen_role: Optional[str] = None
        self.chosen_spec: Optional[str] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This isn't your setup menu.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    def _reset_items(self):
        self.clear_items()

    async def show_class_step(self, interaction: discord.Interaction, first: bool = False):
        self._reset_items()
        self.add_item(ClassSelect(self))
        self.add_item(self._cancel_button())
        embed = discord.Embed(
            title=f"Set {self.slot.capitalize()} Spec",
            description="Step 1/3 — pick your class.",
            color=discord.Color.blurple(),
        )
        if first:
            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def show_role_step(self, interaction: discord.Interaction):
        self._reset_items()
        self.add_item(RoleSelect(self))
        self.add_item(self._cancel_button())
        embed = discord.Embed(
            title=f"Set {self.slot.capitalize()} Spec",
            description=f"Step 2/3 — **{self.chosen_class}**. Now pick a role.",
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_spec_step(self, interaction: discord.Interaction):
        self._reset_items()
        self.add_item(SpecSelect(self))
        self.add_item(self._cancel_button())
        embed = discord.Embed(
            title=f"Set {self.slot.capitalize()} Spec",
            description=f"Step 3/3 — **{self.chosen_class} / {self.chosen_role}**. Now pick a spec.",
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_confirm_step(self, interaction: discord.Interaction):
        self._reset_items()
        self.add_item(self._save_button())
        self.add_item(self._cancel_button())
        embed = discord.Embed(
            title=f"Confirm {self.slot.capitalize()} Spec",
            description=(
                f"**Class:** {self.chosen_class}\n"
                f"**Role:** {ROLE_EMOJI.get(self.chosen_role, '')} {self.chosen_role}\n"
                f"**Spec:** {self.chosen_spec}"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    def _cancel_button(self):
        button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="wowroster_cancel")

        async def cb(interaction: discord.Interaction):
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(content="Cancelled.", embed=None, view=None)
            self.stop()

        button.callback = cb
        return button

    def _save_button(self):
        button = discord.ui.Button(label="Save", style=discord.ButtonStyle.success, custom_id="wowroster_save")

        async def cb(interaction: discord.Interaction):
            await self.cog.save_spec(
                interaction, self.member, self.slot, self.chosen_class, self.chosen_role, self.chosen_spec
            )
            for item in self.children:
                item.disabled = True
            self.stop()

        button.callback = cb
        return button


# --------------------------------------------------------------------------- #
# Persistent panel posted in a channel: Set Main / Set Secondary / View / Reset
# --------------------------------------------------------------------------- #


class RosterPanelView(discord.ui.View):
    def __init__(self, cog: "WowRoster"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Set Main", emoji="⚔️", style=discord.ButtonStyle.primary, custom_id="wowroster_set_main")
    async def set_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SetupView(self.cog, "main", interaction.user)
        await view.show_class_step(interaction, first=True)

    @discord.ui.button(
        label="Set Secondary", emoji="🔄", style=discord.ButtonStyle.primary, custom_id="wowroster_set_secondary"
    )
    async def set_secondary(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SetupView(self.cog, "secondary", interaction.user)
        await view.show_class_step(interaction, first=True)

    @discord.ui.button(
        label="View Roster", emoji="📋", style=discord.ButtonStyle.secondary, custom_id="wowroster_view"
    )
    async def view_roster(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.cog.build_roster_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Reset", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="wowroster_reset")
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ConfirmResetView(self.cog, interaction.user)
        await interaction.response.send_message(
            "Are you sure you want to clear **your** roster entry?", view=view, ephemeral=True
        )


class ConfirmResetView(discord.ui.View):
    def __init__(self, cog: "WowRoster", member: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.member = member

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.member.id

    @discord.ui.button(label="Yes, reset", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.reset_member(interaction, self.member)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Your roster entry was cleared.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", view=None)


# --------------------------------------------------------------------------- #
# Cog
# --------------------------------------------------------------------------- #


class WowRoster(commands.Cog):
    """Let members pick a WoW main/secondary spec via dropdowns, synced to a Google Sheet."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=0xA1A7057, force_registration=True)
        self.config.register_guild(sheet_id=None, worksheet="Roster", credentials=None)
        self.config.register_member(
            main_class=None,
            main_role=None,
            main_spec=None,
            secondary_class=None,
            secondary_role=None,
            secondary_spec=None,
            last_updated=None,
        )
        self._gspread_clients = {}  # guild_id -> gspread.Client (cached)

    async def cog_load(self):
        self.bot.add_view(RosterPanelView(self))

    # ------------------------------------------------------------------ #
    # Data helpers
    # ------------------------------------------------------------------ #

    async def save_spec(self, interaction, member, slot, cls, role, spec):
        async with self.config.member(member).all() as data:
            data[f"{slot}_class"] = cls
            data[f"{slot}_role"] = role
            data[f"{slot}_spec"] = spec
            data["last_updated"] = datetime.now(timezone.utc).isoformat()

        embed = discord.Embed(
            description=f"✅ Saved **{slot}**: {cls} / {role} / {spec}", color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
        await self.sync_member_to_sheet(member)

    async def reset_member(self, interaction, member):
        await self.config.member(member).clear()
        await self.sync_member_to_sheet(member)

    async def build_roster_embed(self, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title=f"{guild.name} — WoW Roster", color=discord.Color.gold())
        all_members = await self.config.all_members(guild)
        if not all_members:
            embed.description = "No one has set a spec yet."
            return embed
        for member_id, data in all_members.items():
            member = guild.get_member(member_id)
            name = member.display_name if member else f"Unknown ({member_id})"
            main = _format_slot(data, "main")
            sec = _format_slot(data, "secondary")
            embed.add_field(name=name, value=f"**Main:** {main}\n**Secondary:** {sec}", inline=False)
        return embed

    # ------------------------------------------------------------------ #
    # Google Sheets sync
    # ------------------------------------------------------------------ #

    async def _get_client(self, guild: discord.Guild):
        if gspread is None:
            return None
        creds_json = await self.config.guild(guild).credentials()
        if not creds_json:
            return None
        if guild.id in self._gspread_clients:
            return self._gspread_clients[guild.id]

        def _build():
            info = json.loads(creds_json)
            creds = GCredentials.from_service_account_info(info, scopes=SCOPES)
            return gspread.authorize(creds)

        client = await asyncio.to_thread(_build)
        self._gspread_clients[guild.id] = client
        return client

    async def _get_worksheet(self, guild: discord.Guild):
        client = await self._get_client(guild)
        if client is None:
            return None
        sheet_id = await self.config.guild(guild).sheet_id()
        ws_name = await self.config.guild(guild).worksheet()
        if not sheet_id:
            return None

        def _open():
            sh = client.open_by_key(sheet_id)
            try:
                ws = sh.worksheet(ws_name)
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title=ws_name, rows=200, cols=len(SHEET_HEADER))
                ws.append_row(SHEET_HEADER)
            if ws.row_values(1) != SHEET_HEADER:
                ws.update("A1", [SHEET_HEADER])
            return ws

        return await asyncio.to_thread(_open)

    async def sync_member_to_sheet(self, member: discord.Member):
        guild = member.guild
        ws = await self._get_worksheet(guild)
        if ws is None:
            return  # sheet not configured yet — local Config is still authoritative
        data = await self.config.member(member).all()
        row = [
            str(member.id),
            str(member),
            data.get("main_class") or "",
            data.get("main_role") or "",
            data.get("main_spec") or "",
            data.get("secondary_class") or "",
            data.get("secondary_role") or "",
            data.get("secondary_spec") or "",
            data.get("last_updated") or "",
        ]

        def _write():
            cell = ws.find(str(member.id), in_column=1)
            if cell is None:
                ws.append_row(row)
            else:
                ws.update(f"A{cell.row}:I{cell.row}", [row])

        await asyncio.to_thread(_write)

    async def sync_all_to_sheet(self, guild: discord.Guild):
        ws = await self._get_worksheet(guild)
        if ws is None:
            return False
        all_members = await self.config.all_members(guild)
        rows = [SHEET_HEADER]
        for member_id, data in all_members.items():
            member = guild.get_member(member_id)
            name = str(member) if member else str(member_id)
            rows.append(
                [
                    str(member_id),
                    name,
                    data.get("main_class") or "",
                    data.get("main_role") or "",
                    data.get("main_spec") or "",
                    data.get("secondary_class") or "",
                    data.get("secondary_role") or "",
                    data.get("secondary_spec") or "",
                    data.get("last_updated") or "",
                ]
            )

        def _write():
            ws.clear()
            ws.update("A1", rows)

        await asyncio.to_thread(_write)
        return True

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #

    @commands.group(name="wowroster", aliases=["wr"])
    @commands.guild_only()
    async def wowroster(self, ctx: commands.Context):
        """WoW roster commands."""

    @wowroster.command(name="panel")
    @checks.admin_or_permissions(manage_guild=True)
    async def wowroster_panel(self, ctx: commands.Context):
        """Post the roster control panel in this channel."""
        embed = discord.Embed(
            title="WoW Roster",
            description="Use the buttons below to set your main/secondary spec or view the roster.",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed, view=RosterPanelView(self))

    @wowroster.command(name="setsheet")
    @checks.admin_or_permissions(manage_guild=True)
    async def wowroster_setsheet(self, ctx: commands.Context, sheet_id: str):
        """Set the Google Sheet ID this server's roster syncs to (the long ID in the sheet's URL)."""
        await self.config.guild(ctx.guild).sheet_id.set(sheet_id)
        await ctx.send("Sheet ID saved. Run `[p]wowroster setcreds` next if you haven't, then `[p]wowroster sync`.")

    @wowroster.command(name="setcreds")
    @checks.admin_or_permissions(manage_guild=True)
    async def wowroster_setcreds(self, ctx: commands.Context):
        """Attach a Google service-account JSON key file to this command to enable sheet sync."""
        if not ctx.message.attachments:
            await ctx.send(
                "Attach the service-account JSON key file to this message "
                "(Google Cloud Console → IAM → Service Accounts → Keys)."
            )
            return
        attachment = ctx.message.attachments[0]
        raw = await attachment.read()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            await ctx.send("That doesn't look like a valid JSON key file.")
            return
        await self.config.guild(ctx.guild).credentials.set(json.dumps(parsed))
        self._gspread_clients.pop(ctx.guild.id, None)
        await ctx.send(
            "Credentials saved. Share your Google Sheet with the `client_email` in that key file (Editor access), "
            "then run `[p]wowroster sync`."
        )

    @wowroster.command(name="sync")
    @checks.admin_or_permissions(manage_guild=True)
    async def wowroster_sync(self, ctx: commands.Context):
        """Force a full push of the local roster to the configured Google Sheet."""
        async with ctx.typing():
            ok = await self.sync_all_to_sheet(ctx.guild)
        if ok:
            await ctx.send("Roster synced to Google Sheets.")
        else:
            await ctx.send("Sheet isn't configured yet — run `setsheet` and `setcreds` first.")

    @wowroster.command(name="show")
    async def wowroster_show(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """View your roster entry, or someone else's."""
        member = member or ctx.author
        data = await self.config.member(member).all()
        embed = discord.Embed(title=f"{member.display_name}'s Roster Entry", color=discord.Color.gold())
        embed.add_field(name="Main", value=_format_slot(data, "main"), inline=False)
        embed.add_field(name="Secondary", value=_format_slot(data, "secondary"), inline=False)
        await ctx.send(embed=embed)


def _format_slot(data: dict, slot: str) -> str:
    cls = data.get(f"{slot}_class")
    role = data.get(f"{slot}_role")
    spec = data.get(f"{slot}_spec")
    if not cls:
        return "*Not set*"
    return f"{ROLE_EMOJI.get(role, '')} {cls} — {role} — {spec}"
