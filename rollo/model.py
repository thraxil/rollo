from sqlobject import *
from turbogears.database import PackageHub
import os, time
from datetime import datetime,timedelta
import sys
import StringIO
import cgitb
import ConfigParser
import types
import threading
import stat
from subprocess import Popen,PIPE
from cherrypy.config import get as config
import os.path

from SilverCity import Python,Perl

hub = PackageHub("rollo")
__connection__ = hub

soClasses=["User","Category","Application","Deployment","Setting","Recipe",
           "Stage","Push","PushStage","Log"]

class User(SQLObject):
    class sqlmeta:
        table = "users"
    uni = UnicodeCol(alternateID=True)
    pushes = MultipleJoin('Push',joinColumn='user_id',orderBy="-id")

    def recent_pushes(self):
        return self.pushes[:10]


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
    pushes = MultipleJoin("Push",orderBy="-id")

    def new_push(self,user,comment):
        """ just make the Push object. don't exec it yet though """
        return Push(user=user,deployment=self,comment=comment)

    def env(self):
        d = dict(DEPLOYMENT_ID=str(self.id))
        for s in self.settings:
            d[s.name] = s.value
        return d

    def status(self):
        if len(self.pushes) > 0:
            return self.pushes[0].status
        else:
            return "unknown"


    
class Setting(SQLObject):
    deployment = ForeignKey('Deployment',cascade=True)
    name = UnicodeCol()
    value = UnicodeCol()

class Recipe(SQLObject):
    name = UnicodeCol(default="")
    code = UnicodeCol(default="")
    language = UnicodeCol(default="python")
    description = UnicodeCol(default="")
    stages = MultipleJoin('Stage',orderBy="cardinality")

    def code_html(self):
        if self.language == "python":
            g = Python.PythonHTMLGenerator()
            file = StringIO.StringIO()
            g.generate_html(file,self.code)
            return file.getvalue()
        if self.language == "shell":
            first_line = self.code.split('\n')[0]
            if 'python' in first_line:
                g = Python.PythonHTMLGenerator()
                file = StringIO.StringIO()
                g.generate_html(file,self.code)
                return file.getvalue()
            elif 'perl' in first_line:
                g = Perl.PerlHTMLGenerator()
                file = StringIO.StringIO()
                g.generate_html(file,self.code)
                return file.getvalue()
            else:
                g = Perl.PerlHTMLGenerator()
                file = StringIO.StringIO()
                g.generate_html(file,self.code)
                return file.getvalue()


class Stage(SQLObject):
    name        = UnicodeCol(default="")
    deployment  = ForeignKey('Deployment',cascade=True)
    recipe      = ForeignKey('Recipe',cascade=True)
    cardinality = IntCol(default=0)
    pushstages = MultipleJoin('PushStage',orderBy="-id")
    
class Push(SQLObject):
    user       = ForeignKey('User',cascade=True)
    deployment = ForeignKey('Deployment',cascade=True)
    comment = UnicodeCol(default="")
    start_time = DateTimeCol(default=datetime.now)
    end_time = DateTimeCol(default=datetime.now)
    status = UnicodeCol(default="inprogress")
    rollback_url = UnicodeCol(default="")
    pushstages = MultipleJoin('PushStage',orderBy="-id")

    def run_stage(self,stage_id,rollback_id=""):
        rollback = None
        if rollback_id != "":
            rollback = Push.get(int(rollback_id))
        stage = Stage.get(int(stage_id))
        pushstage = PushStage(push=self,stage=stage)
        pushstage.run(rollback)
        if pushstage.status == "failed" or pushstage.stage.id == self.deployment.stages[-1].id:
            # last stage, so set the push status
            self.status = pushstage.status
            self.end_time = datetime.now()
        return pushstage

    def checkout_dir(self):
        return os.path.join(config("checkout_dir","/tmp/rollo/checkouts/"),
                            str(self.deployment.id),"local")

    def env(self):
        d = self.deployment.env()
        d['CWD'] = self.checkout_dir()
        d['CHECKOUT_DIR'] = self.checkout_dir()
        d['PUSH_COMMENT'] = self.comment
        d['PUSH_UNI'] = self.user.uni
        d['ROLLBACK_URL'] = self.rollback_url
        return d

class PushStage(SQLObject):
    push = ForeignKey('Push',cascade=True)
    stage = ForeignKey('Stage',cascade=True)
    start_time = DateTimeCol(default=datetime.now)
    end_time = DateTimeCol(default=datetime.now)
    status = UnicodeCol(default="inprogress")
    logs = MultipleJoin('Log',orderBy="-timestamp",joinColumn="pushstage_id")

    def setting(self,name):
        env = self.push.env()
        if hasattr(self,'rollback') and self.rollback is not None:
            env['ROLLBACK_URL'] = self.rollback.rollback_url
        return env.get(name,'')

    def run(self,rollback=None):
        """ run the stage's code """
        self.rollback = rollback
        recipe = self.stage.recipe
        if recipe.language == "python":
            self.status = "ok"
            try:
                exec recipe.code in locals(),globals()
            except Exception, e:
                l = Log(pushstage=self,command=recipe.code,
                        stdout="",stderr=str(e))
                self.status = "failed"
        else:
            # write to temp file, exec, then clean up
            script_filename = os.path.join(config("script_dir","/tmp/rollo/scripts"),"%d.sh" % self.id)
            code = recipe.code
            if not code.startswith("#!"):
                # make sure it has a shebang line
                code = "#!/bin/bash\n" + code
            open(script_filename,"w").write(code)
            os.chmod(script_filename,stat.S_IRWXU|stat.S_IRWXG|stat.S_IROTH)
            try:
                os.makedirs(self.push.checkout_dir())
            except:
                pass
            #TODO: setup timeout
            env = self.push.env()
            if rollback is not None:
                env['ROLLBACK_URL'] = rollback.rollback_url
            p = Popen(script_filename,bufsize=1,stdout=PIPE,stderr=PIPE,
                      cwd=self.push.checkout_dir(),env=env,close_fds=True)
            ret = p.wait()
            stdout = p.stdout.read()
            stderr = p.stderr.read()
            l = Log(pushstage=self,command=recipe.code,
                    stdout=stdout,stderr=stderr)
            if ret == 0:
                self.status = "ok"
            else:
                self.status = "failed"
        self.end_time = datetime.now()

    def execute(self,args):
        """ useful function available to recipes """
        p = Popen(args,stdout=PIPE,stderr=PIPE,cwd=self.push.checkout_dir(),close_fds=True)
        ret = p.wait()
        stdout = p.stdout.read()
        stderr = p.stderr.read()
        l = Log(pushstage=self,command=" ".join(args),stdout=stdout,stderr=stderr)
        return (ret,stdout,stderr)

    def stdout(self):
        if len(self.logs) > 0:
            return self.logs[0].stdout
        else:
            return ""

    def stderr(self):
        if len(self.logs) > 0:
            return self.logs[0].stderr
        else:
            return ""

class Log(SQLObject):
    pushstage = ForeignKey('PushStage',cascade=True)
    command = UnicodeCol(default="")
    stdout  = UnicodeCol(default="")
    stderr  = UnicodeCol(default="")
    timestamp = DateTimeCol(default=datetime.now)
    


