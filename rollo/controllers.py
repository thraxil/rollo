import logging

import cherrypy

import turbogears
from turbogears import controllers, expose, validate, redirect
from cherrypy.config import get as config
import urllib
from rollo.model import *

from os.path import dirname
import os
import webhelpers
from rollo import json

log = logging.getLogger("rollo.controllers")


def get_cookie(cookie_name):
    if cherrypy.request.simpleCookie.has_key(cookie_name):
        return cherrypy.request.simpleCookie[cookie_name].value
    else:
        return ""

def set_cookie(cookie_name,cookie_value,**kwargs):
    cherrypy.response.simpleCookie[cookie_name] = cookie_value
    for k in kwargs.keys():
        cherrypy.response.simpleCookie[cookie_name][k] = kwargs[k]

def get_hostname():
    return cherrypy.request.headerMap.get('Host','localhost')

def expire_session():
    cherrypy.session['uni'] = ""

def get_uni():
    if config('TESTMODE'):
        return "testuser"
    return cherrypy.session.get('uni','')

# can't store SQLObject stuff in a disk session,
# so we just memoize this here
users_cache = dict()
def get_user():
    uni = get_uni()
    if uni == "":
        return None
    u = users_cache.get(get_uni(),None)
    if u is None:
        u = find_or_create_user(uni)
        users_cache[uni] = u
    return u

def find_or_create_user(uni):
    try:
        return User.byUni(uni)
    except:
        return User(uni=uni)

def add_global_variables(variables):
    variables['User'] = User
    variables['user'] = get_user()
    variables['h']    = webhelpers
    return variables

turbogears.view.variable_providers.append(add_global_variables)


def is_authenticated():
    # TODO:
    # this should also make sure that they're
    # CCNMTL.
    # for now, we'll just accept any uni
    return get_user() is not None

def validate_wind_ticket(ticketid):
    """
    checks a wind ticketid.
    if successful, it returns (1,uni)
    otherwise it returns (0,error message)
    """
    
    if ticketid == "":
        return (0,'no ticketid')
    uri = "https://wind.columbia.edu/validate?ticketid=%s" % ticketid
    import urllib
    response = urllib.urlopen(uri).read()
    lines = response.split("\n")
    if lines[0] == "yes":
        uni = lines[1]
        groups = [line for line in lines[1:] if line != ""]
        return (1,uni,groups)
    elif lines[0] == "no":
        return (0,"The ticket was already used or was invalid.",[])
    else:
        return (0,"WIND did not return a valid response.",[])

def referer():
    return cherrypy.request.headerMap.get('Referer','/')

class Content:
    @cherrypy.expose()
    def default(self, *vpath, **params):
        if len(vpath) == 1:
            identifier = vpath[0]
            action = self.show
        elif len(vpath) == 2:
            identifier, verb = vpath
            verb = verb.replace('.', '_')
            action = getattr(self, verb, None)
            if not action:
                raise cherrypy.NotFound
            if not action.exposed:
                raise cherrypy.NotFound
        else:
            raise cherrypy.NotFound
        items = self.query(identifier)
        if hasattr(items,"count"):
            if items.count() == 0:
                raise cherrypy.NotFound
            else:
                return action(items[0], **params)
        else:
            return action(items,**params)

    
from cherrypy.filters import basefilter
class AuthFilter(basefilter.BaseFilter):
    def before_main(self):
        path = cherrypy.request.path
        if config('TESTMODE'):
            return
        if path.startswith("/static"):
            return
        if path.startswith("/tg_widgets"):
            return
        if path.startswith("/favicon"):
            return
        if path.startswith("/log"):
            return

        if is_authenticated():
            return
        else:
            redirect("/login?destination=%s" % urllib.quote(cherrypy.request.browser_url))



class CategoryController(controllers.Controller,Content):
    def query(self,id):
        return Category.get(id=id)


    @expose(template=".templates.category")
    def show(self,category):
        return dict(category=category)

    @expose()
    def add_application(self,category,name=""):
        a = Application(category=category,name=name)
        raise redirect(referer())

