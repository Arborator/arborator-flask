from flask import Flask, render_template, request, make_response, session, redirect, flash, url_for, Response
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic
from flask_login import login_required, login_user, logout_user
from ...app import db
from datetime import datetime
from . import auth
from ..models import User, load_user, AlchemyEncoder
from .auth_config import CONFIG
from ...config import Config
import json

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

@auth.route('/login/<provider_name>/', methods=['GET', 'POST'])
def login(provider_name):
    """
    Login handler.
    """   
    # We need response object for the WerkzeugAdapter.
    response = make_response()
    print("response@@@@", response)
    print("base url=====", request.base_url)
    # Log the user in, pass it the adapter and the provider name.

    
    result = authomatic.login(WerkzeugAdapter(request, response), provider_name)
    #####Sessions!! coming back
        # session=session,
        # session_saver=lambda: app.save_session(session, response))
    print(456546514,result, provider_name, response)
    # If there is no LoginResult object, the login procedure is still pending.
    if result:
        if result.error:
            # return result.error
            print("Error: {}".format(result.error))
            # resp = Response({}, status=200,  mimetype='application/json')
            # return render_template('home/redirect.html', response=resp)
            # return "Error: {}".format(result.error.message)
        #     # Something really bad has happened.
            abort(500)
        print('result = ', result)
        print(result.provider)
        if result.user:
            print('USER FOUND')
            result.user.update()
            # We need to update the user to get more info.
            
            #save user id to session
            user = User.query.filter_by(id=result.user.email).first()
            # session['email'] = result.user.email
            if user is None:
                username = result.user.email.split('@')[0]
                username = User.make_valid_nickname(username)
                username = User.make_unique_nickname(username)
                ##Save UserDetails To Db
                user, created = User.get_or_create(
                        db.session, 
                        id = result.user.email,
                        auth_provider = result.user.provider.id,
                        username = username,
                        #email=result.user.email,
                        first_name=result.user.first_name,
                        family_name=result.user.last_name,
                        picture_url=result.user.picture,
                        super_admin=False,
                        created_date=datetime.utcnow(),
                        last_seen=datetime.utcnow()
                    )

            User.setPictureUrl(db.session, user.username, result.user.picture) # always get the lastest picture on login

            login_user(user, remember=True)
            session['logged_in']=True ### ?????
            
            if not User.query.filter_by(super_admin=True).first():
                print("firstsuper")
                # return redirect(url_for('auth.firstsuper'))
                return render_template('admin/firstsuper.html')
           
            js = json.dumps(user.as_json(), default=str)
            resp = Response(js, status=200,  mimetype='application/json')
            # return resp
            return render_template('home/redirect.html', response=resp)
            # return render_template('home/index.html', result=result)
    return response


@auth.route('/login/userinfos', methods=['GET', 'POST'])
def getUserInfos():
    # print(session)
    print('USERINFOS')
    user_id = session.get("user_id")
    print('user_id', user_id)
    user = load_user(user_id)
    print('super_admin ?', user.super_admin)
    user.last_seen=datetime.utcnow()
    print('user', user)
    print('user json', user.as_json())
    db.session.commit()
    js = json.dumps(user.as_json(), default=str) # returns empty data !
    print('user jjson str', js)
    print(json.dumps(user, cls=AlchemyEncoder) )
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


@auth.route('/logout')
@login_required
def logout():
    """
    Handle requests to the /logout route
    Log an employee out through the logout link
    """
    logout_user()
    flash('You have successfully been logged out.') 

    # redirect to the login page
    #return redirect(url_for('auth.choose_provider'))
    return redirect(url_for('home.home_page'))

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
