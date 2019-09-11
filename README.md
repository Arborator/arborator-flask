# Arborator-Flask
This a flask port of the [arborator-server](https://github.com/Arborator/arborator-server) as commisioned by [Kim Gerdes](https://github.com/kimgerdes)

* `export FLASK_CONFIG=development; export FLASK_APP=run.py`

# Development
To create database
* `flask db init`
init créé le dossier migration (pas la peine de relancer chaque fois)

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

# 2019
installer :  
	sudo apt install python3-flask python3-pip
	pip3 install --user -r requirements.txt 
	pip3 install --user  futures flask_sqlalchemy flask_migrate flask_login sqlalchemy_utils flask_wtf authomatic flask_bootstrap


si problème : 
	sudo pip3 uninstall flask_sqlalchemy flask_migrate flask_login sqlalchemy_utils flask_wtf authomatic flask_bootstrap
	sudo pip3 install flask_sqlalchemy flask_migrate flask_login sqlalchemy_utils flask_wtf authomatic flask_bootstrap
	
faire tourner :
	export FLASK_APP=run.py; export FLASK_CONFIG=development; flask run
	
	
structure : 
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

pip3 install sqlathanor