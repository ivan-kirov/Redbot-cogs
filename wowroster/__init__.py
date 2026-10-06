from .wowroster import WowRoster
from .wowroster import WowRoster


async def setup(bot):
    await bot.add_cog(WowRoster(bot))
