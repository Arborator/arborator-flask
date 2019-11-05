# Some utility functions for grew process
from werkzeug import secure_filename

def upload_project(fileobject, reextensions=None):
    """ 
    upload project into grew and filesystem (upload-folder, see Config). need a file object from request
    Will compile reextensions if no one is specified (better specify it before a loop)
    """

    if reextensions == None : reextensions = re.compile(r'\.(conll(u|\d+)?|txt|tsv|csv)$')

    filename = secure_filename(fileobject.filename)
    sample_name = reextensions.sub("", filename)

    # writing file to upload folder
    fileobject.save(os.path.join(Config.UPLOAD_FOLDER, filename))

    if sample_name not in samples:
        # create a new sample in the grew project
        print ('========== [newSample]')
        reply = grew_request ('newSample', data={'project_id': project_name, 'sample_id': sample_name })
        print (reply)

    else:
        print("/!\ sample already exists")

    with open(os.path.join(Config.UPLOAD_FOLDER, filename), 'rb') as inf:
        print ('========== [saveConll]')
        if import_user:
            reply = grew_request (
                'saveConll',
                data = {'project_id': project_name, 'sample_id': sample_name, "user_id": import_user},
                files={'conll_file': inf},
            )
        else: # if no import_user has been provided, it should be in the conll metadata
            reply = grew_request (
                'saveConll',
                data = {'project_id': project_name, 'sample_id': sample_name},
                files={'conll_file': inf},
            )
        print(reply)