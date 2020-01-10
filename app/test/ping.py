import requests

try:
    r = requests.post('http://arborator.grew.fr')
    if (r.text != ""):
        exit (1)
except Exception as e:
    exit (1)
