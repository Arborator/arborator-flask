# Arborator-Flask
This the back-end of the Arborator-Grew redevelopement of the [arborator-server](https://github.com/Arborator/arborator-server).

# installation

```sh
git clone git@github.com:Arborator/arborator-flask.git
cd arborator-flask
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


# run locally

`export FLASK_APP=run.py; export FLASK_CONFIG=development; flask run --cert=adhoc`

### in case of problems try: 
```shell
sudo pip3 uninstall flask_sqlalchemy flask_migrate flask_login sqlalchemy_utils flask_wtf authomatic flask_bootstrap
sudo pip3 install flask_sqlalchemy flask_migrate flask_login sqlalchemy_utils flask_wtf authomatic flask_bootstrap
pip3 install sqlathanor
pip3 install flask-cors
pip3 install pyopenssl
```
	
-------------


# deployment

**Goal**: install arborator-flask so that it servers in httpS on https://arboratorgrew.xxx.fr:5000/api/home/projects/

[This](https://medium.com/@thucnc/deploy-a-python-flask-restful-api-app-with-gunicorn-supervisor-and-nginx-62b20d62691f) and [this](https://serverfault.com/questions/828130/how-to-run-nginx-ssl-on-non-standard-port) helped a lot.

Internally, flask will run on 5001. Externally it will run on 5000

## Preparation
New server arboratorgrew.xxx.fr (small vps)

### As root:
```
ssh root@arboratorgrew.xxx.fr
adduser arborator
```

nginx installed?
Use arborator-flask/deployment/arborator-flask.nginx.conf
`service nginx restart`

supervisor installed?
```
apt install supervisor
cp deployment/arborator-flask.conf /etc/supervisor/conf.d/`
certbot installed?
apt-get install certbot python-certbot-nginx
certbot --nginx
Toutes les module python installed?
python3 -m pip install flask_sqlalchemy flask_migrate flask_login sqlalchemy_utils flask_wtf authomatic flask_bootstrap flask-cors pyopenssl uwsgi
```

### As arborator:
```
ssh arborator@arboratorgrew.xxx.fr
git clone https://github.com/Arborator/arborator-flask.git
cd /home/arborator/arborator-flask/
```

### For testing:
```
python3 wsgi.py
gunicorn -b localhost:5001 -w 4 wsgi
(by default it looks for “application”. If it’s not called “application”, add it: gunicorn -b localhost:5001 -w 4 wsgi:myapp)
gunicorn -c gunicorn.conf.py wsgi
```

### Start
```
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl avail
sudo supervisorctl restart arborator-flask
```


### Check and debug
Is it working on https://arboratorgrew.xxx.fr:5000/api/home/projects/ ?
Test locally with
`curl localhost:5001/api/home/projects/`

Check who’s running on port 5000 and 5001: 
```
lsof -i:5000
lsof -i:5001
```

From remote (note that strangely, it doesn’t work with https as in the browser)
`curl http://arboratorgrew.xxx.fr:5000/api/home/projects/`


If address already in use for second run: 
```
killall python3
killall gunicorn
```

### Deploy a New Version

#### Backend flask

1. As arborator (ssh arborator@arboratorgrew.xxx.fr):
```
cd arborator-flask
git pull origin master
```

2. Then as root:
```
supervisorctl restart arborator-flask
```

3. And, as root, watch the logs in real time to see if any errors occurred: 
```
tail -f /var/log/nginx/arborator-flask.log
```




-------------



	
# structure
	deux routes : 
	home/views : 
			/ (rien) --> template : home/index.html
			/q --> template: home/quickie.html
	auth/views : /login etc
	
authomatic:
	auth/views.py
	auth/auth_config.py : par provider 
	

modif
	

new install :




# Development
To create database
* `flask db init`
init créé le dossier migration (pas la peine de relancer chaque fois)

* `flask db stamp head`
* `flask db migrate`
si on a modifié models.py, il crée une nouveau script 123456xxxx.py dans migrations/versions

* `flask db upgrade`
s'il y a un nouveau script dans migrations/versions il crée une meilleure version de la bdd, en conservant toute info encore utile.
le nom et l'emplacement de la base est dans config.py


Then run

* `set FLASK_CONFIG = development; set FLASK_APP = run.py; flask run`



## TODO
* Login form for site admins(testing purposes also)
* Complete project functions conversions (25/5/18)
* Set redirect urls for oauth providers
* in-app edit of project config(ini) files or find alternative
* correct dead links on project page
* css corrections/additions/subtractions 


Check out the guide on the [Wiki page](https://github.com/Arborator/arborator-server/wiki).