class ApplicationController(controllers.Controller,Content):
    def query(self,id):
        return Application.get(id=id)

    @expose(template=".templates.application")
    def show(self,application):
        return dict(application=application)

    @expose()
    def add_deployment(self,application,name):
        d = Deployment(application=application,name=name)
        raise redirect(referer())

class DeploymentController(controllers.Controller,Content):
    def query(self,id):
        return Deployment.get(id=id)

    @expose(template=".templates.deployment")
    def show(self,deployment):
        return dict(deployment=deployment,
                    all_categories=Category.select(orderBy="name"),
                    all_recipes=Recipe.select(NOT(Recipe.q.name==""),orderBy="name"))

    @expose()
    def add_setting(self,deployment,name,value):
        s = Setting(deployment=deployment,name=name,value=value)
        raise redirect(referer())

    @expose()
    def edit_settings(self,deployment,**kwargs):
        for k in kwargs.keys():
            if k.startswith('setting_name_'):
                setting_id = int(k[len('setting_name_'):])
                setting = Setting.get(setting_id)
                if kwargs[k] == "":
                    setting.destroySelf()
                else:
                    setting.name = kwargs[k]
                    setting.value = kwargs["setting_value_%d" % setting_id]
        raise redirect(referer())


    @expose()
    def add_stage(self,deployment,name,recipe_id,language,code):
        recipe = None
        code = code.replace('\r\n','\n')
        if recipe_id == "":
            recipe = Recipe(name="",description="",language=language,code=code)
        else:
            recipe = Recipe.get(int(recipe_id))
        existing_stages = len(deployment.stages)
        stage = Stage(deployment=deployment,recipe=recipe,
                      name=name,cardinality=existing_stages+1)
        raise redirect(referer())

    @expose()
    def push(self,deployment,comment="",step=None):
        push = deployment.new_push(user=get_user(),comment=comment)
        if step:
            raise redirect("/push/%d/?step=1" % push.id)
        else:
            raise redirect("/push/%d/" % push.id)

    @expose()
    def rollback(self,deployment,comment="",step=None,push_id=""):
        push = deployment.new_push(user=get_user(),comment=comment)
        if step:
            raise redirect("/push/%d/?step=1;rollback=%s" % (push.id,push_id))
        else:
            raise redirect("/push/%d/?rollback=%s" % (push.id,push_id))


    @expose()
    def clone(self,deployment,name,application_id):
        application = Application.get(int(application_id))
        new_deployment = Deployment(name=name,application=application)
        # clone settings
        for setting in deployment.settings:
            s = Setting(deployment=new_deployment,name=setting.name,
                        value=setting.value)
        # clone stages
        for stage in deployment.stages:
            recipe = stage.recipe
            r = recipe
            if recipe.name == "":
                # not a cookbook recipe, so we clone it
                r = Recipe(name="",language=recipe.language,code=recipe.code)
            s = Stage(deployment=new_deployment,name=stage.name,recipe=r,
                      cardinality=stage.cardinality)

        raise redirect("/deployment/%d/" % new_deployment.id)

    @expose()
    def delete(self,deployment):
        application_id = deployment.application.id
        deployment.destroySelf()
        raise redirect("/application/%d/" % application_id)

    
class StageController(controllers.Controller,Content):
    def query(self,id):
        return Stage.get(id=id)

    @expose(template=".templates.stage")
    def show(self,stage):
        return dict(stage=stage,
                    all_recipes=Recipe.select(NOT(Recipe.q.name==""),orderBy="name"))

    @expose()
    def edit(self,stage,name,cardinality,recipe_id="",code="",language="python"):
        stage.name = name
        stage.cardinality = int(cardinality)
        code = code.replace('\r\n','\n')
        if recipe_id != "":
            r = Recipe.get(recipe_id)
            stage.recipe = r
        else:
            if stage.recipe.name != "":
                stage.recipe = Recipe(language=language,code="")
            else:
                stage.recipe.language = language
                stage.recipe.code = code
        raise redirect(referer())
            
        
        

    @expose()
    def delete(self,stage):
        deployment_id = stage.deployment.id
        stage.destroySelf()
        raise redirect("/deployment/%d/" % deployment_id)


