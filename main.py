import discord
import logging
import re
import datetime
import pytz
import asyncio
import json
import requests
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter
from pytesseract import image_to_string
import numpy as np
import re
import scipy
import scipy.misc
import scipy.cluster
import struct

from trade import Trader
from utility import similarityDistance

''' Scraping:
ALL:
rows = $('#pokemon-table-out tr')
pokemon = []
for (var i = 1; i<rows.length; i+=3){
	p = {};
	p['names'] = []
	lines = rows[i].innerText.split('\n');
	names = lines[0].split(' ')
	p['names'][0] = names[0].substring(1)
	p['names'][1] = names.slice(1, names.length).join(' ').trim()

	stats = lines[1].split('\t')
	p['stamina'] = stats[0]
	p['attack'] = stats[1]
	p['defense'] = stats[2]

	p['rank'] = lines[3].split('\t')[1]
	pokemon.push(p)
}

SHINY:
'''

logging.basicConfig(level=logging.INFO)
client = discord.Client()

pokedata = []
cpm = []

def log(message):
    file = open('logs.txt', 'a')
    d = datetime.datetime.now()
    timezone = pytz.timezone("America/Denver")
    d_aware = timezone.localize(d)
    file.write(d_aware.strftime("%Y-%m-%d %H:%M:%S") + ' ' + message + '\n')
    file.close()

@client.event
async def on_ready():
    print('Logged in')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='Pokemon Go'))
    log('Logged in...')

@client.event
async def on_member_join(member):
    log(member.name + ' joined the server')

@client.event
async def on_reaction_add(reaction, user):
	if user==client.user:
		return
	message = reaction.message
	try:
		e = message.embeds[0]
		if user.name != e['footer']['text'] and user.id!='81881597757882368':
			return
	except:
		return
	r = reaction.emoji
	if r != '➡' and r != '⬅':
		return
	t = Trader(client, message, pokedata)
	await t.doEditMatch(reaction)

@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.is_private:
        log(message.author + ' send me a private message that said "{}"'.format(message.clean_content))
        await client.send_message(message.channel, content='Sorry, I don\'t understand private messages yet. If you think this is a mistake, please message an Admin or Moderator.')
        return
    elif message.server.id=='486556505668059141':
        if message.channel.id=='487294887096614913' or message.channel.id=='487000542787403777':
            mrs = message.author.roles
            roles = message.server.roles
            content = message.clean_content
            firstspace = content.find(' ', 4)
            c = '.iam'
            if similarityDistance('.iam', content[:firstspace]) > similarityDistance('.iamnot', content[:firstspace]):
                c = '.iamnot'
            if similarityDistance(c, content[:firstspace])>3:
                log('Message not understood: {}'.format(content))
                await client.add_reaction(message, '👎')
                return
            else:
                best = None
                bscore = 1
                colors = [discord.Color(0x3498db), discord.Color(0x1abc9c)]
                for r in roles:
                    if r.color in colors:
                        l = len(content)
                        s = similarityDistance(c + ' ' + r.name, content)
                        s = s/l
                        if s < bscore:
                            best = r
                            bscore = s
                if best is not None and bscore<.1:
                    if c=='.iam':
                        await client.add_roles(message.author, best)
                        return
                    if c=='.iamnot':
                        await client.remove_roles(message.author, best)
                        return
                else:
                    await client.send_message(message.channel, 'No role detected')
    else:
        if message.channel.name == 'role-assignment' or message.channel.name == 'porygons-playground' or message.channel.name == 'bot-test':
            await parseCommand(message)
            return
        elif message.channel.name == 'trades_test' or message.channel.name == 'trades':
            t = Trader(client, message, pokedata)
            if message.author.id == '448855673623805966':
                pass#await client.delete_message(message)
            else:
                await t.doCommand()
        elif message.channel.name == 'ivs':
            imageurl = message.attachments[0]['url']
            response = requests.get(imageurl)
            img = Image.open(BytesIO(response.content))
            ivs = await parseImage(img)
            if ivs is None or len(ivs)==0:
                await client.send_message(message.channel, content='Something went wrong.')
            else:
                await client.send_message(message.channel, content='{:.2f}%-{:.2f}%'.format(np.min(ivs), np.max(ivs)) + message.author.mention)

