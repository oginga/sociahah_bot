from django.contrib import admin
from.models import *


class TgUserAdmin(admin.ModelAdmin):
	
	model=TgUser
	list_display=['username','active']
class TgAnontiationshipAdmin(admin.ModelAdmin):
	
	model=TgAnontiationship
	list_display=['id','user1_hash','user2_hash']


admin.site.register(TgUser,TgUserAdmin)
admin.site.register(TgAnontiationship,TgAnontiationshipAdmin)


# Register your models here.
