import logging

import cherrypy

import turbogears
from turbogears import controllers, expose, validate, redirect

from os.path import dirname
import os
from rollo import json

log = logging.getLogger("rollo.controllers")

class Root(controllers.RootController):
    @expose(template="rollo.templates.main")
    def default(self,dir="",slug="index"):
        if dir == "":
            include_document = "%s/static/content/%s.html" % (dirname(__file__),slug)
        else:
            include_document = "%s/static/content/%s/%s.html" % (dirname(__file__),dir,slug)
        try:
            os.stat(include_document)
        except OSError:
            raise cherrypy.NotFound

        data = dict(slug=slug,dir=dir,include_document=include_document)
        # templates
        if dir != "":
            data['tg_template'] = "rollo.templates.%s" % dir
        
        return data
