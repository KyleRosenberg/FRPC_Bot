from PIL import Image, ImageEnhance, ImageFilter
from pytesseract import image_to_string
from pytesseract import image_to_data
import json
import numpy as np
import re
import requests
from io import BytesIO

with open('pokemon.json') as f:
    data = json.load(f)
    pokedata = data['pokemon']
    cpm = data['cpm']


imageurl = 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/1.png'
response = requests.get(imageurl)
i1 = Image.open(BytesIO(response.content))
i1 = i1.convert("P", colors=3)
print(i1.getpalette())

i = Image.open('testimage3.png')
i = i.convert('L')                             # grayscale
i = i.filter(ImageFilter.MedianFilter())       # a little blur
i = i.point(lambda x: 0 if x < 150 else 255)   # threshold (binarize)
i = i.resize((750, 1334))
w, h = i.size
cpi = i.crop((w/3-10, h/15, 2*w/3, 11*h/100))
cpi.save('cp.png')
cp = image_to_string(cpi)
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
                if abs(int(pcp)-int(cp))<5:
                    print(pcp)
                    print('Match: {}, {}, {}: {:.2f}%, level {}'.format(i, j, k, (i+k+j)/45*100, ind/2+1))
