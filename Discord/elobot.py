# Discord Elobot for Mordhau Fight Club
# Runs elo calculations and maintains a leaderboard of teams

import os
import random
import discord
import json
import math

from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
from discord.ext.commands import RoleConverter

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
botDict = {}

class settings:
    def __init__(self, guild):
        if type(guild) is dict:
            self.__dict__.update(guild)
        else:
            self.guild = guild
            self.blacklisted_channels = []
            self.roleList = []
            self.board = {}
            self.boardID = 0
            self.boardChannel = 0
            self.log = {}
    def __str__(self):
        return str(self.__dict__)
    def __repr__(self):
        return str(self.__dict__)

    def updateSettings(self):
        with open(str(self.guild) + '.json', 'w+') as newJsonFile:
            #print("Dumped Config to" +  str(self.guild) + '.json')
            #print(self.__dict__)
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

    async def addTeam(self, ctx, teamName, elo):
        channel = ctx.message.channel
        try:
            teamName = await commands.RoleConverter().convert(ctx, teamName)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(":x: Role does not exist")
            return 
        if self.boardChannel:
            try:
                elo = int(elo)
                if (str(teamName.id) in (k for k in self.board.keys())):
                    await channel.send(':x: Team already exists: ' + str(teamName))
                    return                   
                else:
                    self.board[str(teamName.id)] = elo
                    await channel.send(":white_check_mark: Added team " + str(teamName) + " with '" + str(elo) + "' elo")
                    create_entry = [{int(elo) : 'Start'}]
                    self.log[str(teamName.id)] = create_entry
                    await self.updateBoard(ctx)
                    self.updateSettings()
            except ValueError:
                await channel.send(':x: Invalid syntax')
                return
            
        else:
            await channel.send(":x: Please set a board channel first with the command !setboardchannel #channelname")

    async def deleteTeam(self, ctx, teamName):
        channel = ctx.message.channel
        try:
            teamName = await commands.RoleConverter().convert(ctx, teamName)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(":x: Role does not exist")
            return 
        if self.boardChannel:
            try:
                if str(teamName.id) in self.board.keys():
                    del self.board[str(teamName.id)] 
                    del self.log[str(teamName.id)]
                    await channel.send(':white_check_mark: Removed team: ' + str(teamName))
                    await self.updateBoard(ctx)
                    self.updateSettings()
                    return                   
                else:
                    await channel.send(":x: Team doesn't exist: " + str(teamName))
                    return
            except ValueError:
                await channel.send(':x: Invalid syntax')
                return
            
        else:
            await channel.send(":x: Please set a board channel first with the command !setboardchannel #channelname")
    async def setElo(self, ctx, teamName, elo):
        async def update(self, teamName, channel):
            if str(teamName.id) in self.board.keys():
                currentElo = self.board[str(teamName.id)]
                try:
                    self.board[str(teamName.id)] = int(elo)
                except ValueError:
                    await channel.send(':x: Invalid syntax Example: !setelo "Team Name" 1900')
                    return
                await self.updateBoard(ctx)
                author = ctx.author.name
                self.log[str(teamName.id)].append({int(elo) : str(author + ' Set elo')})
                self.updateSettings()
                await channel.send(":white_check_mark: " + str(teamName) + ": "  +  str(currentElo) + " -> " + str(elo))
                return
            else:
                await channel.send(':x: Team not found: ' + str(teamName))
                return
        
        channel = ctx.channel
        try:
            teamName = await commands.RoleConverter().convert(ctx, teamName)
            await update(self, teamName, channel)
        except discord.ext.commands.errors.RoleNotFound:
                await channel.send(':x: Team not found: ' + str(teamName))
                return
    
    async def setBoardChannel(self, boardChannel, message):
        channel = message.channel
        self.boardChannel = boardChannel.id
        self.updateSettings()
        await channel.send(":white_check_mark: Set board channel to: " + str(boardChannel.name))
        
    async def updateBoard(self, ctx):
        displayBoard = []
        for eachTeam in self.board.keys():
            eachTeam = "<@&" + str(eachTeam) + ">"
            eachTeam = await commands.RoleConverter().convert(ctx, eachTeam)
            teamElo = self.board[str(eachTeam.id)] 
            standing = [eachTeam, teamElo]
            displayBoard.append(standing)
        displayBoard.sort(key=lambda x: x[1])
        displayBoard.reverse()
        counter = len(displayBoard) + 1
        standings = []
        counter = 0
        eloList = [x[1] for x in displayBoard]
        added = False

        for eachTeam in displayBoard:
            teamName = eachTeam[0].name
            teamElo = eachTeam[1]
            if eloList.count(eachTeam[1]) > 1:
                if added == False:
                    counter += 1
                    added = True
                entry = "(" + str(counter) + "T) " + str(teamName) + " - " + str(teamElo) 
            else:
                counter += 1
                added = False
                entry = "(" + str(counter) + ") " + str(teamName) + " - " + str(teamElo) 
            if len(self.log[str(eachTeam[0].id)]) > 1:
                    previousElo =   int(list(self.log[str(eachTeam[0].id)][-2].keys())[0])
                    eloDiff = teamElo - previousElo
                    if eloDiff > 0:
                        entry = entry + " (↑" + str(eloDiff) + ")"
                    elif eloDiff < 0:
                        entry = entry + " (↓" + str(abs(eloDiff)) + ")"
            standings.append(entry)

        standings = "```\n" + "\n".join(standings) + "\n```"
        if self.boardID:
            try:
                channel = await commands.TextChannelConverter().convert(ctx, str(self.boardChannel))
                msg = await channel.fetch_message(self.boardID)
                await msg.edit(content=standings)
                self.updateSettings()
            except discord.NotFound:
                channel = await commands.TextChannelConverter().convert(ctx, str(self.boardChannel))
                message = await channel.send(standings)
                self.boardID = message.id
                self.updateSettings()         
        else:
            channel = await commands.TextChannelConverter().convert(ctx, str(self.boardChannel))
            message = await channel.send(standings)
            self.boardID = message.id
            self.updateSettings()

    async def matchResult(self, ctx, team1, score, team2):
        def calculateElo(currentElo, opponentElo, wins, loss):
            newElo = currentElo + 150 * ((wins / (wins + loss)) - (1 / (1 + 10 ** ((opponentElo - currentElo) / 400)))) + 25 * ((wins - loss) / (abs(wins - loss)))
            return newElo
        team1Elo = self.board[str(team1.id)]
        team2Elo = self.board[str(team2.id)]
        result = score.split('-')
        try:
            team1wins = int(result[0])
            team2wins = int(result[1])
        except ValueError:
            await ctx.send(":x: Invalid Syntax. Score not integer.")
            return
        if (int(team1wins) > 3) or (int(team2wins) > 3):
            await ctx.send(":x: Invalid Syntax. 3 wins maximum.")
            return
        newTeam1Elo = round(calculateElo(team1Elo, team2Elo, int(team1wins), int(team2wins)))
        self.board[str(team1.id)] = newTeam1Elo
        #self.log[(str(team1.id))].append(newTeam1Elo)
        self.log[str(team1.id)].append({int(newTeam1Elo) : str(team1.name + " " + score + " " + team2.name)})
        newTeam2Elo = round(calculateElo(team2Elo, team1Elo, int(team2wins), int(team1wins)))
        self.board[str(team2.id)] = newTeam2Elo
        #self.log[(str(team2.id))].append(newTeam2Elo)
        self.log[str(team2.id)].append({int(newTeam2Elo) : str(team1.name + " " + score + " " + team2.name)})
        
        embed=discord.Embed(title="Elo Summary")
        diffElo = team1Elo - newTeam1Elo
        if diffElo < 0:
            arrow = '↑'
        else:
            arrow = '↓'
        value = str(team1Elo) + ' -> ' + str(newTeam1Elo) + ' (' + arrow + str(abs(diffElo)) + ')'
        embed.add_field(name=team1.name, value=value, inline=True)
        diffElo = team2Elo - newTeam2Elo
        if diffElo < 0:
            arrow = '↑'
        else:
            arrow = '↓'
        value = str(team2Elo) + ' -> ' + str(newTeam2Elo) + ' (' + arrow + str(abs(diffElo)) + ')'
        embed.add_field(name=team2.name, value=value, inline=True)
        await ctx.send(embed=embed)
        await self.updateBoard(ctx)

    async def simulResult(self, ctx, team1, score, team2):
        def calculateElo(currentElo, opponentElo, wins, loss):
            newElo = currentElo + 150 * ((wins / (wins + loss)) - (1 / (1 + 10 ** ((opponentElo - currentElo) / 400)))) + 25 * ((wins - loss) / (abs(wins - loss)))
            return newElo
        team1Elo = self.board[str(team1.id)]
        team2Elo = self.board[str(team2.id)]
        result = score.split('-')
        try:
            team1wins = int(result[0])
            team2wins = int(result[1])
        except ValueError:
            await ctx.send(":x: Invalid Syntax. Score not integer.")
            return
        if (int(team1wins) > 3) or (int(team2wins) > 3):
            await ctx.send(":x: Invalid Syntax. 3 wins maximum.")
            return
        newTeam1Elo = round(calculateElo(team1Elo, team2Elo, int(team1wins), int(team2wins)))
        newTeam2Elo = round(calculateElo(team2Elo, team1Elo, int(team2wins), int(team1wins)))
        
        embed=discord.Embed(title="Simulation Summary")
        diffElo = team1Elo - newTeam1Elo
        if diffElo < 0:
            arrow = '↑'
        else:
            arrow = '↓'
        value = str(team1Elo) + ' -> ' + str(newTeam1Elo) + ' (' + arrow + str(abs(diffElo)) + ')'
        embed.add_field(name=team1.name, value=value, inline=True)
        diffElo = team2Elo - newTeam2Elo
        if diffElo < 0:
            arrow = '↑'
        else:
            arrow = '↓'
        value = str(team2Elo) + ' -> ' + str(newTeam2Elo) + ' (' + arrow + str(abs(diffElo)) + ')'
        embed.add_field(name=team2.name, value=value, inline=True)
        await ctx.send(embed=embed)
        await self.updateBoard(ctx)

    async def displayhistory(self, ctx, team):
        try:
            logList = self.log[str(team.id)]
        except KeyError:
            await ctx.send(":x: Role not found in list of teams")
            return
        logList.reverse()
        counter = -1
        history = ""
        for eachlog in logList:
            if counter > -10:
                elo = list(eachlog.keys())[0]
                result = str(eachlog[elo])
                history += str(abs(counter)) + '. ' + str(elo) + " : " + result + '\n'
                counter -= 1
            else:
                break
        title = "Elo History of " + team.name
        embed=discord.Embed(title=title)
        embed.add_field(name="Last 10 records", value=history, inline=True)
        await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print("Starting Elobot...")
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

