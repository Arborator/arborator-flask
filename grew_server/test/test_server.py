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

# print ("\n***************************************************************************\n")
# print ('========== [newProject]')
# print ('       ... project_id -> proj_1')
# reply = send_request ('newProject', data={'project_id': 'proj_1'})
# print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_t6')
# reply = send_request ('newSample', data={'project_id': 'proj_1', 'sample_id': 'sample_t6' })
# print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_t6')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-test_00006.conllu')
# with open('data/fr_gsd-ud-test_00006.conllu', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_1', 'sample_id': 'sample_t6', 'user_id': 'kim' },
# #        data = {'project_id': 'proj_1', 'sample_id': 'sample_t6' },
#         files={'conll_file': f},
#     )
#     print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# reply = send_request ('newSample', data={'project_id': 'proj_1', 'sample_id': 'sample_01_to_10' })
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-train_00001_00010.conllu')
# with open('data/fr_gsd-ud-train_00001_00010.conllu', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_1', 'sample_id': 'sample_01_to_10', 'user_id': '_base' },
#         files={'conll_file': f},
#     )
#     print (reply)




# print ("\n***************************************************************************\n")
# print ('========== [newProject]')
# print ('       ... project_id -> proj_2')
# reply = send_request ('newProject', data={'project_id': 'proj_2'})
# print (reply)

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_11_to_20')
# reply = send_request ('newSample', data={'project_id': 'proj_2', 'sample_id': 'sample_11_to_20' })
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_11_to_20')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-train_00011_00020.conllu')
# with open('data/fr_gsd-ud-train_00011_00020.conllu', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_2', 'sample_id': 'sample_11_to_20', 'user_id': '_base' },
#         files={'conll_file': f},
#     )
#     print (reply)

# print ("\n***************************************************************************\n")

# print ("\n***************************************************************************\n")
# print ('========== [newSample]')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_21_to_30')
# reply = send_request ('newSample', data={'project_id': 'proj_2', 'sample_id': 'sample_21_to_30' })
# print (reply)

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_2')
# print ('       ... sample_id -> sample_21_to_30')
# print ('       ... user_id -> _base')
# print ('       ... conll_file -> data/fr_gsd-ud-train_00021_00030.conllu')
# with open('../../vieux/grew_server/test/data/kisspetit', 'rb') as f:
#     reply = send_request (
#         'saveConll',
#         data = {'project_id': 'proj_1', 'sample_id': 'kisspetit', 'user_id': 'rinema56@gmail.com'  },
#         files={'conll_file': f},
#     )
#     print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [saveConll] ')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# print ('       ... conll_graph -> data/bruno.conll')
# reply = send_request (
#     'saveConll',
#     data = {'project_id': 'proj_1', 'sample_id': 'sample_01_to_10' },
#     files={'conll_file': f},
# )
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getProjects]')
# reply = send_request ('getProjects')
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getSamples]')
# print ('       ... project_id -> proj_1')
# reply = send_request ('getSamples', data={'project_id': 'proj_1'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getSentences]')
# print ('       ... project_id -> proj_1')
# print ('       ... pattern -> "pattern {N[user, upos = NOUN]}"')
# reply = send_request ('getSentences', data={'project_id': 'proj_1', 'pattern': 'pattern {N[user, upos = NOUN]}'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [eraseSample]')
# print ('       ... project_id -> proj_1')
# print ('       ... sample_id -> sample_01_to_10')
# reply = send_request ('eraseSample', data={'project_id': 'proj_1', 'sample_id': 'sample_01_to_10'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [getSamples]')
# print ('       ... project_id -> proj_1')
# reply = send_request ('getSamples', data={'project_id': 'proj_1'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [eraseProject]')
# print ('       ... project_id -> proj_2')
# reply = send_request ('eraseProject', data={'project_id': 'Marine test 2'})
# print (reply)

# print ("\n***************************************************************************\n")

# print ('========== [renameProject]')
# reply = send_request ('renameProject', data={'project_id': 'Naijaa', "new_project_id":"Naija"})
# print (reply)

# print ("\n***************************************************************************\n")

print ('========== [getProjects]')
reply = send_request ('getProjects')
print (reply)

# print ('========== [getSamples]')
# print ('       ... project_id -> French')
# reply = send_request ('getSamples', data={'project_id': 'French'})
# print (reply)

# print ('========== [getSamples]')
# print ('       ... project_id -> Naija')
# reply = send_request ('getSamples', data={'project_id': 'Naija'})
# print (reply)

# print ('========== [getConll]')
# reply = send_request ('getConll', data={'project_id':'FrenchTest', "sample_id":'peripitiesVoiture'})
# print (reply)



# print ('========== [getUsers]')
# reply = send_request ('getUsers', data={'project_id':'proj_1', "sample_id":'sample_t6'})
# print (reply)

