import os
from cryptography.hazmat.backends import default_backend


class Config(object):
    """
    Common configurations
    """

    # MODE_DEPLOY = 'production' # 'production' or 'development'

    SECRET_KEY = 'p9Bv<3Eid9%$i01jge87rt32trig87'
    basedir = os.path.dirname(os.path.abspath(__file__))

    # if MODE_DEPLOY == 'production': dbName = 'prod'
    # else: dbName = 'dev'
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #         'sqlite:///' + os.path.join(basedir, 'arborator_{}.sqlite'.format(dbName))
    
    # SQLALCHEMY_TRACK_MODIFICATIONS = True

    # Put any configurations here that are common across all environments
    FIRSTADMINKEY="azer"
    # UPLOAD_FOLDER = "grew_server/test/data/"
    UPLOAD_FOLDER = "app/test/data/"

    # if both are uncommented then vue can access the session cookie
    SESSION_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SECURE = True

    # Github app
    # if ENV == 'development':
       
    # elif ENV == 'production':
        
    
    
    



class DevelopmentConfig(Config):
    """
    Development configurations
    """

    DEBUG = True
    SQLALCHEMY_ECHO = False # changed it because the log was too long
    basedir = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(basedir, 'arborator_dev.sqlite')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    ENV = 'development'
    fname = 'keys/arborator-grew-dev.pem'
    APP_ID = open('keys/arborator-grew-dev-appid.txt').read()
    # INSTALATION_ID = int(open('keys/arborator-grew-dev-installationid.txt').read())
    cert_bytes = open(fname, 'rb').read()
    PKEY = default_backend().load_pem_private_key(cert_bytes, None)
   
    

class TestingConfig(Config):
    """
    Testing configurations
    """

    TESTING = True

class ProductionConfig(Config):
    """
    Production configurations
    """

    DEBUG = False
    basedir = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(basedir, 'arborator_prod.sqlite')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    ENV = 'production'
    fname = 'keys/arborator-grew.pem'
    APP_ID = open('keys/arborator-grew-appid.txt').read()
    # INSTALATION_ID = int(open('keys/arborator-grew-installationid.txt').read())
    cert_bytes = open(fname, 'rb').read()
    PKEY = default_backend().load_pem_private_key(cert_bytes, None)

app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
