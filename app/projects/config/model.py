import sys
sys.path.append(".....")
import base64
from sqlalchemy import Column, Integer, String, BLOB, Boolean
# try:
from app import db # dev
# except:
#     from app import db  # prod


class BaseM(object):

    def as_json(self, exclude=[], include={}):
        json_rep = dict()
        for k in vars(self):
            # print(getattr(self, k))
            if k in exclude:
                # print(k)
                continue
            elif k[0] == "_":
                continue
            elif type(getattr(self, k)) is bytes:
                # print('yay')
                # print(getattr(self, k))
                json_rep[k] = str(base64.b64encode(getattr(self, k)))
                # json_rep[k] = str(getattr(self, k))
            else:
                json_rep[k] = getattr(self, k)
        for k in include:
            json_rep[k] = include[k]
        return json_rep


# TODO: ManytoMany reltnshp btwn user/proj
class Project(db.Model, BaseM): 
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String(256), nullable=False, unique=True)
    description = Column(String(256))
    image = Column(BLOB)
    visibility = Column(Integer)
    show_all_trees = Column(Boolean, default=True)
    exercise_mode = Column(Boolean, default=False)
    default_user_trees = db.relationship('DefaultUserTrees')