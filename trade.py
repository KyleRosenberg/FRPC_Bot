from utility import similarityDistance
import numpy as np
import re
import json
import discord
import datetime
import pytz

from network import Network

def log(message):
    file = open('logs.txt', 'a')
    d = datetime.datetime.now()
    timezone = pytz.timezone("America/Denver")
    d_aware = timezone.localize(d)
    file.write(d_aware.strftime("%Y-%m-%d %H:%M:%S") + ' ' + message + '\n')
    file.close()


class Trader:

    def __init__(self, c, m, p):
        self.client = c
        self.content = str(m.clean_content).lower()
        self.message = m
        self.pokedata = p
        try:
            with open('{}.json'.format(self.message.guild.id)) as f:
                data = json.load(f)
                self.wants = data['wants']
                self.haves = data['haves']
        except:
            self.wants = []
            self.haves = []
        for h in self.haves:
            if 'event' not in h:
                h['event'] = False
            if 'legacy' not in h:
                h['legacy'] = False
        for h in self.wants:
            if 'event' not in h:
                h['event'] = False
            if 'legacy' not in h:
                h['legacy'] = False

        with open('{}.json'.format(self.message.guild.id), 'w') as f:
            json.dump({
                'haves': self.haves,
                'wants': self.wants
            }, f)

        weights_file = 'weights.nn'
        biases_file = 'biases.nn'
        weights = []
        biases = []
        with open(weights_file, 'r') as f:
            weights = json.loads(f.read())
        with open(biases_file, 'r') as f:
            biases = json.loads(f.read())

        self.nn = Network([10, 5, 1])
        self.nn.weights = weights
        self.nn.biases = biases

    async def doCommand(self):
        content = self.content
        firstspace = content.find(' ', 4)
        if firstspace==-1:
            firstspace=len(content)
        command = content[:firstspace]
        rest = content[firstspace+1 :]
        coms = ['.trade', '.want', '.unwant', '.have', '.unhave', '.match', '.profile', '.clear', '.unclear']
        funcs = [self.doTrade, self.doWant, self.doUnWant, self.doHave, self.doUnHave, self.doMatch, self.doProfile, self.clear, self.unclear]
        scores = [similarityDistance(command, i)/len(command) for i in coms]
        lowest = np.min(scores)
        index = np.argmin(scores)
        if lowest > 0.15:
            pass
            '''
            con = 'Command not recognized {} {}'.format(command, self.message.author.mention)
            await self.message.channel.send(content=con)
            '''
        else:
            if index >=0 and index<len(funcs):
                await funcs[index](rest)
            else:
                await self.message.channel.send(content='This error shouldn\'t happen. Command not matched.')

    def getPokemonDetails(self, content):
        pokemon = {}
        if 'shiny ' in content:
            pokemon['shiny'] = True
            content = content.replace('shiny ', '')
        else:
            pokemon['shiny'] = False
        if 'event ' in content:
            pokemon['event'] = True
            content = content.replace('event ', '')
        else:
            pokemon['event'] = False
        if 'legacy ' in content:
            pokemon['legacy'] = True
            content = content.replace('legacy ', '')
        else:
            pokemon['legacy'] = False
        best = None
        bs = np.infty
        for p in self.pokedata:
            sc = similarityDistance(content.strip(), p['names'][1].lower())
            if sc < bs:
                bs = sc
                best = p
        if bs/len(content.strip()) > .2:
            return None
        pokemon['pokemon'] = best['names'][1]
        pokemon['active'] = True
        pokemon['owner'] = self.message.author.name
        pokemon['stats'] = best
        return pokemon

    def sameDict(self, a, b):
        if len(a)!=len(b) and 'stats' not in a and 'stats' not in b:
            return False
        for k in a:
            if k=='active' or k=='stats':
                continue
            if k not in b:
                return False
            if a[k]!=b[k]:
                return False
        return True

    async def clear(self, content):
        for h in self.haves:
            if h['owner']==self.message.author.name:
                h['active'] = False
        for w in self.wants:
            if w['owner'] == self.message.author.name:
                w['active'] = False
        with open('{}.json'.format(self.message.guild.id), 'w') as f:
            json.dump({
                'haves': self.haves,
                'wants': self.wants
            }, f)
        await self.message.add_reaction('👍')

    async def unclear(self, content):
        for h in self.haves:
            if h['owner']==self.message.author.name:
                h['active'] = True
        for w in self.wants:
            if w['owner'] == self.message.author.name:
                w['active'] = True
        with open('{}.json'.format(self.message.guild.id), 'w') as f:
            json.dump({
                'haves': self.haves,
                'wants': self.wants
            }, f)
        await self.message.add_reaction('👍')

    async def doTrade(self, content):
        sp = content.split(',')
        try:
            d1 = self.getPokemonDetails(sp[0])
            d2 = self.getPokemonDetails(sp[1])
            if d1 == None:
                await self.message.add_reaction('👎')
                return
            if d2 == None:
                await self.message.add_reaction('👎')
                return
            score = self.scorePokemon(d1, d2)
            reply = '{} ({}) for {} and {}'.format('Fair' if score>0.5 else 'Unfair', score, self.getPokeString(d1), self.getPokeString(d2))
            await self.message.channel.send(content=reply)
        except Exception as e:
            print(e)
            log('Exception in trade: {}'.format(e))
            await self.message.add_reaction('👎')

    async def doHave(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.message.add_reaction('👎')
            else:
                add = True
                same = False
                for h in self.haves:
                    if self.sameDict(h, d):
                        same = h['active']
                        h['active']=True
                        add = False
                        break
                if add:
                    self.haves.append(d)
                if not same:
                    await self.message.add_reaction('👍')
                else:
                    await self.message.add_reaction('👊')
                with open('{}.json'.format(self.message.guild.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
                #await self.message.add_reaction('👍')
        except:
            log('Exception in doHave')
            await self.message.add_reaction('👎')

    async def doUnHave(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.message.add_reaction('👎')
            else:
                had = False
                for h in self.haves:
                    if self.sameDict(h, d):
                        h['active']=False
                        had = True
                        break
                if had:
                    await self.message.add_reaction('👍')
                else:
                    await self.message.add_reaction('👊')
                with open('{}.json'.format(self.message.guild.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
        except:
            log('Exception in doUnhave')
            await self.message.add_reaction('👎')

    async def doWant(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.message.add_reaction('👎')
            else:
                add = True
                same = False
                for h in self.wants:
                    if self.sameDict(h, d):
                        same = h['active']
                        h['active']=True
                        add = False
                        break
                if add:
                    self.wants.append(d)
                if not same:
                    await self.message.add_reaction('👍')
                else:
                    await self.message.add_reaction('👊')
                with open('{}.json'.format(self.message.guild.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
                #await self.message.add_reaction('👍')
        except:
            log('Exception in doWant')
            await self.message.add_reaction('👎')

    async def doUnWant(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.message.add_reaction('👎')
            else:
                had = False
                for h in self.wants:
                    if self.sameDict(h, d):
                        h['active']=False
                        had = True
                        break
                if had:
                    await self.message.add_reaction('👍')
                else:
                    await self.message.add_reaction('👊')
                with open('{}.json'.format(self.message.guild.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
        except:
            log('Exception in doUnwant')
            await self.message.add_reaction('👎')

    async def doEditMatch(self, emoji):
        pages = ['0️⃣', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣']
        page = -1
        for r in self.message.reactions:
            try:
                ind = pages.index(r.emoji)
                page = ind
                break
            except ValueError:
                pass
        if page==-1:
            print('Weird error')
            return
        if emoji.name == '➡':
            page+=1
        else:
            page-=1
        
        await self.message.clear_reactions()

        e = self.message.embeds[0]
        sender = e.footer.text
        type = e.fields[0].name
        sender_haves = self.getEntriesFromUser(sender, self.haves)
        sender_wants = self.getEntriesFromUser(sender, self.wants)
        matches_h_w = []
        for hi in self.haves:
            if hi['active']==False:
                continue
            for hj in sender_wants:
                if hj['active']==False:
                    continue
                if hi['owner']!=hj['owner']:
                    if hi['pokemon']==hj['pokemon'] and hi['shiny']==hj['shiny'] and hi['legacy']==hj['legacy'] and hi['event']==hj['event'] and (hi not in matches_h_w):
                        matches_h_w.append(hi)

        matches_w_h = []
        for hi in self.wants:
            if hi['active']==False:
                continue
            for hj in sender_haves:
                if hj['active']==False:
                    continue
                if hi['owner']!=hj['owner']:
                    if hi['pokemon']==hj['pokemon'] and hi['shiny']==hj['shiny'] and hi['legacy']==hj['legacy'] and hi['event']==hj['event'] and (hi not in matches_w_h):
                        matches_w_h.append(hi)

        newh = []
        neww = []
        super_matches = []
        for h in matches_h_w:
            for w in matches_w_h:
                if h['owner']==w['owner']:
                    super_matches.append((h, w))

        for s in super_matches:
            newh.append(s[0])
            neww.append(s[1])

        nh = [h for h in matches_h_w if h not in newh]
        nw = [h for h in matches_w_h if h not in neww]

        matches_h_w = sorted(nh, key=lambda k:k['owner'].lower())
        matches_w_h = sorted(nw, key=lambda k:k['owner'].lower())

        embed = discord.Embed()
        if type=='Wants':
            i = 0
            for k in range(page):
                reply = ''
                reply_good = True
                while i < len(matches_h_w) and reply_good:
                    o = matches_h_w[i]['owner']
                    theirs = ''
                    tarray = []
                    while i < len(matches_h_w) and matches_h_w[i]['owner']==o and reply_good:
                        m = matches_h_w[i]
                        t = self.getPokeString(m)
                        if len(reply + theirs + t + ', ')<900:
                            theirs += t + ', '
                            tarray.append(t)
                        else:
                            reply_good = False
                        i+=1
                    if len(tarray)>0:
                        reply += '{}: {}\n'.format(o, ', '.join(tarray))
                    #i+=1
                if reply=='':
                    reply = 'No one :('
            embed.add_field(name='Wants', value=reply, inline=False)
            embed.set_footer(text=sender)
            await self.message.edit(new_content='', embed=embed)
            if page > 1:
                await self.message.add_reaction('\N{LEFTWARDS BLACK ARROW}')
            await self.message.add_reaction(pages[page])
            if not reply_good:
                await self.message.add_reaction('\N{BLACK RIGHTWARDS ARROW}')
        elif type=='Haves':
            i = 0
            for k in range(page):
                reply = ''
                reply_good = True
                while i < len(matches_w_h) and reply_good:
                    o = matches_w_h[i]['owner']
                    theirs = ''
                    tarray = []
                    while i < len(matches_w_h) and matches_w_h[i]['owner']==o and reply_good:
                        m = matches_w_h[i]
                        t = self.getPokeString(m)
                        if len(reply + theirs + t + ', ')<900:
                            theirs += t
                            tarray.append(t)
                        else:
                            reply_good = False
                        i+=1
                    if len(tarray)>0:
                        reply += '{}: {}\n'.format(o, ', '.join(tarray))
                    #i+=1
                if reply=='':
                    reply = 'No one :('
            embed.add_field(name='Haves', value=reply, inline=False)
            embed.set_footer(text=sender)
            await self.message.edit(new_content='', embed=embed)
            if page > 1:
                await self.message.add_reaction('\N{LEFTWARDS BLACK ARROW}')
            await self.message.add_reaction(pages[page])
            if not reply_good:
                await self.message.add_reaction('\N{BLACK RIGHTWARDS ARROW}')
        elif type=='Super Matches':
            super_matches_sorted = sorted(super_matches, key=lambda k:k[0]['owner'])
            i = 0
            for k in range(page):
                reply = ''
                reply_good = True
                while i < len(super_matches_sorted) and reply_good:
                    o = super_matches_sorted[i][0]['owner']
                    theirs = []
                    yours = []
                    while i < len(super_matches_sorted) and super_matches_sorted[i][0]['owner']==o and reply_good:
                        m = super_matches_sorted[i]
                        t = self.getPokeString(m[0])
                        if t not in theirs:
                            theirs.append(t)
                        y = self.getPokeString(m[1])
                        if y not in yours:
                            yours.append(y)
                        i+=1
                    r = '{}\'s {} <-> {}\n'.format(o, ', '.join(theirs), ', '.join(yours))
                    if len(r+reply)<900:
                        reply += r
                    else:
                        reply_good = False
                if reply=='':
                    reply = 'No one :('
            embed.add_field(name='Super Matches', value=reply, inline=False)
            embed.set_footer(text=sender)
            await self.message.edit(new_content='', embed=embed)
            if page > 1:
                await self.message.add_reaction('\N{LEFTWARDS BLACK ARROW}')
            await self.message.add_reaction(pages[page])
            if not reply_good:
                await self.message.add_reaction('\N{BLACK RIGHTWARDS ARROW}')

    async def doMatch(self, content):
        sender = self.message.author.name
        if self.message.author.id==81881597757882368 and len(content)>0 and content != "shiny":
            sender = content
        sender_haves = self.getEntriesFromUser(sender, self.haves)
        sender_wants = self.getEntriesFromUser(sender, self.wants)
        if content=="shiny":
            sender_haves = [h for h in sender_haves if h["shiny"]]
            sender_wants = [w for w in sender_wants if w["shiny"]]
        matches_h_w = []
        for hi in self.haves:
            if hi['active']==False:
                continue
            for hj in sender_wants:
                if hj['active']==False:
                    continue
                if hi['owner']!=hj['owner']:
                    if hi['pokemon']==hj['pokemon'] and hi['shiny']==hj['shiny'] and hi['legacy']==hj['legacy'] and hi['event']==hj['event'] and (hi not in matches_h_w):
                        matches_h_w.append(hi)

        #matches_h_w = matches_h_w.sort(key=lambda k:k['owner'])
        #print(matches_h_w)

        matches_w_h = []
        for hi in self.wants:
            if hi['active']==False:
                continue
            for hj in sender_haves:
                if hj['active']==False:
                    continue
                if hi['owner']!=hj['owner']:
                    if hi['pokemon']==hj['pokemon'] and hi['shiny']==hj['shiny'] and hi['legacy']==hj['legacy'] and hi['event']==hj['event'] and (hi not in matches_w_h):
                        matches_w_h.append(hi)


        newh = []
        neww = []
        super_matches = []
        for h in matches_h_w:
            for w in matches_w_h:
                if h['owner']==w['owner']:
                    super_matches.append((h, w))

        for s in super_matches:
            newh.append(s[0])
            neww.append(s[1])

        nh = [h for h in matches_h_w if h not in newh]
        nw = [h for h in matches_w_h if h not in neww]

        matches_h_w = sorted(nh, key=lambda k:k['owner'].lower())
        matches_w_h = sorted(nw, key=lambda k:k['owner'].lower())

        embed = discord.Embed()

        '''if self.message.author.avatar_url=='':
            embed.set_thumbnail(url=self.message.author.default_avatar_url)
        else:
            embed.set_thumbnail(url=self.message.author.avatar_url)
        embed.set_author(name=self.message.author.name)'''

        reply = ''
        i = 0
        reply_good = True
        while i < len(matches_h_w) and reply_good:
            o = matches_h_w[i]['owner']
            theirs = ''
            tarray = []
            while i < len(matches_h_w) and matches_h_w[i]['owner']==o and reply_good:
                m = matches_h_w[i]
                t = self.getPokeString(m)
                if len(reply + theirs + t + ', ')<900:
                    theirs += t + ', '
                    tarray.append(t)
                else:
                    reply_good = False
                i+=1
            if len(tarray)>0:
                reply += '{}: {}\n'.format(o, ', '.join(tarray))
            #i+=1
        if reply=='':
            reply = 'No one :('
        embed.add_field(name='Wants', value=reply, inline=False)
        embed.set_footer(text=sender)
        m = await self.message.channel.send(content='', embed=embed)
        if not reply_good:
            await m.add_reaction('1⃣')
            await m.add_reaction('\N{BLACK RIGHTWARDS ARROW}')

        embed = discord.Embed()
        reply = ''
        i = 0
        reply_good = True
        while i < len(matches_w_h) and reply_good:
            o = matches_w_h[i]['owner']
            theirs = ''
            tarray = []
            while i < len(matches_w_h) and matches_w_h[i]['owner']==o and reply_good:
                m = matches_w_h[i]
                t = self.getPokeString(m)
                if len(reply + theirs + t + ', ') < 900:
                    theirs += t
                    tarray.append(t)
                else:
                    reply_good = False
                i+=1
            if len(tarray)>0:
                reply += '{}: {}\n'.format(o, ', '.join(tarray))
            #i+=1
        if reply=='':
            reply = 'No one :('
        embed.add_field(name='Haves', value=reply, inline=False)
        embed.set_footer(text=sender)
        m = await self.message.channel.send(content='', embed=embed)
        if not reply_good:
            await m.add_reaction('1⃣')
            await m.add_reaction('\N{BLACK RIGHTWARDS ARROW}')
            #await m.add_reaction('\N{LEFTWARDS BLACK ARROW}')

        embed = discord.Embed()
        reply = ''
        super_matches_sorted = sorted(super_matches, key=lambda k:k[0]['owner'])
        i = 0
        reply_good = True
        while i < len(super_matches_sorted) and reply_good:
            o = super_matches_sorted[i][0]['owner']
            theirs = []
            yours = []
            while i < len(super_matches_sorted) and super_matches_sorted[i][0]['owner']==o and reply_good:
                m = super_matches_sorted[i]
                t = self.getPokeString(m[0])
                if t not in theirs:
                    theirs.append(t)
                y = self.getPokeString(m[1])
                if y not in yours:
                    yours.append(y)
                i+=1
            r = '{}\'s {} <-> {}\n'.format(o, ', '.join(theirs), ', '.join(yours))
            if len(r+reply)<900:
                reply += r
            else:
                reply_good = False
            #i+=1
        if reply=='':
            reply = 'No one :('
        embed.add_field(name='Super Matches', value=reply, inline=False)
        embed.set_footer(text=sender)
        m = await self.message.channel.send(content='', embed=embed)
        if not reply_good:
            await m.add_reaction('1⃣')
            await m.add_reaction('\N{BLACK RIGHTWARDS ARROW}')

    def getPokeString(self, d):
        ret = ''
        if 'shiny' in d and d['shiny']:
            ret += 'Shiny '
        if 'event' in d and d['event']:
            ret += 'Event '
        if 'legacy' in d and d['legacy']:
            ret += 'Legacy '
        return ret + d['pokemon']

    async def doProfile(self, content):
        sender = self.message.author.name
        if self.message.author.id==81881597757882368 and len(content)>0:
            sender = content
        sender_haves = sorted(self.getEntriesFromUser(sender, self.haves), key=lambda k:k['pokemon'].lower())
        sender_wants = sorted(self.getEntriesFromUser(sender, self.wants), key=lambda k:k['pokemon'].lower())
        embed = discord.Embed()
        if self.message.author.name==sender:
            if self.message.author.avatar_url=='':
                embed.set_thumbnail(url=self.message.author.default_avatar_url)
            else:
                embed.set_thumbnail(url=self.message.author.avatar_url)
        embed.set_author(name=sender)
        reply = ''
        for m in sender_wants:
            if len(reply) > 1000:
                break
            if m['active']:
                reply += '{}\n'.format(self.getPokeString(m))
        if reply=='':
            reply = 'Nothing'
        embed.add_field(name='What you want:', value=reply, inline=False)
        await self.message.channel.send(content='', embed=embed)

        # Send separately becauase it could be too big
        embed = discord.Embed()
        embed.set_author(name=sender)
        reply = ''
        for m in sender_haves:
            if len(reply) > 1000:
                break
            if m['active']:
                reply += '{}\n'.format(self.getPokeString(m))
        if reply=='':
            reply = 'Nothing'
        embed.add_field(name='What you have:', value=reply, inline=False)
        await self.message.channel.send(content='', embed=embed)

    def getEntriesFromUser(self, user, list):
        return [l for l in list if l['owner'].lower()==user.lower()]

    def scorePokemon(self, p1, p2):
        sh1 = int(p1['shiny'])
        sh2 = int(p2['shiny'])
        a1 = int(p1['stats']['ATK'])
        a2 = int(p2['stats']['ATK'])
        d1 = int(p1['stats']['DEF'])
        d2 = int(p2['stats']['DEF'])
        s1 = int(p1['stats']['STA'])
        s2 = int(p2['stats']['STA'])
        cr1 = int(p1['stats']['capture_rate'])
        cr2 = int(p2['stats']['capture_rate'])
        inputs = [sh1, sh2, a1, a2, d1, d2, s1, s2, cr1, cr2]
        print(inputs)
        score = self.nn.feedforward(inputs)
        return score
