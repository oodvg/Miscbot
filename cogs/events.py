import discord
from discord.ext import commands, tasks
from cogs.utils import utilities as utils

from datetime import datetime, timedelta
import requests

class Events(commands.Cog, name="Events"):
    def __init__(self, bot):
        self.bot = bot
        self.check_queue.start()

    @commands.command()
    @commands.has_role("Staff")
    async def completechallenge(self, ctx, member: discord.Member, challenge_type: str, scaled_challenge_score: float=None):
        name, uuid = await utils.get_dispnameID(await utils.name_grabber(member))
        challenge_type = challenge_type.lower()

        # Calculate points based on challenge
        if challenge_type in ["scaled", "s"]:
            if scaled_challenge_score == None:
                await ctx.send("You must enter the player's score for this challenge!")
                return
            
            # Get player data
            row = await self.get_player_short(uuid)
            if row != None:
                uuid, total_points, completed_challenges = row
                await self.update_value(uuid, total_points, completed_challenges, scaled_challenge_score)
            else:
                await self.insert_new(uuid, 0, 1, scaled_challenge_score)

            await ctx.send(f"{name}'s scaled challenge score today is {scaled_challenge_score}")
            return

        elif challenge_type in ["hard", "h"]:
            points_earned = 2
        elif challenge_type in ["easy", "e"]:
            points_earned = 1
        elif challenge_type in ["member", "m"]:
            if await utils.get_guild(name) != "Miscellaneous" and await utils.get_guild(name) not in self.bot.misc_allies:
                await ctx.send("This player is not eligible for this challenge! Only members of miscellaneous and allied guilds can participate!")
                return
            else:
                points_earned = 1
        else:
            await ctx.send("Invalid challenge! Available challenges are: **S**caled, **H**ard, **E**asy, **M**ember.")
            return

        # Update player's statistics for general challenge
        # Get data from db
        row = await self.get_player(uuid)
        if row != None:
            uuid, total_points, completed_challenges, scaled_challenge_score = row
            total_points += points_earned
            completed_challenges += 1
            await self.update_value(uuid, total_points, completed_challenges, scaled_challenge_score)
        else:
            total_points = points_earned
            completed_challenges = 1
            await self.insert_new(uuid, total_points, completed_challenges, 0)
        
        # Send player's overall stats
        embed = discord.Embed(title=f"Event statistics - {name}", description=f"**Points earned:** {points_earned}\n**Total points:** {total_points}\n**Challenges completed:** {completed_challenges}", color=0x8368ff)
        await ctx.send(embed=embed)


    
    @commands.command()
    @commands.has_role("Staff")
    async def addpoints(self, ctx, member: discord.Member, points: int):
        name, uuid = await utils.get_dispnameID(await utils.name_grabber(member))
        row = await self.get_player_short(uuid)

        if row == None:
            await self.insert_new(uuid, points, None, 0)
            completed_challenges = 0
        else:
            uuid, total_points, completed_challenges = row
            points += total_points
            await self.update_value(uuid, points, completed_challenges)

        # Send player's overall stats
        embed = discord.Embed(title=f"Event statistics - {name}", description=f"**Total points:** {points}\n**Challenges completed:** {completed_challenges}", color=0x8368ff)
        await ctx.send(embed=embed)


        
    @commands.command()
    @commands.has_role("Staff")
    async def removepoints(self, ctx, member: discord.Member, points: int):
        name, uuid = await utils.get_dispnameID(await utils.name_grabber(member))
        row = await self.get_player_short(uuid)

        if row != None:
            uuid, total_points, completed_challenges = row
            points = total_points - points
            await self.update_value(uuid, points)
        else:
            await self.insert_new(uuid, points, None, 0)
            completed_challenges = 0

        # Send player's overall stats
        embed = discord.Embed(title=f"Event statistics - {name}", description=f"**Total points:** {points}\n**Challenges completed:** {completed_challenges}", color=0x8368ff)
        await ctx.send(embed=embed)



    @commands.command(aliases=["qchallenge"])
    @commands.has_role("Staff")
    async def queuechallenge(self, ctx):
        await ctx.send("Please enter the date for which these challenges will be set (EST). `(YYYY-MM-DD)`")
        target_date = await self.bot.wait_for('message',
            check=lambda x: x.channel == ctx.channel and x.author == ctx.author)
        target_date = target_date.content

        if target_date.lower() == "none":
            await ctx.send("Entry cancelled!")
            return
        
        try: 
            target_date = (datetime.strptime(target_date, "%Y-%m-%d")).strftime("%Y-%m-%d")
        except Exception:
            await ctx.send("Invalid date! Please enter a date in the form YYYY-MM-DD")
            return


        await ctx.send(f"Please enter the scaled challenge for {target_date}.")
        scaled_challenge = await self.bot.wait_for('message',
                    check=lambda x: x.channel == ctx.channel and x.author == ctx.author)
        scaled_challenge = scaled_challenge.content
        if scaled_challenge.lower() == "none":
            await ctx.send("Entry cancelled!")
            return

        await ctx.send(f"Please enter the hard challenge for {target_date} worth two points.")
        hard_challenge = await self.bot.wait_for('message',
                    check=lambda x: x.channel == ctx.channel and x.author == ctx.author)
        hard_challenge = hard_challenge.content
        if hard_challenge.lower() == "none":
            await ctx.send("Entry cancelled!")
            return
        
        await ctx.send(f"Please enter the easy challenge for {target_date} worth one point.")
        easy_challenge = await self.bot.wait_for('message',
                    check=lambda x: x.channel == ctx.channel and x.author == ctx.author)
        easy_challenge = easy_challenge.content
        if easy_challenge.lower() == "none":
            await ctx.send("Entry cancelled!")
            return

        await ctx.send(f"Please enter the member/ally challenge for {target_date} worth one point.")
        guild_challenge = await self.bot.wait_for('message',
                    check=lambda x: x.channel == ctx.channel and x.author == ctx.author)
        guild_challenge = guild_challenge.content
        if guild_challenge.lower() == "none":
            await ctx.send("Entry cancelled!")
            return


        tomorrow_day = (datetime.utcnow() + timedelta(days=1) - timedelta(hours=5)).strftime("%Y-%m-%d")
        cursor = await self.bot.db.execute("SELECT date FROM event_challenge WHERE date = (?)", (tomorrow_day,))

        if await cursor.fetchone() == None:
            await self.bot.db.execute("INSERT INTO event_challenge VALUES (?, ?, ?, ?, ?)", (tomorrow_day, scaled_challenge, hard_challenge, easy_challenge, guild_challenge,))
        else:
            await self.bot.db.execute("UPDATE event_challenge SET scaled_challenge = (?), hard_challenge = (?), easy_challenge = (?), member_challenge = (?) WHERE date = (?)", (scaled_challenge, hard_challenge, easy_challenge, guild_challenge, tomorrow_day,))
        await self.bot.db.commit()

        await ctx.send(f"Alright! The challenges for {target_date} have been set!")
        embed = await self.challenge_embed(target_date)
        if embed != None:
            await ctx.send(embed=embed)


    @commands.command(aliases=["challengelb"])
    @commands.has_role("Staff")
    async def challengeleaderboard(self, ctx):
        description = "Listed below are the top 10 players for today's scaled challenge.\n"
        with requests.Session() as session:
            count = 1
            for data_set in await self.get_scaled_lb():
                uuid, score = data_set
                name = utils.fetch(session, uuid)
                description = description + "\n**" + str(count) + " -**" + uuid + ": " + str(score) if name == None else description + "\n**" + str(count) + " -** " + name + ": " + str(score)
                count += 1
            session.close()
        await ctx.send(embed=discord.Embed(title="Scaled Challenge Leaderboard", description=description, color=0x8368ff))

    
    
    @commands.command(aliases=["resetlb", "clearlb"])
    @commands.has_role("Staff")
    async def resetleaderboard(self, ctx):
        await ctx.send("Are you sure you want to reset the daily scaled challenge leaderboard? This action cannot be undone. (yes/no)")
        confirmation = await self.bot.wait_for('message',
                    check=lambda x: x.channel == ctx.channel and x.author == ctx.author)
        confirmation = confirmation.content 
        if confirmation.lower() in ["yes", "y", "ye", "yeah"]:
            await self.bot.db.execute("UPDATE event SET scaled_challenge_score = 0")
            await self.bot.db.commit()
            await ctx.send("The daily scaled challenge leaderboard has been cleared!")
        else:
            await ctx.send("Cancelling data deletion!")



    async def insert_new(self, uuid, points, challenges, scaled_challenge_score):
        await self.bot.db.execute("INSERT INTO event VALUES (?, ?, ?, ?)", (uuid, points, challenges, scaled_challenge_score,))
        await self.bot.db.commit()

    async def update_value(self, uuid, points, completed=None, scaled_challenge_score=None):
        if scaled_challenge_score != None:
            await self.bot.db.execute("UPDATE event SET points = (?), scaled_challenge_score = (?) WHERE uuid = (?)", (points, scaled_challenge_score, uuid,))
        elif completed == None:
            await self.bot.db.execute("UPDATE event SET points = (?) WHERE uuid = (?)", (points, uuid,))
        else:
            await self.bot.db.execute("UPDATE event SET points = (?), completed = (?) WHERE uuid = (?)", (points, completed, uuid,))
        await self.bot.db.commit()

    async def get_player(self, uuid):
        cursor = await self.bot.db.execute("SELECT * FROM event WHERE uuid = (?)", (uuid,))
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def get_player_short(self, uuid):
        cursor = await self.bot.db.execute("SELECT uuid, points, completed FROM event WHERE uuid = (?)", (uuid,))
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def get_scaled_lb(self):
        cursor = await self.bot.db.execute("SELECT uuid, scaled_challenge_score FROM event ORDER BY scaled_challenge_score DESC")
        rows = await cursor.fetchmany(10)
        await cursor.close()
        return rows

    async def challenge_embed(self, date):
        cursor = await self.bot.db.execute("SELECT * FROM event_challenge WHERE date = (?)", (date,))
        row = await cursor.fetchone()
        await cursor.close()

        if row != None:
            _, scaled_challenge, hard_challenge, easy_challenge, member_challenge = row
            embed=discord.Embed(title=f"Challenges for {date}", color=0x8368ff)
            embed.add_field(name="Scaled challenge", value=scaled_challenge, inline=False)
            embed.add_field(name="Hard challenge", value=hard_challenge, inline=False)
            embed.add_field(name="Easy challenge", value=easy_challenge, inline=False)
            embed.add_field(name="Member/ally challenge", value=member_challenge, inline=False)
            return embed
            
        return None

    @tasks.loop(minutes=1)
    async def check_queue(self):
        current_date = (datetime.utcnow() - timedelta(hours=5)).strftime("%Y-%m-%d")
        embed = await self.challenge_embed(current_date)

        if embed != None:
            await self.bot.events_channel.send(embed=embed)
            await self.bot.events_channel.send(f"{self.bot.christmas_event.mention}")

            await self.bot.db.execute("DELETE FROM event_challenge WHERE date = (?)", (current_date,))
            await self.bot.db.commit()


    @check_queue.before_loop
    async def before_queue_check(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Events(bot))