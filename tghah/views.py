from django.shortcuts import render
from django.conf import settings
from telegram import ReplyKeyboardMarkup,ForceReply,Update,Bot,InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater,Dispatcher, CommandHandler, MessageHandler, Filters,CallbackQueryHandler)
from .models import TgUser,TgAnontiationship
from django.http import HttpResponse
from django.db.models import Q
from django.core.cache import cache
import json,re,hashlib

import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CONVO_TEXTS=["Paste or write the name of the user i.e @johnsnow","Write anonymous message to be sent:"]

# Used to change text above inline keyboard--should not be same when updating the existing keyboard
SWAP_1=0
SWAP_2=1



def _start(bot,update):
	start_message="Welcome to Sociahah.\nSubscription successfull.\nYou will be able to receive and send anonymous remarks.\n\nUse the /help command for help or start typing '/' to view the available commands!"
	# create as a new user
	
	chat_id=update.message.chat_id
	username=update.message.chat.username

	if username!='':
		user,created=TgUser.objects.get_or_create(tg_id=int(chat_id),username='@'+username)
		if user:
			user.active=True
			user.save()
			bot.sendMessage(chat_id=chat_id, text=start_message.encode('utf-8'))
		else:
			bot.sendMessage(chat_id=chat_id, text="Could not register you! Failed!".encode('utf-8'))
	else:
		print("Username is empty")
		bot.sendMessage(chat_id=chat_id, text="Please update your telegram username(in your profile) first required for subscription!".encode('utf-8'))

def _help(bot,update):
	chat_id=update.message.chat_id
	help_message=u"Need Help? Use the below commands:\n\n /dm (to send anonymous text)\n\n /block (to view or block anons)\n\n /stop (to deactivate your subscription!)\n\n /start (to start or reactivate subscription!))"
	update.message.reply_text(help_message.encode('utf-8'))

def _stop(bot,update):
	chat_id=update.message.chat_id
	stop_message="Bot stopped successfully.\nYou will NOT be able to send or receive anonymous remarks from friends!"
	try:
		user=TgUser.objects.get(tg_id=chat_id)
		
	except Exception as e:
		bot.sendMessage(chat_id=chat_id, text="Could not Stop subscription.Subscription may ALREADY be inactive!".encode('utf-8'))
	else:
		user.active=False
		user.save()
		bot.sendMessage(chat_id=chat_id, text=stop_message.encode('utf-8'))

def _dm(bot,update):
	text = update.message.text
	chat_id = update.message.chat_id
	user_id = update.message.from_user.id

	cache.set(chat_id,{"convo":True,"current":0,"next":1,"data":{}})
	print "INITIAL:",type(cache.get(chat_id)), cache.get(chat_id)

	update.message.reply_text(CONVO_TEXTS[0])


def _get_username(bot, update):
	#send message
	chat_id = update.message.chat_id

	senderObj=TgUser.objects.get(tg_id=chat_id)
	
	recepient = update.message.text
	if cache.get(chat_id):
		if recepient.startswith('@'):
			# check if username in database
			try:
				print "Trying to get recepient"
				recepientObj=TgUser.objects.get(username=recepient)
				
			except Exception as e:
				print "Exception",e
				# user not registered with bot || cannot send message
				update.message.reply_text("Sorry! User %s is not registered with the bot"%recepient)
				cache.delete(chat_id)	
			else:
				if senderObj.active:
					cached=cache.get(chat_id)
					cached["data"]["username"]=recepient
					cached["current"]=1
					cached["next"]=2
					cache.set(chat_id,cached)
					update.message.reply_text(CONVO_TEXTS[1])
				else:
					update.message.reply_text("Sorry! %s is not a valid username"%recepient)
		else:
			update.message.reply_text("Sorry! %s is not a valid username"%recepient)
			cache.delete(chat_id)	
	else:
		# wrong name passed
		update.message.reply_text("Sorry! Please start afresh using /dm command")
		cache.delete(chat_id)
		

