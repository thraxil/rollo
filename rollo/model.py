from sqlobject import *
from turbogears.database import PackageHub
import os, time
from datetime import datetime,timedelta
import subprocess
import sys
import StringIO
import cgitb
import ConfigParser
import types

hub = PackageHub("rollo")
__connection__ = hub

soClasses=["User","Category","Application","Deployment","Setting","Recipe",
           "Stage","Push","PushStage","Log"]

class User(SQLObject):
    class sqlmeta:
        table = "users"
    uni = UnicodeCol(alternateID=True)
    pushes = MultipleJoin('Push',joinColumn='user_id',orderBy="-start_time")

class Category(SQLObject):
    name = UnicodeCol(alternateID=True)
    applications = MultipleJoin('Application',orderBy="name")

class Application(SQLObject):
    name = UnicodeCol(alternateID=True)
    category = ForeignKey('Category',cascade=True)
    deployments = MultipleJoin('Deployment',orderBy="name")

class Deployment(SQLObject):
    name = UnicodeCol(default="prod")
    application = ForeignKey('Application',cascade=True)
    settings = MultipleJoin('Setting',orderBy="name")
    stages = MultipleJoin("Stage",orderBy="cardinality")
    pushes = MultipleJoin("Push",orderBy="-start_time")
    
class Setting(SQLObject):
    deployment = ForeignKey('Deployment',cascade=True)
    name = UnicodeCol()
    value = UnicodeCol()

class Recipe(SQLObject):
    name = UnicodeCol(default="")
    code = UnicodeCol(default="")
    description = UnicodeCol(default="")
    stages = MultipleJoin('Stage',orderBy="cardinality")

class Stage(SQLObject):
    name        = UnicodeCol(default="")
    deployment  = ForeignKey('Deployment',cascade=True)
    recipe      = ForeignKey('Recipe',cascade=True)
    cardinality = IntCol(default=0)
    pushstages = MultipleJoin('PushStage',orderBy="-start_time")
    
class Push(SQLObject):
    user       = ForeignKey('User',cascade=True)
    deployment = ForeignKey('Deployment',cascade=True)
    comment = UnicodeCol(default="")
    start_time = DateTimeCol(default=datetime.now)
    end_time = DateTimeCol(default=datetime.now)
    status = UnicodeCol(default="inprogress")
    rollback_url = UnicodeCol(default="")
    pushstages = MultipleJoin('PushStage',orderBy="-start_time")


class PushStage(SQLObject):
    push = ForeignKey('Push',cascade=True)
    stage = ForeignKey('Stage',cascade=True)
    start_time = DateTimeCol(default=datetime.now)
    end_time = DateTimeCol(default=datetime.now)
    status = UnicodeCol(default="inprogress")
    logs = MultipleJoin('Log',orderBy="-timestamp")

class Log(SQLObject):
    pushstage = ForeignKey('PushStage',cascade=True)
    command = UnicodeCol(default="")
    stdout  = UnicodeCol(default="")
    stderr  = UnicodeCol(deafult="")
    timestamp = DateTimeCol(default=datetime.now)
    


