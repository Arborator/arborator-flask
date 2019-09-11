import os


class Config(object):
    """
    Common configurations
    """


    SECRET_KEY = 'p9Bv<3Eid9%$i01jge87rt32trig87'
    basedir = os.path.dirname(os.path.abspath(__file__))


    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
            'sqlite:///' + os.path.join(basedir, 'arborator.sqlite')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # Put any configurations here that are common across all environments
    FIRSTADMINKEY="azer"
    UPLOAD_FOLDER = "grew_server/test/data/"

class DevelopmentConfig(Config):
    """
    Development configurations
    """

    DEBUG = True
    SQLALCHEMY_ECHO = False # changed it because the log was too long
   
    

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

app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