class CookbookController(controllers.Controller,Content):
    def query(self,id):
        return Recipe.get(id=id)

    @expose(template=".templates.recipes")
    def index(self):
        return dict(all_recipes=Recipe.select(NOT(Recipe.q.name==""),orderBy="name"))

    @expose()
    def add_recipe(self,name,description,language,code):
        code = code.replace('\r\n','\n')        
        r = Recipe(name=name,description=description,language=language,code=code)
        raise redirect(referer())

    @expose(template=".templates.recipe")
    def show(self,recipe):
        return dict(recipe=recipe)

    @expose()
    def edit(self,recipe,name,description,language,code):
        recipe.name = name
        recipe.description = description
        recipe.language = language
        code = code.replace('\r\n','\n')
        recipe.code = code
        raise redirect(referer())

class PushController(controllers.Controller,Content):
    def query(self,id):
        return Push.get(id=id)

    @expose(template=".templates.push")
    def show(self,push,step=None,rollback=""):
        return dict(push=push,step=step,rollback=rollback)

    @expose(allow_json=True,format="json")
    def status(self,push):
        return dict(push=push)

    @expose()
    def delete(self,push):
        deployment_id = push.deployment.id
        push.destroySelf()
        raise redirect("/deployment/%d/" % deployment_id)


    @expose(allow_json=True,format="json")
    def stage(self,push,stage_id,rollback_id=""):
        """ run the stage """
        pushstage = push.run_stage(stage_id,rollback_id)
        return dict(status=pushstage.status,
                    logs=pushstage.logs,
                    end_time=pushstage.end_time,
                    stage_id=pushstage.stage.id)

class Root(controllers.RootController):
    _cpFilterList = [AuthFilter()]

    category = CategoryController()
    application = ApplicationController()
    deployment = DeploymentController()
    stage = StageController()
    cookbook = CookbookController()
    push = PushController()
    
    @expose(template=".templates.index")
    def index(self):
        return dict(recent_pushes=get_user().recent_pushes(),categories=Category.select(orderBy="name"))

    @expose()
    def add_category(self,name=""):
        c = Category(name=name)
        raise redirect(referer())

    @expose(template=".templates.login")
    def login(self,destination="",ticketid=""):
        if destination == "":
            destination = "/"
            
        if ticketid:
            # verify a wind ticket and log them in
            (success,uni,groups) = validate_wind_ticket(ticketid)
            if int(success) == 0:
                return "WIND authentication failed. Please Try Again."
            u = find_or_create_user(uni)
            if 'tlc.cunix.local:columbia.edu' in groups or \
               'staff.cunix.local:columbia.edu' in groups or \
               'tlcxml.cunix.local:columbia.edu' in groups:
                # it's good
                cherrypy.session['uni'] = uni
                set_cookie("candyman_auth",uni, path="/", expires=10 * 365 * 24 * 3600)
                raise redirect(destination)
            else:
                # they're not ccnmtl. kick them out
                return "This application is restricted to CCNMTL staff. See an admin if you need to get in."
        else:
            location = cherrypy.request.browser_url
            location = "/".join(location.rsplit("/")[:3]) + "/login"
            winddest = "%s?destination=%s" % (location,urllib.quote(destination))
            dest = "https://wind.columbia.edu/login?destination=%s&service=cnmtl_full_np" % winddest
            raise redirect(dest)


    @expose()
    def logout(self):
        expire_session()
        set_cookie("candyman_auth","",path="/",expires=0)
        raise redirect("/")