async def parseImage(i):
    try:
        i = i.convert('L')                             # grayscale
        i = i.filter(ImageFilter.MedianFilter())       # a little blur
        i = i.point(lambda x: 0 if x < 150 else 255)   # threshold (binarize)
        i = i.resize((750, 1334))
        w, h = i.size
        cpi = i.crop((w/3-10, h/15, 2*w/3, 11*h/100))
        cpi.save('cp.png')
        cp = image_to_string(cpi, config='outputbase digits')
        p = re.compile('\d{2,4}')
        m = p.search(cp)
        cp = m.group(0)
        print(cp)
        print('CP:', cp)

        ni = i.crop((w/5, 3*h/7, 4*w/5, 3.5*h/7))
        ni.save('name.png')
        name = image_to_string(ni)
        print('Name:', name)

        hi = i.crop((w/5, 3.5*h/7, 4*w/5, 4*h/7))
        hi.save('hp.png')
        hp = image_to_string(hi, config='outputbase digits')
        print(hp)
        p = re.compile('\d+')
        m = p.findall(hp)
        print(m)
        hp = m[0]
        print('HP:', hp)

        si = i.crop((2*w/5, 5.5*h/7, 6*w/9, 6*h/7))
        si.save('sd.png')
        sd = image_to_string(si)[1:]
        p = re.compile('\d{1,3}00')
        m = p.search(sd)
        sd = m.group(0)
        print('Stardust:', sd)

        sd = int(sd)
        if sd<=1000:
            level_range = (sd/100-1, sd/100+0.5)
        elif sd<=2500:
            it = (sd-1300)/300+0.5
            level_range = (sd/100-it-1.5, sd/100-it)
        elif sd<=5000:
            it = (sd-3000)/500
            level_range = (21+2*it, 21+2*it+1.5)
        elif sd<=9000:
            it = (sd-6000)/1000
            level_range = (31+2*it, 31+2*it+1.5)
        else:
            level_range = (39, 39.5)

        print(level_range)

        for p in pokedata:
            if name == p['names'][1]:
                poke = p
                break

        matches = []
        for i in range(4):
            ind = int(level_range[0]*2+i-2)
            if ind>=len(cpm):
                break
            c = cpm[ind]
            for k in range(16):
                psta = (int(poke['stamina'])+k)
                if int(np.floor(psta*c)) != int(hp):
                    continue
                for j in range(16):
                    for i in range(16):
                        patt = (int(poke['attack'])+i)
                        pdef = (int(poke['defense'])+j)
                        pcp = np.max([10.0, np.floor(np.sqrt(psta)*patt*np.sqrt(pdef)*c**2/10.0)])
                        if int(pcp)==int(cp):
                            s = 'Match: A:{}, D:{}, S:{}: {:.2f}%, level {}'.format(i, j, k, (i+k+j)/45*100, ind/2+1)
                            matches.append((i+k+j)/45*100)
                            print(s)
        return matches
    except Exception as e:
        print(e)
        return None

async def parseCommand(message):
    content = str(message.clean_content).lower()
    lines = content.split('\n')
    for l in lines:
        firstspace = l.find(' ', 4)
        if firstspace == -1:
            print("I don't think this was supposed to happen, but this message is weird:\n {}".format(l))
            return
        if similarityDistance('.stats', l[:firstspace]) < 2 and (message.channel.name == 'porygons-playground' or message.channel.name == 'bot-test'):
            await doPokeStats(message, l)
        elif (message.channel.name == 'role-assignment' or message.channel.name == 'bot-test'):
            await setUserRole(message, l)

