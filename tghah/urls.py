
from .views import *
from django.conf.urls import url, include
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

urlpatterns = [

	url(r'^'+settings.TG_TOKEN+'/webhook$', csrf_exempt(tg_update)),
]