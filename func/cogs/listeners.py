from discord.ext import commands
from func.classes.Listener import Listener


class Listeners(commands.Cog, name="listeners"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await Listener(obj=member).on_member_join()

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        await Listener(obj=event).on_error()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await Listener(obj=error).on_command_error(ctx)


def setup(bot):
    bot.add_cog(Listeners(bot))