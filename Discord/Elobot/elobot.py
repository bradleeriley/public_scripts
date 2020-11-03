# Discord Elobot for Mordhau Fight Club
# Runs elo calculations and maintains a leaderboard of teams

import os
import random
import discord
import json
import math
import copy

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

class settings:
    def __init__(self, guild):
        if type(guild) is dict: # If the guild exists, import it.
            self.__dict__.update(guild)
        else: # If its a new guild, create empty settings.
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

    def updateSettings(self): # Dump the settings into a json file with the guild ID as the file name.
        with open(str(self.guild) + '.json', 'w+') as newJsonFile:
            json.dump(self.__dict__, newJsonFile, indent=4)
    def todayDate(self):
        today = date.today()
        today = today.strftime("%m-%d-%Y")
        return today
    # Will use later
    #def setBlackChannels(self, channel):
        #self.blacklisted_channels.append(channel)

    # Add an allowed role to use the bot (except for the !simulmatch command)
    async def addRole(self, role, message):
        channel = message.channel
        if role.id not in self.roleList:
            self.roleList.append(role.id)
            self.updateSettings() 
            await channel.send(":white_check_mark: Added role: " + str(role.name))
        else:
            await channel.send(':x: Role already exists: ' + str(role.name))
            return
    
    # Removes a role from the allowed roles
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

    # Adds a role (team) with specified elo to the leaderboard then updates the json file.
    async def addTeam(self, ctx, teamName, elo):
        channel = ctx.message.channel # Get the channel the command was sent from
        try: # Try to convert the team name into a role
            teamName = await commands.RoleConverter().convert(ctx, teamName)
        except discord.ext.commands.errors.RoleNotFound:
            await ctx.send(":x: Role does not exist")
            return 
        if self.boardChannel: # Check to see if a leaderboard exists
            try:
                elo = int(elo) # Try to see if the elo is actually a number
                if (str(teamName.id) in (k for k in self.board.keys())): # Check to see if the team already exists.
                    await channel.send(':x: Team already exists: ' + str(teamName))
                    return                   
                else: # If its a new team create the key name of the team name and the value with the elo, update the json file. Let the user know it worked.
                    self.board[str(teamName.id)] = elo
                    await channel.send(":white_check_mark: Added team " + str(teamName) + " with '" + str(elo) + "' elo")
                    #logEntry = [{int(elo) : [{'Start' : 'Start'}]}]
                    today = date.today()
                    today = today.strftime("%m-%d-%Y")
                    logEntry = [{'elo' : int(elo), 'date' : today, 'opponent': 'Start', 'wins' : 0, 'loss' : 0}]
                    self.log[str(teamName.id)] = logEntry
                    await self.updateBoard(ctx)
                    self.updateSettings()
            except ValueError:
                await channel.send(':x: Invalid syntax')
                return 
        else:
            await channel.send(":x: Please set a board channel first with the command !setboardchannel #channelname")

    # Removes a team from the leaderboard and updates the json for the guild.
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
    
    # Manually change the elo of a team, then update the json.
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
                #self.log[str(teamName.id)].append({int(elo) : [str(author + ' Set elo')]})
                today = self.todayDate()
                logEntry = {'elo' : int(elo), 'date' : today, 'opponent': str(author + ' Set elo'), 'wins' : 0, 'loss' : 0}
                self.log[str(teamName.id)].append(logEntry)
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

    # Set the channel the leaderboard will be in. Passed channel object as boardChannel   
    async def setBoardChannel(self, boardChannel, message):
        channel = message.channel
        self.boardChannel = boardChannel.id
        self.updateSettings()
        await channel.send(":white_check_mark: Set board channel to: " + str(boardChannel.name))
        
    # Looks at the board of the guild and rewrites the leaderboard in the board channel
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
            teamID = eachTeam[0].id
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
            if len(self.log[str(teamID)]) > 1:
                    previousElo = self.log[str(teamID)][-1]['elo']
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

    # Add a match between two teams with a max of 3 wins
    # ex: !addmatch @Reliquary 3-0 @Syndicate
    async def matchResult(self, ctx, team1, score, team2):
        def calculateElo(currentElo, opponentElo, wins, loss):
            # This is the actual elo calculation
            newElo = currentElo + 150 * ((wins / (wins + loss)) - (1 / (1 + 10 ** ((opponentElo - currentElo) / 400)))) + 25 * ((wins - loss) / (abs(wins - loss)))
            return newElo
        # Format the command message into variables
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
        # Calculate the new elo for each team and add the new elo to the leaderboard as well as the log.
        newTeam1Elo = round(calculateElo(team1Elo, team2Elo, int(team1wins), int(team2wins)))
        self.board[str(team1.id)] = newTeam1Elo
        #self.log[(str(team1.id))].append(newTeam1Elo)
        today = self.todayDate()
        logEntry1 = {'elo' : newTeam1Elo, 'date' : today, 'opponent': team2.id, 'wins' : team1wins, 'loss' : team2wins}
        self.log[str(team1.id)].append(logEntry1)
        
        newTeam2Elo = round(calculateElo(team2Elo, team1Elo, int(team2wins), int(team1wins)))
        self.board[str(team2.id)] = newTeam2Elo
        #self.log[(str(team2.id))].append(newTeam2Elo)
        #self.log[str(team2.id)].append({int(newTeam2Elo) : str(team1.name + " " + score + " " + team2.name)})
        logEntry2 = {'elo' : newTeam2Elo, 'date' : today, 'opponent': team1.id, 'wins' : team2wins, 'loss' : team1wins}
        self.log[str(team2.id)].append(logEntry2)
        # Put together the embedded message telling how much elo is lost or gained.
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

    # Same thing as addmatch except it doesn't update the leaderboard or log
    # Used to test elo calculation or see probable outcomes.
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

    # Looks at the log for a team and displays the last 10 records with the win loss and elo change
    async def displayhistory(self, ctx, team):
        def calcDiff(logList, eachLog):
            eloDiff = logList[eachLog - 1]['elo'] - logList[eachLog]['elo']
            if eloDiff < 0:
                arrow = '↑'
            else:
                arrow = '↓'
            if eloDiff == 0:
                string = ''
            elif abs(eloDiff) < 10:
                string = '(' + arrow + str(abs(eloDiff)) + ')   '
            elif abs(eloDiff) > 99:
                string = '(' + arrow + str(abs(eloDiff)) + ') '
            else:
                string = '(' + arrow + str(abs(eloDiff)) + ')  '
            return string
        async def buildString(logList):
            string = '```'
            count = 0
            for eachLog in reversed(range(len(logList))):
                if count < 10:
                    count += 1
                    if isinstance(logList[eachLog]['opponent'], int):
                        opponent = await commands.RoleConverter().convert(ctx, str(logList[eachLog]['opponent']))
                        string += logList[eachLog]['date'] + " : " + str(logList[eachLog]['elo'])
                        string += ' ' + calcDiff(logList, eachLog)
                        string += ' ' + team.name + ' ' + str(logList[eachLog]['wins']) + ' - ' + str(logList[eachLog]['loss']) + ' ' + opponent.name
                    elif logList[eachLog]['opponent'] == 'Start':
                        string += logList[eachLog]['date'] + " : " + str(logList[eachLog]['elo'])
                        #string += ' ' + calcDiff(logList, eachLog)
                        string += ' Start'
                    elif 'Set elo' in logList[eachLog]['opponent']:
                        string += logList[eachLog]['date'] + " : " + str(logList[eachLog]['elo'])
                        string += ' ' + calcDiff(logList, eachLog)
                        string += logList[eachLog]['opponent']

                    string += '\n'
                else:
                    break
            string += '```'
            return string
        def buildEmbed(string):
            title = "Elo History of " + team.name
            embed=discord.Embed(title=title)
            embed.add_field(name="Last 10 records", value=string, inline=True)
            return embed
        try:
            logList = self.log[str(team.id)]
        except KeyError:
            await ctx.send(":x: Role not found in list of teams")
            return
        string = await buildString(logList)
        embed = buildEmbed(string)
        await ctx.send(embed=embed)

    async def displaystats(self, ctx, team):
        async def id_converter(logList, ctx):
            newMatchList = []
            for eachMatch in logList:
                if isinstance(eachMatch['opponent'], int):
                    eachMatch['opponent'] = "<@&" + str(eachMatch['opponent']) + ">"
                    eachMatch['opponent'] = await commands.RoleConverter().convert(ctx, eachMatch['opponent'])
                    newMatchList.append(eachMatch)
            return newMatchList
        
        async def get_mostPlayed(matches, ctx):
            def most_common(lst):
                return max(set(lst), key=lst.count)
            opponents = [x['opponent']for x in matches]
            mostPlayed = most_common(opponents)
            mostPlayedCount = opponents.count(mostPlayed)
            #mostPlayed = await commands.RoleConverter().convert(ctx, mostPlayed)
            return [mostPlayed.name, mostPlayedCount]
        
        def get_winLoss(matches):
            roundWins = sum([x['wins'] for x in matches])
            if not roundWins:
                roundWins = 0
            roundLoss = sum([x['loss'] for x in matches])
            if not roundLoss:
                roundLoss = 0
            matchWin = len([x['wins'] for x in matches if x['wins'] > x['loss']])
            if not matchWin:
                matchWin = 0
            matchLoss = len([x['loss'] for x in matches if x['loss'] > x['wins']])
            if not matchLoss:
                matchLoss = 0
            return [roundWins, roundLoss, matchWin, matchLoss]
        
        def get_mostRoundStat(matches, stat):
            opponents = {}
            if len(matches) > 1:
                for eachMatch in matches:
                    if eachMatch['opponent'] not in opponents.keys():
                        opponents[eachMatch['opponent']] = eachMatch[stat]
                    else:
                        opponents[eachMatch['opponent']] += eachMatch[stat]
                keys = list(opponents.keys())
                if len(keys) == 1:
                    team = keys[0]
                    mostRoundTeam = team.name
                    mostRoundCount = opponents[team]
                else:
                    mostRoundWins = max(opponents.items(), key=lambda k: k[1])
                    mostRoundTeam = str(mostRoundWins[0])
                    mostRoundCount = str(mostRoundWins[1])
                return [mostRoundTeam, mostRoundCount]
            else:
                team = matches[0]
                if team[stat] > 0:
                    return [team['opponent'].name, team[stat]]
                else:
                    return "0"
                

        def get_mostMatchStat(matches, stat):
            opponents = {}
            if stat == 'loss':
                opposite = 'wins'
            else:
                opposite = 'loss'
            if len(matches) < 2:
                team = matches[0]
                if team[stat] > team[opposite]:
                    mostMatchWins = [team['opponent'].name, 1]
                else:
                    mostMatchWins = [0]
                    return mostMatchWins
            else:
                for eachMatch in matches:
                    if eachMatch['opponent'].name not in opponents.keys():
                        if eachMatch[stat] > eachMatch[opposite]:
                            opponents[eachMatch['opponent'].name] = 1
                    else:
                        if eachMatch[stat] > eachMatch[opposite]:
                            opponents[eachMatch['opponent'].name] += 1     
                if opponents:
                    mostMatchWins = max(opponents.items(), key=lambda k: k[1])
                else:
                    mostMatchWins = [0]
                    return mostMatchWins          
            mostMatchTeam = str(mostMatchWins[0])
            mostMatchCount = str(mostMatchWins[1])
            return [mostMatchTeam, mostMatchCount]

        async def buildEmbed(ctx, stats, team):
            title = "Stats for " + team.name
            mostPlayed = str(stats['mostPlayed'][0]) + ' - ' + str(stats['mostPlayed'][1])
            if len(stats['winOpponent']) > 1:
                mostWins = str(stats['winOpponent'][0]) + ' - ' + str(stats['winOpponent'][1])
            else:
                mostWins = "0"

            if len(stats['lossOpponent']) > 1:
                mostLoss = str(stats['lossOpponent'][0]) + ' - ' + str(stats['lossOpponent'][1])
            else:
                mostLoss = "0"

            if len(stats['matchWinOpponent']) > 1:
                mostWinsOpponent = str(stats['matchWinOpponent'][0]) + ' - ' + str(stats['matchWinOpponent'][1])
            else:
                mostWinsOpponent = "0"

            if len(stats['matchLossOpponent']) > 1:
                mostLossOpponent = str(stats['matchLossOpponent'][0]) + ' - ' + str(stats['matchLossOpponent'][1])
            else:
                mostLossOpponent = "0"

            embed=discord.Embed(title=title, color=0x1eea1a)
            embed.add_field(name="Match Wins:", value=stats['matchWinCount'], inline=True)
            embed.add_field(name="Match Losses:", value=stats['matchLossCount'], inline=True)
            embed.add_field(name="Match Win/Loss Ratio:", value=round(stats['matchWinLossRatio'], 2), inline=True)
            embed.add_field(name="Round Wins:", value=stats['roundWinCount'], inline=True)
            embed.add_field(name="Round Losses:", value=stats['roundLossCount'], inline=True)
            embed.add_field(name="Round Win/Loss Ratio:", value=round(stats['roundWinLossRatio'], 2), inline=True)
            embed.add_field(name="Most Matches:", value=mostPlayed, inline=True)
            embed.add_field(name="Most Match Wins:", value=mostWinsOpponent, inline=True)
            embed.add_field(name="Most Match Losses:", value=mostLossOpponent, inline=True)
            embed.add_field(name="Most Round Wins:", value=mostWins, inline=True)
            embed.add_field(name="Most Round Losses:", value=mostLoss, inline=True)
            return embed
        try:
            logList = copy.deepcopy(self.log[str(team.id)])
        except KeyError:
            await ctx.send(":x: Role not found in list of teams")
            return

        stats = {}
        matches = await id_converter(logList, ctx)
        if not matches:
            await ctx.send(":x: That team doesn't have any stats to display.")
            return
        stats['mostPlayed'] = await get_mostPlayed(matches, ctx)
        totalWinLoss = get_winLoss(matches)
        stats['roundWinCount'] = totalWinLoss[0]
        stats['roundLossCount'] = totalWinLoss[1]
        stats['matchWinCount'] = totalWinLoss[2]
        stats['matchLossCount'] = totalWinLoss[3]
        if stats['roundWinCount'] == 0 or stats['roundLossCount'] == 0:
            stats['roundWinLossRatio'] = stats['roundWinCount']
        else:
            stats['roundWinLossRatio'] = stats['roundWinCount'] / stats['roundLossCount']
        if stats['matchWinCount'] == 0 or stats['matchLossCount'] == 0:
            stats['matchWinLossRatio'] = stats['matchWinCount']
        else:
            stats['matchWinLossRatio'] = stats['matchWinCount'] / stats['matchLossCount']
        stats['lossOpponent'] = get_mostRoundStat(matches, 'loss')
        stats['winOpponent'] = get_mostRoundStat(matches, 'wins')
        stats['matchWinOpponent'] = get_mostMatchStat(matches, 'wins')
        stats['matchLossOpponent'] = get_mostMatchStat(matches, 'loss')
        embed = await buildEmbed(ctx, stats, team)
        await ctx.send(embed=embed)

        

            

        #await winLoss(logList, ctx)
