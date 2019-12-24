#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os
     
#sys.path.append('/home/arborator/www/arboratorgrew/arborator-flask')

#from run import app as application 
from app import create_app
#config_name = os.getenv('FLASK_CONFIG')
application = create_app('production')
application.debug = True
#app = create_app(debug=False)
#app = create_app('development')

print(11111111111111111111111111111)

#app.run(host='0.0.0.0', port=5000)
#app.run(host='localhost', port=5000)
