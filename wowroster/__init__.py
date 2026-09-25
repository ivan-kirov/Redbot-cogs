from .wowroster import WoWRoster


async def setup(bot):
    await bot.add_cog(WoWRoster(bot))