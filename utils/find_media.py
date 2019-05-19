#!/usr/bin/env python3

import os
import urllib.parse

from collections import OrderedDict

dirs = {'Movie' : '/amaroq/media/movies',
        'Video' : '/amaroq/media/videos'}

lst = {}

for tk,tv in dirs.items():
    data = {r:(r,d,f) for r,d,f in os.walk(tv)}
    data = OrderedDict(sorted(data.items(), key=lambda s: s[0].casefold()))

    for dk,dv in data.items():
        r,d,f = dv
        urb = r.replace('/amaroq','')
        #nb  = r.replace(tv,'').replace('/',' ')
        nb  = r.replace(tv,'')

        for file in f:
            if file[0] != ".":
                k = '{} - {}/{}'.format(tk,nb,os.path.splitext(file)[0].replace(':',' '))
                v = 'http://172.16.20.1{}/{}'.format(urb,urllib.parse.quote(file))
                lst[k] = v

with open('/amaroq/hass/config/media.yaml','w') as mf:
    for k,v in lst.items():
        mf.write('- name: {}\n'.format(k))
        mf.write('  type: video\n')
        mf.write('  id: {}\n'.format(v))

