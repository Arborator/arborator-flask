from flask import Flask, render_template, request, make_response, session, redirect, flash, url_for, Response
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic
from flask_login import login_required, login_user, logout_user
from ....app import db
from datetime import datetime
from . import auth
from ...models.models import User, load_user, AlchemyEncoder
from .auth_config import CONFIG
from ....config import Config
import json
import requests

# added alternative imports in case of errors (to cure later on)
from functools import wraps
from authomatic.extras.flask import FlaskAuthomatic




authomatic = Authomatic(CONFIG, Config.SECRET_KEY, report_errors=True)
# added alternative in case of errors (to cure later on)
# authomatic = FlaskAuthomatic(CONFIG, Config.SECRET_KEY, session_max_age=600, secure_cookie=True, session=None, session_save_method=None, report_errors=True, debug=False, logging_level=20, prefix='authomatic', logger=None)

# à virer à terme (faire en quasar)
@auth.route('/auth')
def choose_provider():
    """
    Login Providers Page Handler
    """
    return render_template('auth/index.html')


def parse_user(provider_name, user):
    results_parsed = {}

    if provider_name == "github":
        access_token = user.data.get("access_token")
        data = get_username(access_token, "github")
        results_parsed["id"] = data.get("id")
        results_parsed["username"] = data.get("login")
        results_parsed["picture_url"] = data.get("avatar_url")
        results_parsed["email"] = data.get("email")

    elif provider_name == "google":
        results_parsed["id"] = user.email
        results_parsed["username"] = user.email.split('@')[0]
        results_parsed["email"] = user.email
        results_parsed["first_name"]= user.first_name
        results_parsed["family_name"] = user.last_name
        results_parsed["picture_url"] = user.picture
        
    return results_parsed
     

def get_username(access_token, provider_name):
    if provider_name == "github":
        headers = {"Authorization": "bearer " + access_token}
        response = requests.get("https://api.github.com/user", headers=headers)
        data = response.json()
        return data
    else:
        abort(404)




@auth.route('/login/<provider_name>/', methods=['GET', 'POST'])
def login(provider_name):
    """
    Login handler.
    """   
    # We need response object for the WerkzeugAdapter.
    response = make_response()

    # Log the user in, pass it the adapter and the provider name.
    result = authomatic.login(WerkzeugAdapter(request, response), provider_name)

    #####Sessions!! coming back
        # session=session,
        # session_saver=lambda: app.save_session(session, response))

    # If there is no LoginResult object, the login procedure is still pending.
    if result:
        if result.error:
            print("Error: {}".format(result.error))
            abort(500)
  
        if result.user:
            if provider_name == "google":
                result.user.update() # specific to google, we need to update the user to get more info.
            else:
                pass
            results_parsed = parse_user(provider_name, result.user) # parse the format specific to each provider

            #save user id to session
            user = User.query.filter_by(id=results_parsed.get("id")).first()
            # session['email'] = result.user.email
            if user is None:

                username = results_parsed.get("username")
                username = User.make_valid_nickname(username)
                username = User.make_unique_nickname(username)

                ##Save UserDetails To Db
                user, created = User.get_or_create(
                        db.session, 
                        id = results_parsed["id"],
                        auth_provider = result.user.provider.id,
                        username = results_parsed.get("username"),
                        #email=result.user.email,
                        first_name=results_parsed.get("first_name"),
                        family_name=results_parsed.get("family_name"),
                        picture_url=results_parsed.get("picture_url"),
                        super_admin=False,
                        created_date=datetime.utcnow(),
                        last_seen=datetime.utcnow()
                    )

            User.setPictureUrl(db.session, user.username, results_parsed.get("picture_url")) # always get the lastest picture on login

            login_user(user, remember=True)
            session['logged_in']=True ### ?????
            
            if not User.query.filter_by(super_admin=True).first():
                print("firstsuper")
                return render_template('admin/firstsuper.html')
           
            js = json.dumps(user.as_json(), default=str)
            resp = Response(js, status=200,  mimetype='application/json')
            return render_template('home/redirect.html', response=resp)

    return response


@auth.route('/login/userinfos', methods=['GET', 'POST'])
def getUserInfos():
    # print(session)
    user_id = session.get("user_id")
    user = load_user(user_id)
    user.last_seen=datetime.utcnow()
    db.session.commit()
    js = json.dumps(user.as_json(), default=str) # returns empty data !
    js = json.dumps(user, cls=AlchemyEncoder)
    resp = Response(js, status=200,  mimetype='application/json')
    return resp



@auth.route('/firstsuper')
@login_required
def firstsuper():
    """
    Handle requests to the /firstsuper route
    """
    return render_template('admin/firstsuper.html')
    # redirect to the login page
    # return redirect(url_for('auth.choose_provider'))

@auth.route('/checkfirstsuper', methods=['POST'])
# @login_required
def checkfirstsuper():
    """
    Handle requests to the /firstsuper route
    """
    mdp = request.form.get('password')
    if mdp == Config.FIRSTADMINKEY:
        user_id = session.get("user_id")
        user = load_user(user_id)
        user.super_admin = True
        db.session.commit()
        #print("88888888",user,user.super_admin)
        message="You are logged in as the first super user"
    else:
        message = "Access as superadmin has been denied."
    flash(message)
	
    # redirect to the login page
    return redirect(url_for('home.home_page'))


# @auth.route('/logout')
# @login_required
# def logout():
#     """
#     Handle requests to the /logout route
#     Log an employee out through the logout link
#     """
#     logout_user()
#     flash('You have successfully been logged out.') 

#     # redirect to the login page
#     #return redirect(url_for('auth.choose_provider'))
#     return redirect(url_for('home.home_page'))

@auth.route('/logout')
def logout():
    """
    Handle requests to the /logout route
    Log an employee out through the logout link
    """
    logout_user()
    js = json.dumps({'logout':True}, default=str)
    resp = Response(js, status=200,  mimetype='application/json')
    return resp

@auth.route('/test')
# @login_required
def xxxt():
    """
    Handle requests to the /logout route
    Log an employee out through the logout link
    """
    # logout_user()
    # flash('You have successfully been logged out.') 

    # # redirect to the login page
    #return redirect(url_for('auth.choose_provider'))
    # return redirect(url_for('home.home_page'))
    js = json.dumps({"stat":"ok"})
    return redirect("https://google.com", Response=js)
