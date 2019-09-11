#!/usr/bin/env python3

import sys
import requests

if (len(sys.argv) > 1 and sys.argv[1] == "local"):
    server = 'http://localhost:8080'
else:
    server = 'http://arborator.grew.fr'

def send_request(fct_name, data={}, files={}):
    try:
        r = requests.post(
            "%s/%s" % (server,fct_name),
            files = files,
            data = data
        )
        return r.text
    except requests.ConnectionError:
        print ("Connection refused")
    except Exception as e:
        print ("Uncaught exception, please report %s" % e)

print ('========== [newProject]')
print ('       ... project_id -> main')
reply = send_request ('newProject', data={'project_id': 'main'})
print (reply)

print ('========== [newSample]')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
reply = send_request ('newSample', data={'project_id': 'main', 'sample_id': 'licorne' })
print (reply)

print ('========== [saveConll] ')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
print ('       ... conll_file -> all.conll')
with open('all.conll', 'rb') as f:
    reply = send_request (
        'saveConll',
        data = {'project_id': 'main', 'sample_id': 'licorne' },
        files={'conll_file': f},
    )
    print (reply)

print ("\n***************************************************************************\n")

for pat_file in ['diff_pos.pat', 'diff_label.pat', 'diff_gov.pat', 'usual.pat']:
    print ('========== [getSentences]')
    print ('       ... project_id -> main')
    print ('       ... pattern -> %s' % pat_file)
    with open('%s' % pat_file, 'rb') as f:
        pattern = f.read()
        reply = send_request (
            'getSentences',
            data = {
                'project_id': 'main',
                'pattern': pattern
            }
        )
        print (reply)

print ("\n***************************************************************************\n")

print ('========== [getUsers]')
print ('       ... project_id -> main')
reply = send_request ('getUsers', data={'project_id': 'main'})
print (reply)

print ("\n***************************************************************************\n")

print ('========== [getUsers]')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
reply = send_request ('getUsers', data={'project_id': 'main', 'sample_id': 'licorne'})
print (reply)

print ("\n***************************************************************************\n")

print ('========== [getUsers]')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
print ('       ... sent_id -> lic_001')
reply = send_request ('getUsers', data={'project_id': 'main', 'sample_id': 'licorne', 'sent_id': 'lic_001'})
print (reply)

print ("\n***************************************************************************\n")

print ('========== [getConll]')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
print ('       ... sent_id -> lic_001')
print ('       ... user_id -> kim')
reply = send_request ('getConll', data={'project_id': 'main', 'sample_id': 'licorne', 'sent_id': 'lic_001', 'user_id': 'kim'})
print (reply)

print ("\n***************************************************************************\n")

print ('========== [getConll]')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
print ('       ... sent_id -> lic_001')
reply = send_request ('getConll', data={'project_id': 'main', 'sample_id': 'licorne', 'sent_id': 'lic_001'})
print (reply)

print ("\n***************************************************************************\n")

print ('========== [getConll]')
print ('       ... project_id -> main')
print ('       ... sample_id -> licorne')
reply = send_request ('getConll', data={'project_id': 'main', 'sample_id': 'licorne'})
print (reply)
