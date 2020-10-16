import os
import random
import discord
import json

from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
from discord.ext.commands import RoleConverter

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!')
botDict = {}

class settings:
    def __init__(self, guild):
        if type(guild) is dict:
            self.__dict__.update(guild)
        else:
            self.guild = str(guild)
            self.blacklisted_channels = []
            self.roleList = []
            self.board = {}
            self.boardID = 0
            self.boardChannel = 0
            self.log = []
    def __str__(self):
        return str(self.__dict__)
    def __repr__(self):
        return str(self.__dict__)

    def updateSettings(self):
        with open(str(self.guild) + '.json', 'w+') as newJsonFile:
            print("Dumped Config to" +  str(self.guild) + '.json')
            print(self.__dict__)
            json.dump(self.__dict__, newJsonFile, indent=4)

    def setGuild(self, guild):
        self.guild = guild.id

    def setBlackChannels(self, channel):
        self.blacklisted_channels.append(channel)

    async def addRole(self, role, message):
        channel = message.channel
        if role.id not in self.roleList:
            self.roleList.append(role.id)
            self.updateSettings() 
            await channel.send(":white_check_mark: Added role: " + str(role.name))
        else:
            await channel.send(':x: Role already exists: ' + str(role.name))
            return
    
    async def removerole(self, role, message):
        channel = message.channel
        if self.roleList:
            try:
                self.roleList.remove(role.id)
                self.updateSettings() 
                await channel.send(":white_check_mark: Removed role: " + role.name)
            except ValueError:
                await channel.send(':x: Role not found in list of allowed roles: ' + str(role.name))
        else:
            await channel.send(':x: There are currently no roles allowed')

    async def addTeam(self, message, teamName, elo):
        channel = message.channel
        if self.boardChannel:
            try:
                elo = int(elo)
                self.board[str(teamName)] = elo
                await channel.send(":white_check_mark: Added team " + str(teamName) + " with '" + str(elo) + "' elo")
            except ValueError:
                await channel.send(':x: Invalid syntax')
                return
            self.updateSettings()
        else:
            await channel.send(":x: Please set a board channel first with the command !setboardchannel #channelname")

    async def setElo(self, teamName, elo, message):
        try:
            teamName = str(teamName)
            self.board[str(teamName)] = elo
        except KeyError:
            channel = message.channel
            await channel.send('Unable to find team: ' + str(teamName))
    
    async def setBoardChannel(self, channel):
        self.boardChannel = channel
        await channel.send(":white_check_mark: Set board channel to: " + str(channel.name))
        

    
@bot.event
async def on_ready():
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
                botDict[str(guild.id)] = (eloBot)
                print("Found existing file!")
    print(botDict)

@bot.command()
async def check(ctx):
    print(botDict[str(ctx.guild.id)].roleList)
    roleIDs = [role.id for role in ctx.message.author.roles]
    print(roleIDs)
    if set(botDict[str(ctx.guild.id)].roleList) & set(roleIDs):
        await ctx.send("You have permissions, nice.")

@bot.command()
@commands.has_permissions(administrator=True)
async def addrole(ctx, role):
    try:
        print(role)
        role = await commands.RoleConverter().convert(ctx, role)
    except commands.BadArgument:
        await ctx.send(f":x: Invalid syntax, try !role @rolename")
        return
    await botDict[str(ctx.guild.id)].addRole(role, ctx.message)
    
@bot.command()
@commands.has_permissions(administrator=True)
async def removerole(ctx, role):
    try:
        role = await commands.RoleConverter().convert(ctx, role)
    except commands.BadArgument:
        await ctx.send(f":x: Invalid syntax, try !role @rolename")
        return
    await botDict[str(ctx.guild.id)].removerole(role, ctx.message)

@bot.command()
async def showroles(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)) or ctx.message.author.guild_permissions.administrator:
        if set(botDict[str(ctx.guild.id)].roleList):
            allowedRoles = botDict[str(ctx.guild.id)].roleList
            roleNames = []
            for eachRole in allowedRoles:
                eachRole = "<@&" + str(eachRole) + ">"
                role = await commands.RoleConverter().convert(ctx, eachRole)
                roleNames.append(role.name)
            roleNames = '\n'.join(roleNames)
            embed=discord.Embed(title="Allowed Roles")
            embed.add_field(name="Roles", value=roleNames, inline=True)
            await ctx.send(embed=embed)
        else:
            embed=discord.Embed(title="Allowed Roles")
            embed.add_field(name="Roles", value="None", inline=True)
            await ctx.send(embed=embed)

@bot.command()
async def addteam(ctx, teamName, elo):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].addTeam(ctx.message, teamName, elo)

@bot.command()
async def setboardchannel(ctx, channel):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        try:
            channel = await commands.TextChannelConverter().convert(ctx, channel)
        except commands.BadArgument:
            await ctx.send(f":x: Invalid syntax. Try: !setboardchannel #channelname")

if __name__ == "__main__":      
    bot.run(TOKEN)