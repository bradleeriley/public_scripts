# Discord Elobot for Mordhau Fight Club
# Runs elo calculations and maintains a leaderboard of teams

import guildconfig
import os
import discord
import json

from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
from discord.ext.commands import RoleConverter
from datetime import date

# Storing Discord Bot token locally
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


bot = commands.Bot(command_prefix='!') # Setting the bot prefix
bot.remove_command('help') # Removes default help command from discord.py

# All the bot settings will be stored here for each guild
botDict = {}
settings = guildconfig.settings
        #await winLoss(logList, ctx)
# When the bot starts it will load the teams json files, so no data is lost.
@bot.event
async def on_ready():
    print("Starting Elobot...")
    if not os.path.exists('config'):
        os.makedirs('config')
        os.chdir('config') 
    else:
        os.chdir('config') 
    for guild in bot.guilds:
        if os.path.isfile(str(guild.id) + '.json') == False:
            with open(str(guild.id) + '.json', 'w+') as newJsonFile:
                eloBot = settings(guild.id)
                botDict[str(guild.id)] = (eloBot)
                json.dump(vars(eloBot), newJsonFile, indent=4)
        else:
            with open(str(guild.id) + '.json', 'r') as jsonFile:
                config = json.load(jsonFile)
                eloBot = settings(config)
                botDict[str(guild.id)] = eloBot
    print("Ready!")

# When the bot joins a new guild, make a json file for it
@bot.event
async def on_guild_join(guild):
    if os.path.isfile(str(guild.id) + '.json') == False:
            with open(str(guild.id) + '.json', 'w+') as newJsonFile:
                eloBot = settings(guild.id)
                botDict[str(guild.id)] = (eloBot)
                json.dump(vars(eloBot), newJsonFile, indent=4)

# If the bot is kicked or leaves a guild, delete the json.
@bot.event
async def on_guild_remove(guild):
    if os.path.isfile(str(guild.id) + '.json') == True:
        os.remove(str(guild.id) + '.json')

# Only users with administrative priveledges in Discord can add an allowed role
@bot.command()
@commands.has_permissions(administrator=True)
async def addrole(ctx, role):
    try:
        role = await commands.RoleConverter().convert(ctx, role)
    except commands.BadArgument:
        await ctx.send(f":x: Invalid syntax, try !role @rolename")
        return
    await botDict[str(ctx.guild.id)].addRole(role, ctx)

# Only users with administrative priveledges in Discord can remove an allowed role
@bot.command()
@commands.has_permissions(administrator=True)
async def removerole(ctx, role):
    try:
        role = await commands.RoleConverter().convert(ctx, role)
    except commands.BadArgument:
        await ctx.send(f":x: Invalid syntax, try !role @rolename")
        return
    await botDict[str(ctx.guild.id)].removerole(role, ctx)

# Print a nice embed message listing the allowed roles.
# Administrator and allowed roles can run this command.
@bot.command()
async def showsettings(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)) or ctx.message.author.guild_permissions.administrator:
        boardHidden = str(botDict[str(ctx.guild.id)].hideBoard)
        if set(botDict[str(ctx.guild.id)].roleList):
            allowedRoles = botDict[str(ctx.guild.id)].roleList
            roleNames = []
            for eachRole in allowedRoles:
                eachRole = "<@&" + str(eachRole) + ">"
                role = await commands.RoleConverter().convert(ctx, eachRole)
                roleNames.append(role.name)
            roleNames = '\n'.join(roleNames)
            embed=discord.Embed(title="Elobot Settings")
            embed.add_field(name="Allowed Roles", value=roleNames, inline=True)
            #await ctx.send(embed=embed)
            embed.add_field(name="Hide Board", value=boardHidden, inline=True)
            await ctx.send(embed=embed)
        else:
            embed=discord.Embed(title="Elobot Settings")
            embed.add_field(name="Roles", value="None", inline=True)
            embed.add_field(name="Hide Board", value=boardHidden, inline=True)
            await ctx.send(embed=embed)

# Adds team with specified elo
# ex: !addteam @20Royals 2000
# ex: !addteam 20Royals 2000
# ex: !addteam "Apeman A" 1500
@bot.command()
async def addteam(ctx, teamName, elo):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].addTeam(ctx, teamName, elo)

# Deletes a team from the leaderboard and log.
# ex: !removeteam @Last Kings
# ex: !removeteam "Last Kings"
@bot.command()
async def removeteam(ctx, teamName):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].deleteTeam(ctx, teamName) 

# Manually set the elo for a team and immediately update the leaderboard
# ex: !setelo @Reliquary 1200
# ex: !setelo "Apeman A" 2300
@bot.command()
async def setelo(ctx, teamName, elo):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].setElo(ctx, teamName, elo)

# Sets the channel that the leaderboard will be maintained in, must contain a channel mention.
# ex: !setboardchannel #elo-log
@bot.command()
async def setboardchannel(ctx, channel):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        try:
            channel = await commands.TextChannelConverter().convert(ctx, channel)
            await botDict[str(ctx.guild.id)].setBoardChannel(channel, ctx)
        except commands.BadArgument:
            await ctx.send(f":x: Invalid syntax. Try: !setboardchannel #channelname")

# If there are any changes to the json file or board but are not printed yet in the board channel, refresh the board channel leaderboard.
# ex: !refreshboard
@bot.command()
async def refreshboard(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].updateBoard(ctx)

@bot.command()
async def board(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].showBoard(ctx)

@bot.command()
async def hideboard(ctx, setting):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        if setting.lower() == 'true' or setting.lower() == 'false':
            await botDict[str(ctx.guild.id)].toggle_hideBoard(ctx, setting)
        else:
            await ctx.send(":x: Only true or false are valid arguments. Example: !toggleboard true")