def _get_message(bot, update):
	message = update.message.text
	chat_id=update.message.chat_id
	cached=cache.get(chat_id)
	name=cached['data']['username']
	recepientObj=None

	# send message to recepient
	try:
		# create relationship
		senderObj=TgUser.objects.get(tg_id=chat_id)
		recepientObj=TgUser.objects.get(username=name)
	except Exception as e:
		update.message.reply_text("Sorry! could not send message to %s. Internal error!"%name)
		cache.delete(chat_id)
	else:
		anontiationship=_check_reverse_relationship(senderObj,recepientObj)

		if anontiationship:
			msg="       <b>%s</b> \n%s\n"%("anon"+str(anontiationship.id),message)
			if recepientObj and recepientObj.active:
				# send message to recepient
				# check if relationship is blocked
				if anontiationship.status:
					cache.delete(chat_id)
					bot.sendMessage(recepientObj.tg_id,parse_mode='HTML',text=msg)
					update.message.reply_text("Neat!\nMessage sent to %s!"%name)
				else:
					update.message.reply_text("Sorry! Anontiationship is blocked by either parties!")
					cache.delete(chat_id)
				# inform sender of message receipt				
			else:
				update.message.reply_text("Sorry! %s has deactivated his/her subscription"%name)
				cache.delete(chat_id)
		else :
			# tell sender message could not be sent
			update.message.reply_text("Sorry! could not send message to %s"%name)
			cache.delete(chat_id)

def _block_unblock(bot,update):
	chat_id=update.message.chat_id
	senderObj=TgUser.objects.get(tg_id=chat_id)
	markup=_create_keyboard(senderObj)
	update.message.reply_text("Press 'BLOCK' to block anon:", reply_markup=markup)


def msg_handler(bot,update):
	chat_id = update.message.chat_id
	user_id = update.message.from_user.id
	red=cache.get(chat_id)
	print "\n\n REDIS: \n %s\n\n"%(red)
	reply=update.message.reply_to_message or None
	
	if cache.get(chat_id):
		session=cache.get(chat_id)
		if session["convo"]:
			next_state=session["next"]
			call_next_state(bot,update,next_state)
		else:
			update.message.reply_text("Please use the available commands like:\n /dm --to start a conversation")
	else:
		update.message.reply_text("Please use the available commands like:\n /dm --to start a conversation")

def _button_handler(bot,update):

	query = update.callback_query
	chat_id =query.message.chat_id

	if re.match('^block[0-9]+$',query.data) != None:
		u_id=re.match('^block(?P<pk>\d+)$',query.data)
		pk=u_id.group('pk')
		anontiationship=TgAnontiationship.objects.get(id=int(pk))
		anontiationship.status=False
		anontiationship.save()

		# getting a new instance of anons
		senderObj=TgUser.objects.get(tg_id=chat_id)
		markup=_create_keyboard(senderObj)
		text="Press 'BLOCK/UNBLOCK' to block/unblock anon:"
		bot.editMessageText(chat_id=chat_id,message_id=update.callback_query.message.message_id,text=text,reply_markup=markup)
		bot.answer_callback_query(text=" Anon blocked successfully!", callback_query_id=query.id,)

	elif re.match('^unblock[0-9]+$',query.data) != None:
		u_id=re.match('^unblock(?P<pk>\d+)$',query.data)
		pk=u_id.group('pk')
		anontiationship=TgAnontiationship.objects.get(id=int(pk))
		anontiationship.status=True
		anontiationship.save()

		# getting a new instance of anons
		senderObj=TgUser.objects.get(tg_id=chat_id)
		markup=_create_keyboard(senderObj)
		text="Press 'BLOCK/UNBLOCK' to block/unblock anon:"
		bot.editMessageText(chat_id=chat_id,message_id=update.callback_query.message.message_id,text=text,reply_markup=markup)
		bot.answer_callback_query(text=" Anon unblocked successfully!", callback_query_id=query.id,)

	else:
		bot.answer_callback_query(text=" No action! ", callback_query_id=query.id,)
        
def call_next_state(bot,update,next_state):
	if next_state == 1:
		_get_username(bot,update)
	elif next_state == 2:
		_get_message(bot,update)