async def doPokeStats(message, content):
    firstspace = content.find(' ', 4)
    secondspace = content.find(' ', firstspace+1)
    poke = content[firstspace+1:]
    levels = [20, 25, 40]
    if secondspace != -1:
        poke = poke[:secondspace-(firstspace+1)]
        levels = [int(content[secondspace:])]

    best = None
    bestscore = np.infty
    if poke.isdigit():
        for p in pokedata:
            if poke==p['names'][0]:
                best = p
                bestscore = 0
    else:
        for p in pokedata:
            score = similarityDistance(p['names'][1], poke)
            if score<bestscore:
                best = p
                bestscore = score
    try:
        imageurl = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{}.png'.format(best['names'][0])
        response = requests.get(imageurl)
        i1 = Image.open(BytesIO(response.content))
        i1 = i1.convert("P", colors=3)
        embed = discord.Embed(color=getIfromRGB(i1.getpalette()[6:9]))

        embed.set_thumbnail(url=imageurl)
    except:
        embed = discord.Embed()

    embed.set_author(name=best['names'][1])

    for l in levels:
        ind = int(l*2-2)
        c = cpm[ind]
        psta = (int(best['stamina'])+15)
        patt = (int(best['attack'])+15)
        pdef = (int(best['defense'])+15)
        pcp = np.max([10.0, np.floor(np.sqrt(psta)*patt*np.sqrt(pdef)*c**2/10.0)])
        reply = '```CP: {}\nHP: {}\nAttack: {}\nDefense: {}```'.format(int(pcp), int(psta*c), int(patt*c), int(pdef*c))
        embed.add_field(name='100% IV at level {}'.format(l), value=reply, inline=False)
    await client.send_message(message.channel, content='', embed=embed)

def getIfromRGB(rgb):
    red = rgb[0]
    green = rgb[1]
    blue = rgb[2]
    RGBint = (red<<16) + (green<<8) + blue
    return RGBint

async def setUserRole(message, content):
    firstspace = content.find(' ', 4)
    c = '.iam'
    if similarityDistance('.iam', content[:firstspace]) > similarityDistance('.iamnot', content[:firstspace]):
        c = '.iamnot'
    if similarityDistance(c, content[:firstspace])>3:
        log('Message not understood: {}'.format(content))
        await client.add_reaction(message, '👎')
        return
    else:
        roles = message.server.roles
        bestScore = len(content)
        bestRole = 0
        for r in roles:
            score = similarityDistance(c + ' ' + r.name.lower(), content)
            if score < bestScore:
                bestScore = score
                bestRole = r
        differentiation = bestScore/len(content)
        valid = ['VALOR', 'MYSTIC', 'INSTINCT', 'DailyRaider', 'NOBORaider', 'SOBORaider', 'PearlStreetRaider', 'CURaider', 'exraider']
        validColors = [discord.Color(0x1f8b4c)]
        if (not bestRole.name in valid) and (not bestRole.color in validColors):
            differentiation = 1
        if differentiation < .15:
            log('Match found between {} and {} with score {}'.format(c + ' ' + bestRole.name.lower(), content, differentiation))
            if c=='.iam':
                v = True
                if bestRole.name in valid[:2]:
                    if userHasRole(message.author, valid[0]) or userHasRole(message.author, valid[1]) or userHasRole(message.author, valid[2]):
                        v = False
                        log('User {} trying to assign another team.'.format(message.author.name))
                        return
                if v:
                    log('Assigning ' + message.author.name + ' ' + bestRole.name)
                    await client.send_message(message.author, content='I have assigned you to the role {}. If this is a mistake, please contact a Moderator or an Admin for further assistance.'.format(bestRole.name))
                    await client.add_roles(message.author, bestRole)
                    return
            elif not bestRole.name in valid[:2]:
                log('Unassigning ' + message.author.name + ' ' + bestRole.name)
                await client.send_message(message.author, content='I have unassigned you from the role {}. If this is a mistake, please contact a Moderator or an Admin for further assistance.'.format(bestRole.name))
                await client.remove_roles(message.author, bestRole)
                return
        else:
            #log('Message not understood: {}'.format(content))
            await client.add_reaction(message, '👎')

def userHasRole(user, role):
    roles = user.roles
    for r in roles:
        if r.name==role:
            return True
    return False


def main():
    global pokedata
    global cpm
    with open('pokemon.json') as f:
        data = json.load(f)
        pokedata = data['pokemon']
        cpm = data['cpm']
    with open('secret.txt') as s:
        secret = s.read()
    client.run(secret[:-1]);

if __name__ == '__main__':
    main()