# When the bot starts it will load the teams json files, so no data is lost.
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
    await botDict[str(ctx.guild.id)].addRole(role, ctx.message)

# Only users with administrative priveledges in Discord can remove an allowed role
@bot.command()
@commands.has_permissions(administrator=True)
async def removerole(ctx, role):
    try:
        role = await commands.RoleConverter().convert(ctx, role)
    except commands.BadArgument:
        await ctx.send(f":x: Invalid syntax, try !role @rolename")
        return
    await botDict[str(ctx.guild.id)].removerole(role, ctx.message)

# Print a nice embed message listing the allowed roles.
# Administrator and allowed roles can run this command.
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
            await botDict[str(ctx.guild.id)].setBoardChannel(channel, ctx.message)
        except commands.BadArgument:
            await ctx.send(f":x: Invalid syntax. Try: !setboardchannel #channelname")

# If there are any changes to the json file or board but are not printed yet in the board channel, refresh the board channel leaderboard.
# ex: !refreshboard
@bot.command()
async def refreshboard(ctx):
    authorRoles = [role.id for role in ctx.message.author.roles]
    if (set(botDict[str(ctx.guild.id)].roleList) & set(authorRoles)):
        await botDict[str(ctx.guild.id)].updateBoard(ctx)

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
        embed=discord.Embed(title="Elo Bot", description="Help")
        embed.add_field(name="!elobothelp", value="Shows this menu.", inline=False)
        embed.add_field(name="!showroles", value="Shows the roles that are allowed to run !setboardchannel, !addteam, !setelo, !removeteam, and !showhistory.", inline=False)
        embed.add_field(name="!addrole @role", value="Add the role to the list of allowed roles in !showroles to run elo commands.", inline=False)
        embed.add_field(name="!addteam @role integer", value="Use a role to create a team with the specified elo (replace integer with a number).", inline=False)
        embed.add_field(name="!removeteam @role", value="Deletes a team from the leaderboard.", inline=False)
        embed.add_field(name="!setelo @role integer", value="Manually set the elo of a team (replace integer with the elo you want to change it to.)", inline=False)
        embed.add_field(name="!showhistory @role", value="Displays the last 10 elo changes for a team, and why,", inline=False)
        embed.add_field(name="!addmatch @role int-int @role", value="Adds a match to the log and changes elo. Wins are capped to a max of 3.", inline=False)
        embed.add_field(name="!simulmatch @role int-int @role", value="Simulates a matches results and the elo change from said match. Wins are capped to a max of 3.", inline=False)
        await ctx.send(embed=embed)
    elif (set(botDict[str(ctx.guild.id)].board.keys()) & set(authorRoles)):
        embed=discord.Embed(title="Elo Bot", description="Help")
        embed.add_field(name="!elobothelp", value="Shows this menu.", inline=False)
        embed.add_field(name="!simulmatch @role int-int @role", value="Simulates a matches results and the elo change from said match. Wins are capped to a max of 3.", inline=False)
        await ctx.send(embed=embed)


if __name__ == "__main__":      
    bot.run(TOKEN)