def _create_keyboard(user):
	blockTexts=["BLOCK","BLCK"]
	unblockTexts=["UNBLOCK","UNBLCK"]
	global SWAP_1,SWAP_2

	SWAP_1,SWAP_2=SWAP_2,SWAP_1
	user_hash=hashlib.sha1(str(user.tg_id)).hexdigest()
	# swapping for different values
	block_text=blockTexts[SWAP_1]
	unblock_text=unblockTexts[SWAP_1]
	userz=TgAnontiationship.objects.all()
	for i in userz:
		print i.user1_hash+" : ",i.user2_hash

	anontiationships=TgAnontiationship.objects.filter(Q(user1_hash__exact=user_hash) | Q(user2_hash__exact=user_hash))
	keyboard=[]
	for relationship in anontiationships:
		if relationship.status:
			keyboard.append([InlineKeyboardButton("anon"+str(relationship.id),callback_data='anon'+str(relationship.id)),\
							InlineKeyboardButton(block_text,callback_data='block'+str(relationship.id))])
		else:
			keyboard.append([InlineKeyboardButton("anon"+str(relationship.id),callback_data='anon'+str(relationship.id)),\
							InlineKeyboardButton(unblock_text,callback_data='unblock'+str(relationship.id))])

	# keyboard=[[InlineKeyboardButton("anon"+str(relationship.id),callback_data='anon'+str(relationship.id)),\
	# InlineKeyboardButton(text,callback_data='block'+str(relationship.id))] for relationship in anontiationships  'block'+str(relationship.id) if relationship.status else 'unblock'+str(relationship.id) ]
	markup=InlineKeyboardMarkup(keyboard)
	return markup



def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def _check_reverse_relationship(sender,recepient):
	# forward anontiationship
	sender_hash=hashlib.sha1(str(sender.tg_id)).hexdigest()
	recepient_hash=hashlib.sha1(str(recepient.tg_id)).hexdigest()
	try:
		anontiationship=TgAnontiationship.objects.get(user1_hash=sender_hash,user2_hash=recepient_hash)
		return anontiationship
	except Exception as e:
		pass

	# reverse anontiationship
	try:
		anontiationship=TgAnontiationship.objects.get(user1_hash=sender_hash,user2_hash=recepient_hash)
		return anontiationship
	except Exception as e:
		# relationship doesnt exist,CREATE ONE
		try:
			anontiationship=TgAnontiationship.objects.create(user1_hash=sender_hash,user2_hash=recepient_hash,status=True)
			return anontiationship
		except Exception as e:
			return None
			

class TelegramBot(object):
	"""docstring for TelegramBot"""
	_instance=None

	def __init__(self,**kwargs):
		super(TelegramBot, self).__init__()
		self.dispatcher.add_handler(CommandHandler('start',_start))
		self.dispatcher.add_handler(CommandHandler('help', _help))
		self.dispatcher.add_handler(CommandHandler('stop', _stop))
		
		self.dispatcher.add_handler(CommandHandler('dm', _dm))
		self.dispatcher.add_handler(MessageHandler([Filters.text], msg_handler))
		self.dispatcher.add_handler(CommandHandler('block',_block_unblock))
		self.dispatcher.add_handler(CallbackQueryHandler(_button_handler))
				
		# self.dispatcher.add_handler(MessageHandler([Filters.text], _custom_messagehandler))
		self.dispatcher.add_error_handler(error)

	def __new__(self):
		if not self._instance:
			self._instance=super(TelegramBot,self).__new__(self)
			self.bot = Bot(settings.TG_TOKEN)
			self.dispatcher=Dispatcher(self.bot, None, workers=0)
		return self._instance

	def webhook_request(self,update):
		dis =self.dispatcher.process_update(update)


def tg_update(request):
	if request.method == 'POST':
		bot=TelegramBot()
		update=Update.de_json(json.loads(request.body),bot.bot)
		bot.webhook_request(update)
		
		return HttpResponse('POST received\n'+str(request.POST))
	else:
		return HttpResponse("404!")