@bot.event
async def on_guild_join(guild):
    if os.path.isfile(str(guild.id) + '.json') == False:
            with open(str(guild.id) + '.json', 'w+') as newJsonFile:
                eloBot = settings(guild.id)
                botDict[str(guild.id)] = (eloBot)
                json.dump(vars(eloBot), newJsonFile, indent=4)
@bot.event
async def on_guild_remove(guild):
    if os.path.isfile(str(guild.id) + '.json') == True:
        os.remove(str(guild.id) + '.json')

@bot.command()
@commands.has_permissions(administrator=True)
async def addrole(ctx, role):
    try:
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
        await botDict[str(ctx.guild.id)].addTeam(ctx, teamName, elo)

@bot.command()
async def removeteam(ctx, teamName):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].deleteTeam(ctx, teamName) 
@bot.command()
async def setelo(ctx, teamName, elo):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].setElo(ctx, teamName, elo)

@bot.command()
async def setboardchannel(ctx, channel):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        try:
            channel = await commands.TextChannelConverter().convert(ctx, channel)
            await botDict[str(ctx.guild.id)].setBoardChannel(channel, ctx.message)
        except commands.BadArgument:
            await ctx.send(f":x: Invalid syntax. Try: !setboardchannel #channelname")

@bot.command()
async def refreshboard(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].updateBoard(ctx)

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
async def simulmatch(ctx, team1, score, team2):
    authorRoles = [role.id for role in ctx.message.author.roles]
    authorRoles = [str(i) for i in authorRoles]
    print(set(botDict[str(ctx.guild.id)].board.keys()))
    print(botDict[str(ctx.guild.id)].roleList)
    print(set(authorRoles))
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

if __name__ == "__main__":      
    bot.run(TOKEN)