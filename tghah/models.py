from __future__ import unicode_literals

from django.db import models

# Create your models here.

class TgUser(models.Model):
	tg_id=models.IntegerField(unique=True)
	username=models.CharField(max_length=200)
	active=models.BooleanField(default=True)
	created=models.DateTimeField(auto_now_add=True)

	def __unicode__(self):
		return self.username
	
class TgAnontiationship(models.Model):
	# relationship table
	user1_hash=models.CharField(max_length=253)
	user2_hash=models.CharField(max_length=253)
	status=models.BooleanField(default=True)# ?active:blocked

	class Meta:
		unique_together=(("user1_hash","user2_hash"))


# BOT DESCRIPTION
# Just like Sarahah but on Telegram!