# Adds a match between two teams with a max of 3 wins.
# Updates the elo for the teams and updates the leaderboard.
# ex: !addmatch @Sperg Squad 3-0 @Obsidian
# ex: !addmatch "Apeman A" 3-0 "Reliquary"
# ex: !addmatch "Apeman A" 3-0 @Reliquary
@bot.command()
async def addmatch(ctx, team1, score, team2):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        try:
            team1 = await commands.RoleConverter().convert(ctx, team1)
            team2 = await commands.RoleConverter().convert(ctx, team2)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(':x: Role entered is not valid. Example: !addmatch @Reliquary 3-0 @Terry')
            return
        if '-' not in score:
            await ctx.send(':x: Incorrect syntax. Example: !addmatch @Reliquary 3-0 @Terry')
        await botDict[str(ctx.guild.id)].matchResult(ctx, team1, score, team2)

# Displays the log for a team. Gives a brief history to the wins and losses
# ex: !showhistory @Reliquary
# ex: !showhistory "Last Kings B"
@bot.command()
async def showhistory(ctx, team):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        try:
            team = await commands.RoleConverter().convert(ctx, team)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(':x: Role entered is not valid')
            return
        await botDict[str(ctx.guild.id)].displayhistory(ctx, team)

@bot.command()
async def showstats(ctx, team):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        try:
            team = await commands.RoleConverter().convert(ctx, team)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(':x: Role entered is not valid')
            return
        await botDict[str(ctx.guild.id)].displaystats(ctx, team)

@bot.command()
async def showlog(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        if botDict[str(ctx.guild.id)].adminLog:
            await botDict[str(ctx.guild.id)].showLog(ctx)
            return
        else:
            await ctx.send(':x: Admin log is empty')
            return
# Simulates the elo changes within a match. Same as !addmatch except doesn't write any of the new elo changes.
# ex: !simulmatch @Sperg Squad 3-0 @Obsidian
# ex: !simulmatch "Apeman A" 3-0 "Reliquary"
# ex: !simulmatch "Apeman A" 3-0 @Reliquary
@bot.command()
async def simulmatch(ctx, team1, score, team2):
    authorRoles = [role.id for role in ctx.message.author.roles]
    authorRoles = [str(i) for i in authorRoles]
    if (set([str(i) for i in botDict[str(ctx.guild.id)].roleList]) & set(authorRoles)) or (set(botDict[str(ctx.guild.id)].board.keys()) & set(authorRoles)) :
        try:
            team1 = await commands.RoleConverter().convert(ctx, team1)
            team2 = await commands.RoleConverter().convert(ctx, team2)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(':x: Role entered is not valid. Example: !simulmatch Reliquary 3-0 Terry')
            return
        if '-' not in score:
            await ctx.send(':x: Incorrect syntax. Example: !simulmatch Reliquary 3-0 Terry')
        await botDict[str(ctx.guild.id)].simulResult(ctx, team1, score, team2)



# Displays the help screen
@bot.command()
async def elobothelp(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    authorRoles = [str(i) for i in authorRoles]
    if (set([str(i) for i in botDict[str(ctx.guild.id)].roleList]) & set(authorRoles)):
        embed=discord.Embed(title="Elo Bot", description="Remember, you do NOT have to mention a role to run the command, you can insert the name of the role instead. If there is a space in the role name, use quotes around it.")
        embed.add_field(name="!elobothelp", value="Shows this menu.", inline=False)
        embed.add_field(name="!showroles", value="Shows the roles that are allowed to run !setboardchannel, !addteam, !setelo, !removeteam, and !showhistory.", inline=False)
        embed.add_field(name="!hideboard <true/false>", value="If you do not want the updateable leaderboard, you can hide the board.", inline=False)
        embed.add_field(name="!board", value="Sends a copy of the current leaderboard in the channel you asked from. Useful if you are hiding the leaderboard with the above command.", inline=False)
        embed.add_field(name="!addrole @role", value="Add the role to the list of allowed roles in !showroles to run elo commands.", inline=False)
        embed.add_field(name="!addteam @role integer", value="Use a role to create a team with the specified elo (replace integer with a number).", inline=False)
        embed.add_field(name="!removeteam @role", value="Deletes a team from the leaderboard.", inline=False)
        embed.add_field(name="!setelo @role integer", value="Manually set the elo of a team (replace integer with the elo you want to change it to.)", inline=False)
        embed.add_field(name="!showhistory @role", value="Displays the last 10 elo changes for a team, and why.", inline=False)
        embed.add_field(name="!addmatch @role int-int @role", value="Adds a match to the log and changes elo. Wins are capped to a max of 3.", inline=False)
        embed.add_field(name="!simulmatch @role int-int @role", value="Simulates a matches results and the elo change from said match. Wins are capped to a max of 3.", inline=False)
        await ctx.send(embed=embed)
    elif (set(botDict[str(ctx.guild.id)].board.keys()) & set(authorRoles)):
        embed=discord.Embed(title="Elo Bot", description="Help")
        embed.add_field(name="!elobothelp", value="Shows this menu.", inline=False)
        embed.add_field(name="!simulmatch @role int-int @role", value="Simulates a matches results and the elo change from said match. Wins are capped to a max of 3.", inline=False)
        embed.add_field(name="!showstats @role", value="Displays statistics. You do not have to mention a role, you can enter the role name. Example: !showstats 'Apeman A'", inline=False)
        await ctx.send(embed=embed)


if __name__ == "__main__":      
    bot.run(TOKEN)