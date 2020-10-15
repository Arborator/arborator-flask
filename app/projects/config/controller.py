from . import config

@config.route('/foo/', methods=['GET'])
def foo():
    print("KK foo")
    return {"3":['3', 4, 5]}

