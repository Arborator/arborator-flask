from flask import Flask, render_template, request, make_response, session, redirect, flash, url_for
from authomatic.adapters import WerkzeugAdapter
from authomatic import Authomatic
from flask_login import login_required, login_user, logout_user
from ...app import db
from datetime import datetime
from . import auth
from ..models import User, load_user
from .auth_config import CONFIG
from ...config import Config




authomatic = Authomatic(CONFIG, Config.SECRET_KEY, report_errors=True)

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

    # Log the user in, pass it the adapter and the provider name.
    result = authomatic.login(WerkzeugAdapter(request, response), provider_name)
    #####Sessions!! coming back
        # session=session,
        # session_saver=lambda: app.save_session(session, response))
    
    # If there is no LoginResult object, the login procedure is still pending.
    if result:
        if result.error:
            return "Error: {}".format(result.error.message)
            # Something really bad has happened.
            abort(500)
        if result.user:
            result.user.update()

            # We need to update the user to get more info.
            
            #save user id to session
            user = User.query.filter_by(id=result.user.email).first()
            print(result.user.id)
            # session['email'] = result.user.email
            if user is None:
                username = result.user.email.split('@')[0]
                #print(username)
                username = User.make_valid_nickname(username)
                username = User.make_unique_nickname(username)
                #print("======", result.user.id)
                ##Save UserDetails To Db
                user, created = User.get_or_create(db.session, 
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
                # ##Add Try/Catch and Logger Here
                # ##Check if user exists in dbS 
                #db.session.add(user)
                #db.session.commit()
            login_user(user, remember=True)
            session['logged_in']=True ### ?????
            if False:#(create list of preset super admin emails... maybe .ini file)
                print("wtf ??")
                return render_template('projects/dashboard.html')
            if not User.query.filter_by(super_admin=True).first():
            # if True:#(create list of preset super admin emails... maybe .ini file)
                print("wtf ??")
                # return redirect(url_for('auth.firstsuper'))
                return render_template('admin/firstsuper.html')
            
            # elif user.is_admin:
            #     check project(s) in charge
            #     redirect to project page
            # The rest happens inside the template.
            return render_template('home/index.html', result=result)
    return response


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
