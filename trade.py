from utility import similarityDistance
import numpy as np
import re
import json
import discord
import datetime
import pytz

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
            with open('{}.json'.format(self.message.server.id)) as f:
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

        with open('{}.json'.format(self.message.server.id), 'w') as f:
            json.dump({
                'haves': self.haves,
                'wants': self.wants
            }, f)


    async def doCommand(self):
        content = self.content
        firstspace = content.find(' ', 4)
        if firstspace==-1:
            firstspace=len(content)
        command = content[:firstspace]
        rest = content[firstspace+1 :]
        coms = ['.trade', '.want', '.unwant', '.have', '.unhave', '.match', '.profile']
        funcs = [self.doTrade, self.doWant, self.doUnWant, self.doHave, self.doUnHave, self.doMatch, self.doProfile]
        scores = [similarityDistance(command, i)/len(command) for i in coms]
        lowest = np.min(scores)
        index = np.argmin(scores)
        if lowest > 0.15:
            pass
            '''
            con = 'Command not recognized {} {}'.format(command, self.message.author.mention)
            await self.client.send_message(self.message.channel, content=con)
            '''
        else:
            if index >=0 and index<len(funcs):
                await funcs[index](rest)
            else:
                await self.client.send_message(self.message.channel, content='This error shouldn\'t happen. Command not matched.')

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
        return pokemon

    def sameDict(self, a, b):
        if len(a)!=len(b):
            return False
        for k in a:
            if k not in b:
                return False
            if a[k]!=b[k] and k!='active':
                return False
        return True

    async def doTrade(self, content):
        p = re.compile('(shiny )?(.+), ?(shiny )?(.+)')
        m = p.search(content)
        #TODO: Convert to findall maybe
        s1 = str(m.group(1))
        p1 = str(m.group(2))
        s2 = str(m.group(3))
        p2 = str(m.group(4))
        best1 = None
        bs1 = np.infty
        best2 = None
        bs2 = np.infty
        for p in self.pokedata:
            sc1 = similarityDistance(p1, p['names'][1].lower())
            sc2 = similarityDistance(p2, p['names'][1].lower())
            if sc1 < bs1:
                bs1 = sc1
                best1 = p
            if sc2 < bs2:
                bs2 = sc2
                best2 = p
        score1 = self.scorePokemon(best1, s1)
        score2 = self.scorePokemon(best2, s2)
        reply = '{} worth {} for {} worth {}'.format(best1['names'][1], score1, best2['names'][1], score2)
        await self.client.send_message(self.message.channel, content=reply)

    async def doHave(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.client.add_reaction(self.message, '👎')
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
                    await self.client.add_reaction(self.message, '👍')
                else:
                    await self.client.add_reaction(self.message, '👊')
                with open('{}.json'.format(self.message.server.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
                #await self.client.add_reaction(self.message, '👍')
        except:
            log('Exception in doHave')
            await self.client.add_reaction(self.message, '👎')

    async def doUnHave(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.client.add_reaction(self.message, '👎')
            else:
                had = False
                for h in self.haves:
                    if self.sameDict(h, d):
                        h['active']=False
                        had = True
                        break
                if had:
                    await self.client.add_reaction(self.message, '👍')
                else:
                    await self.client.add_reaction(self.message, '👊')
                with open('{}.json'.format(self.message.server.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
        except:
            log('Exception in doHave')
            await self.client.add_reaction(self.message, '👎')

    async def doWant(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.client.add_reaction(self.message, '👎')
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
                    await self.client.add_reaction(self.message, '👍')
                else:
                    await self.client.add_reaction(self.message, '👊')
                with open('{}.json'.format(self.message.server.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
                #await self.client.add_reaction(self.message, '👍')
        except:
            log('Exception in doHave')
            await self.client.add_reaction(self.message, '👎')

    async def doUnWant(self, content):
        try:
            d = self.getPokemonDetails(content)
            if d == None:
                await self.client.add_reaction(self.message, '👎')
            else:
                had = False
                for h in self.wants:
                    if self.sameDict(h, d):
                        h['active']=False
                        had = True
                        break
                if had:
                    await self.client.add_reaction(self.message, '👍')
                else:
                    await self.client.add_reaction(self.message, '👊')
                with open('{}.json'.format(self.message.server.id), 'w') as f:
                    json.dump({
                        'haves': self.haves,
                        'wants': self.wants
                    }, f)
        except:
            log('Exception in doHave')
            await self.client.add_reaction(self.message, '👎')

    async def doEditMatch(self, reaction):
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
        if reaction.emoji == '➡':
            page+=1
        else:
            page-=1
        for r in self.message.reactions:
            reactors = await self.client.get_reaction_users(r)
            for re in reactors:
                await self.client.remove_reaction(self.message, r.emoji, re)
        e = self.message.embeds[0]
        sender = e['footer']['text']
        type = e['fields'][0]['name']
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
        if type=='People that Have what you Want':
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
                        if len(reply + theirs + t + ', ')<1000:
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
            embed.add_field(name='People that Have what you Want', value=reply, inline=False)
            embed.set_footer(text=sender)
            m = await self.client.edit_message(self.message, new_content='', embed=embed)
            if page > 1:
                await self.client.add_reaction(m, '\N{LEFTWARDS BLACK ARROW}')
            await self.client.add_reaction(m, pages[page])
            if not reply_good:
                await self.client.add_reaction(m, '\N{BLACK RIGHTWARDS ARROW}')
        elif type=='People that Want what you Have':
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
                        if len(reply + theirs + t + ', ')<1000:
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
            embed.add_field(name='People that Want what you Have', value=reply, inline=False)
            embed.set_footer(text=sender)
            m = await self.client.edit_message(self.message, new_content='', embed=embed)
            if page > 1:
                await self.client.add_reaction(m, '\N{LEFTWARDS BLACK ARROW}')
            await self.client.add_reaction(m, pages[page])
            if not reply_good:
                await self.client.add_reaction(m, '\N{BLACK RIGHTWARDS ARROW}')
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
                    if len(r+reply)<1000:
                        reply += r
                    else:
                        reply_good = False
                if reply=='':
                    reply = 'No one :('
            embed.add_field(name='Super Matches', value=reply, inline=False)
            embed.set_footer(text=sender)
            m = await self.client.edit_message(self.message, new_content='', embed=embed)
            if page > 1:
                await self.client.add_reaction(m, '\N{LEFTWARDS BLACK ARROW}')
            await self.client.add_reaction(m, pages[page])
            if not reply_good:
                await self.client.add_reaction(m, '\N{BLACK RIGHTWARDS ARROW}')

    async def doMatch(self, content):
        sender = self.message.author.name
        if self.message.author.id=='81881597757882368' and len(content)>0:
            sender = content
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
                if len(reply + theirs + t + ', ')<1000:
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
        embed.add_field(name='People that Have what you Want', value=reply, inline=False)
        embed.set_footer(text=sender)
        m = await self.client.send_message(self.message.channel, content='', embed=embed)
        if not reply_good:
            await self.client.add_reaction(m, '1⃣')
            await self.client.add_reaction(m, '\N{BLACK RIGHTWARDS ARROW}')

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
                if len(reply + theirs + t + ', ')<1000:
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
        embed.add_field(name='People that Want what you Have', value=reply, inline=False)
        embed.set_footer(text=sender)
        m = await self.client.send_message(self.message.channel, content='', embed=embed)
        if not reply_good:
            await self.client.add_reaction(m, '1⃣')
            await self.client.add_reaction(m, '\N{BLACK RIGHTWARDS ARROW}')
            #await self.client.add_reaction(m, '\N{LEFTWARDS BLACK ARROW}')

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
            if len(r+reply)<1000:
                reply += r
            else:
                reply_good = False
            #i+=1
        if reply=='':
            reply = 'No one :('
        embed.add_field(name='Super Matches', value=reply, inline=False)
        embed.set_footer(text=sender)
        m = await self.client.send_message(self.message.channel, content='', embed=embed)
        if not reply_good:
            await self.client.add_reaction(m, '1⃣')
            await self.client.add_reaction(m, '\N{BLACK RIGHTWARDS ARROW}')

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
        if self.message.author.id=='81881597757882368' and len(content)>0:
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
            if m['active']:
                reply += '{}\n'.format(self.getPokeString(m))
        if reply=='':
            reply = 'Nothing'
        embed.add_field(name='What you want:', value=reply, inline=False)
        reply = ''
        for m in sender_haves:
            if m['active']:
                reply += '{}\n'.format(self.getPokeString(m))
        if reply=='':
            reply = 'Nothing'
        embed.add_field(name='What you have:', value=reply, inline=False)
        await self.client.send_message(self.message.channel, content='', embed=embed)

    def getEntriesFromUser(self, user, list):
        return [l for l in list if l['owner'].lower()==user.lower()]

    def scorePokemon(self, pokemon, shiny):
        score = 0
        score += int(pokemon['rank'])
        if shiny=='shiny ':
            score += 1
        return score
