from redbot.core import commands, Config


class WoWRoster(commands.Cog):
    """WoW roster management."""

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(
            self,
            identifier=987654321
        )

        default_user = {
            "main_class": None,
            "main_role": None,
            "main_spec": None
        }

        self.config.register_user(**default_user)

    @commands.group()
    async def wow(self, ctx):
        """WoW roster commands."""
        pass

    @wow.command()
    async def setmain(self, ctx, wow_class: str, role: str):
        """Set main class and role."""

        await self.config.user(ctx.author).main_class.set(wow_class)
        await self.config.user(ctx.author).main_role.set(role)

        await ctx.send(
            f"Saved: {wow_class} ({role})"
        )

    @wow.command()
    async def myroster(self, ctx):
        """Show your roster."""

        data = await self.config.user(ctx.author).all()

        await ctx.send(
            f"Class: {data['main_class']}\n"
            f"Role: {data['main_role']}\n"
            f"Spec: {data['main_spec']}"
        )