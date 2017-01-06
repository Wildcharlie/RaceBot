#!/usr/bin/python
# -*- coding: utf-8 -*-

import string
import requests
import json
import time
import re
import random
from threading import Thread

class raceChannel:
	CHANNEL = '#speedrunslive'
	
class API:
	URL = 'localhost:82'
	KEY = ''
	
class botName:
	NAME = 'RaceBot'
	
def getdata( id ):
	# This returns a specific races data
	# It's used a lot
	r = requests.get( 'http://%s/races/%s/?lower=true' % ( API.URL, id ) )
	return r.json
	
def getraces():
	# This is to get all races
	# Only used for .races for now
	r = requests.get( 'http://%s/races' % ( API.URL ) )
	return r.json
		

# Sorts players by placing	
def sort_players( playerlist ):
	entrants_x = []
	for x in playerlist[ 'entrants' ]:
		entrants_x.append( [ playerlist[ 'entrants' ][ x ][ 'place' ], playerlist[ 'entrants' ][ x ][ 'displayname' ], playerlist[ 'entrants' ][ x ][ 'time' ], playerlist[ 'entrants' ][ x ][ 'message' ] ] )
	sorted_players = sorted( entrants_x, compare_players )
	return sorted_players
	
def compare_players( player1, player2 ):
	return cmp( int( player1[ 0 ] ), int( player2[ 0 ] ) )
	
def readycheck( entrants, name ):
	# This returns the remaining people who are not ready in the race
	# Starts at -1 because it doesn't know the person who just readied
	z = -1
	for x in entrants[ 'entrants' ]:
		if x == name: pass
		elif entrants[ 'entrants' ][ x ][ 'place' ] == playerStatus.ENTRY: z += 1
	return z
	
def status( state ):
	if state == 1: return 'Entry Open'
	elif state == 2 or state == 3: return 'In Progress'
	elif state == 5: return 'Race Over'
	else: return 'Complete'
	
def goalcheck( goal ):
	if goal.lower().strip() == 'dont record' or goal.lower().strip() == 'don\'t record':
		return None
	else: return True
	
def fixplace( place ):
	if place == 1: return '1st'
	elif place == 2: return '2nd'
	elif place == 3: return '3rd'
	elif place == 11: return '11th'
	elif place == 12: return '12th'
	elif place == 13: return '13th'
	elif place%10 == 1: return '%sst' % place
	elif place%10 == 2: return '%snd' % place
	elif place%10 == 3: return '%srd' % place
	else: return '%sth' % place
	
# These classes are so I don't have to use
# numbers that I'm not going to remember
class playerStatus:
	ENTRY = 9995
	READY = 9994
	QUIT = 9998
	DQ = 9999

class raceStatus:
	ENTRY = 1
	CD = 2
	BUSY = 3
	COMPLETE = 4
	RECORDED = 5
		
class countdown:
	# Countdown gets its own class.
	# I want to change this in the future
	# because I'm reusing the send fuction and some variables
	def __init__( self, irc, chan, id, goal, game, filename ):
		self.irc = irc
		self.filename = filename
		self.chan = chan
		self.id = id
		self.goal = goal
		self.game = game
		self.cd = Thread( target=self.count )
		self.cd.daemon = True
		self.cd.start()
		
	def send( self, msg ):
		self.irc.send( '%s\r\n' % msg.encode('utf-8') )
		
	def count( self ):
		time.sleep( 2 )
		self.send ( 'PRIVMSG %s :4The race will begin in 10 seconds!' % self.chan )
		time.sleep( 5 )
		for x in range( 0, 5 ):
			self.send ( 'PRIVMSG %s :4%s' % ( self.chan, 5-x ) )
			time.sleep( 1 )
		self.send ( 'PRIVMSG %s :4GO!' % self.chan )
		if self.filename: self.send ( 'PRIVMSG %s :4Filename: %s\r\n' % ( self.chan, self.filename ) )
		self.send( 'TOPIC #srl-%s :Status: IN PROGRESS | Game: %s | Goal: %s' % ( self.id, self.game, self.goal ) )
		params = json.dumps({ 'state': raceStatus.BUSY })
		h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
		requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
	
class entrantlist:
	# This class is specifically for .entrants
	# It parses the data and gives back strings etc
	# So it can spit it back out
	def __init__( self, data ):
		self.output = data
		self.name  = self.output[ 1 ]
		self.place = self.placing()
		self.time = self.gettime()
		self.message = self.getmessage()
				
	def placing( self ):
		if self.output[ 0 ] == playerStatus.ENTRY or self.output[ 0 ] == playerStatus.READY: return ''
		elif self.output[ 0 ] == playerStatus.QUIT or self.output[ 0 ] == playerStatus.DQ: return '- '
		else: return '%s. ' % str( self.output[ 0 ] )
		
	def gettime( self ):
		if self.output[ 2 ] == 0: return ''
		elif self.output[ 0 ] == playerStatus.QUIT: return ' (Forfeit)'
		elif self.output[ 0 ] == playerStatus.DQ: return ' (DQ)'
		elif self.output[ 0 ] == playerStatus.READY: return ' (Ready)'
		else: return ' (%s)' % self.convert( self.output[ 2 ] )
		
	def getmessage( self ):
		if self.output[ 3 ] == None or self.output[ 3 ] == '': return ''
		else: return ' (%s)' % str( self.output[ 3 ].encode('utf-8') )
		
	def convert( self, seconds ):
		hours = seconds // ( 60*60 )
		seconds %= ( 60*60 )
		minutes = seconds // 60
		seconds %= 60
		return "%02i:%02i:%02i" % ( hours, minutes, seconds )
	
class Process:
	def __init__( self, irc ):
		self.irc = irc
		self.oplist = {}
		self.kicklist = {}
		self.stopstart = False
		
	def process( self, line ):
		# Process any commands given to see what needs to be done
		# Once the command is found then goes to a different function
		# to perform the action
		first = line.message.split( ' ' )[ 0 ].strip()
		
		if first == '.setstream': self.setstream( line )
		#elif first == '.removestream' and self.isop( line.nick ): self.removestream( line )
		elif first == '.stream': self.stream( line )
		elif first == '.creategame' and self.isop( line.nick ): self.creategame( line )
		elif first == '.command' and self.isop( line.nick ): 
			print ' '.join( line.message.split( ' ' ) [ 1: ] )
			print 'hello'
			self.send( '%s' % ( ' '.join( line.message.split( ' ' ) [ 1: ] ) )  )
		
		if line.channel == raceChannel.CHANNEL or line.channel == raceChannel.CHANNEL+'-j':
			if first == '.startrace' and self.stopstart == False: self.startrace( line )
			elif first == '.races': self.races( line )
			elif first == '.queue' and self.isop( line.nick ): self.queue( line )
			
		elif line.channel[ :5 ] == '#srl-':
			id = line.channel[ 5: ]
			if first == '.end' and self.isop( line.nick ): 
				raceid = Race( self.irc, line ).end()
				if raceid: self.kicklist[ raceid ] = Part( self.irc, raceid )
			elif first == '.enter' or first == '.join': Race( self.irc, line ).enter()
			elif first == '.ready': Race( self.irc, line ).ready()
			elif first == '.unready': Race( self.irc, line ).unready()
			elif first == '.time': Race( self.irc, line ).time()
			elif first == '.setgoal': Race( self.irc, line ).setgoal()
			elif first == '.goal': Race( self.irc, line ).goal()
			elif first == '.setgame': Race( self.irc, line ).setgame()
			elif first == '.unenter': Race( self.irc, line ).unenter()
			elif first == '.undone': Race( self.irc, line ).undone()
			elif first == '.remove' and self.isop( line.nick ): Race( self.irc, line ).remove()
			elif first == '.done': Race( self.irc, line ).finish( 1 )
			elif first == '.quit' or first == '.forfeit': Race( self.irc, line ).finish( 2 )
			elif first == '.entrants' or first == '.results': Race( self.irc, line ).print_entrants()
			elif first == '.dq' and self.isop( line.nick ): Race( self.irc, line ).dq()
			elif first == '.comment': Race( self.irc, line ).comment()
			elif first == '.rematch': Race( self.irc, line ).rematch()
			elif first == '.record' and self.isop( line.nick ): 
				raceid = Race( self.irc, line ).record()
				if raceid: self.kicklist[ raceid ] = Part( self.irc, raceid )
			elif first == '.filename': Race( self.irc, line ).filename()
			elif first == '.undo' and self.isop( line.nick ): Race( self.irc, line ).undo()
			
	def send( self, msg ):
		self.irc.send( '%s\r\n' % msg.encode('utf-8') )
		
	def isop( self, name ):
		if self.oplist.has_key( name ): return True
		else: return None
		
	def names( self, line ):
		chan = line.message.split( ':' )[ 0 ].strip()
		list = line.message.split( ':' )[ 1 ].split( ' ' )
		if chan == raceChannel.CHANNEL:
			for x in list:
				if x[ 0 ] == '@' or x[ 0 ] == '%' or x[ 0 ] == '+':
					self.oplist[ x[ 1: ] ] = True
		elif self.kicklist.has_key( chan[ 5: ] ):
			if self.kicklist[ chan[ 5: ] ].cycle < 2: self.kicklist[ chan[ 5: ] ].kick( list )
			else: 
				del self.kicklist[ chan[ 5: ] ]
					
	def quit( self, line ):
		if self.oplist.has_key( line.nick ) and line.channel == raceChannel.CHANNEL: del self.oplist[ line.nick ]	
		
	def join( self, line ):				
		if line.channel[ :5 ] == '#srl-':
			id = line.channel[ 5: ]
			data = getdata( id )
			if data[ 'entrants' ].has_key( line.nick.lower() ): self.send( 'MODE %s +v %s' % ( line.channel, line.nick ) )
		elif line.channel == raceChannel.CHANNEL:
			self.races( line )
	
	def mode( self, line ):
		try:
			if line.channel == raceChannel.CHANNEL:
				level = line.message.split( ' ' )[ 0 ]
				name = line.message.split( ' ' )[ 1 ]
				if level == '-v' or level == '-h' or level == '-o':
					if self.oplist.has_key( name ): del self.oplist[ name ]
				elif level == '+v' or level == '+h' or level == '+o': self.oplist[ name ] = True
		except: pass
			
	def startrace( self, line ):
		try:
			if len( line.message.split( ' ' ) ) > 2: self.send( 'PRIVMSG %s :.startrace <game abbrev>' % ( line.channel ) )
			elif len( line.message.split( ' ' )[ 1 ].strip() ):
					self.stopstart = True
					game = line.message.split( ' ' )[ 1 ].strip()
					params = json.dumps({ 'game': game })
					h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
					r = requests.post( "http://%s/races" % ( API.URL ), data=params, headers=h )
					data = json.loads( r.text )
					self.send( 'JOIN #srl-%s' % data[ 'id' ] )
					self.send( 'TOPIC #srl-%s :Status: Entry Open | Game: %s | Goal: ' % ( data[ 'id' ], data[ 'game' ][ 'name' ] ) )
					self.send( 'MODE #srl-%s +nst' % data[ 'id' ] )
					self.send( 'PRIVMSG %s :Race initiated for %s. Join4 #srl-%s to participate.' % ( raceChannel.CHANNEL, data[ 'game' ][ 'name' ], data[ 'id' ] ) )
					self.send( 'PRIVMSG %s-j :Race initiated for %s. Join4 #srl-%s to participate.' % ( raceChannel.CHANNEL, data[ 'game' ][ 'name' ], data[ 'id' ] ) )
					if data[ 'game' ][ 'abbrev' ] == 'newgame': self.send( 'PRIVMSG %s :Warning: Game doesn\'t exist yet.' % ( line.channel ) )
					timer = Thread( target=self.startracetimer )
					timer.daemon = True
					timer.start()
			else: self.send( 'PRIVMSG %s :.startrace <game abbrev>' % ( line.channel ) )

		except: self.send( 'PRIVMSG %s :.startrace <game abbrev>' % ( line.channel ) )
		
	def destroy( self ):
		r = requests.get( 'http://%s/races' % ( API.URL ) )
		data = json.loads( r.text )

		for i, x in enumerate( data[ 'races' ] ):
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			r = requests.delete( 'http://%s/races/%s' % ( API.URL, x[ 'id' ] ), headers=h )
		
	def races( self, line ):
		data = getraces()
		print data
		i = 1	
		if data[ 'races' ]:
			for x in data[ 'races' ]:
				if x[ 'state' ] < raceStatus.COMPLETE: 
					self.send( 'NOTICE %s %s. %s - %s |4 #srl-%s | %s entrant(s) | %s' % ( line.nick, i, x[ 'game' ][ 'name' ], x[ 'goal' ], x[ 'id' ], len( x[ 'entrants' ] ), status( x[ 'state' ] ) ) )
					i += 1
		else: self.send( 'NOTICE %s :No races in progress.' % ( line.nick ) )
		
	def queue( self, line ):
		data = getraces()
		i = 1
		if data[ 'races' ]:
			for x in data[ 'races' ]:
				if x[ 'state' ] >= raceStatus.COMPLETE: 
					self.send( 'NOTICE %s %s. %s - %s |4 #srl-%s | %s entrant(s) | %s' % ( line.nick, i, x[ 'game' ][ 'name' ], x[ 'goal' ], x[ 'id' ], len( x[ 'entrants' ] ), status( x[ 'state' ] ) ) )
					i += 1
				
	def setstream( self, line ):
		try:
			match = re.compile('(justin|twitch)(\.tv)?\/(channel\/)?([\w-]+)', re.I).search( line.message )
			if match == None: self.send ( 'PRIVMSG %s :Channel should be a full Twitch link, e.g. "http://twitch.tv/thegreatme"; or the site and channel separated by a slash, e.g. "twitch/thegreatme' % line.channel)
			else: 
				params = json.dumps({ 'channel': match.group( 4 ) })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				r = requests.put( "http://%s/streams/%s" % ( API.URL, line.nick ), data=params, headers=h )
				self.send( 'PRIVMSG %s :Stream set.' % line.channel )			
		except: pass
		
	def removestream( self, line ):
		try:
			if len( line.message.split( ' ' ) ) > 1: 
				name = line.message.split( ' ' )[ 1 ]
				params = json.dumps({ 'user': name })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				r = requests.delete( "http://%s/streams" % ( API.URL ), data=params, headers=h )
				self.send( 'PRIVMSG %s :Stream removed.' % line.channel )			
		except: pass
		
	def stream( self, line ):
		try:
			if len( line.message.split( ' ' ) ) > 1: 
				name = line.message.split( ' ' )[ 1 ]
				r = requests.get( "http://%s/streams/%s" % ( API.URL, name ) )
				streaminfo = json.loads( r.text )
				if streaminfo[ 'channel' ] != '': self.send( 'PRIVMSG %s :http://www.twitch.tv/%s' % ( line.channel, streaminfo[ 'channel' ] ) )
				else: self.send( 'PRIVMSG %s :Doesn\'t exist.' % ( line.channel ) )
		except: pass
			
	def creategame( self, line ):
		try:
			abbrev = line.message.split ( ' ' )[ 1 ]
			game = " ".join( line.message.split ( ' ' )[ 2: ] )[ :140 ]
			params = json.dumps({ 'name': game })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/games/%s' % ( API.URL, abbrev ), data=params, headers=h )
			self.send( 'PRIVMSG %s :Game: %s | Full name: %s' % ( line.channel, abbrev, game ) )
		except: pass
		
	def startracetimer( self ):
		time.sleep( 5 )
		self.stopstart = False
		
class Part:
	def __init__( self, irc, id ):
		self.id = id
		self.cycle = 0
		self.irc = irc
		self.timer = Thread( target=self.kicktimer )
		self.timer.daemon = True
		self.timer.start()
		
	def send( self, msg ):
		self.irc.send( '%s\r\n' % msg.encode('utf-8') )
		
	def namelist( self, id ):
		self.kicklist[ id ] = 0
		self.send( 'NAMES #srl-%s' % id )
		
	def kick( self, list ):
		for x in list:
			if x[ 0 ] == '@' or x[ 0 ] == '%' or x[ 0 ] == '+':
				name = x[ 1: ]
			else: name = x
			if name.lower() != botName.NAME.lower(): self.send( 'KICK #srl-%s %s' % ( self.id, name ) )
		self.cycle += 1
		self.send( 'NAMES #srl-%s' % self.id )
		if self.cycle == 2:
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.delete( 'http://%s/races/%s' % ( API.URL, self.id ), headers=h )
			self.send( 'PART #srl-%s' % self.id )
		
	def kicktimer( self ):
		time.sleep( 570 )
		self.data = getdata( self.id )
		if self.data[ 'state' ] == raceStatus.RECORDED:
			self.send ( 'PRIVMSG #srl-%s  :The channel will be cleared in 30 seconds!' % self.id )
			time.sleep( 30 )
			self.send( 'MODE #srl-%s +i' % self.id )
			self.data = getdata( self.id )
			if self.data[ 'state' ] == raceStatus.RECORDED:
				self.send( 'NAMES #srl-%s' % self.id )
			else: self.cycle = 2	
		else: self.cycle = 2
		
class Race:
	# This is for pretty much all the race commands
	# in race channels.
	def __init__( self, irc, line ):
		self.irc = irc
		self.line = line
		self.id = line.channel[ 5: ]
		self.data = getdata( self.id )		
		
	def all_ready( self, name ):
		if self.data[ 'numentrants' ] > 1 and self.data[ 'state' ] == raceStatus.ENTRY:
			rcount = readycheck( self.data, name )
			if rcount == -1: 
				params = json.dumps({ 'state': raceStatus.CD })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
				countdown( self.irc, self.line.channel, self.id, self.data['goal'], self.data['game']['name'], self.checkfilename() )
				
	def checkfilename( self ):
		if self.data['filename'] != '': 
			id_X = 2
			filename_id = ''.join( random.choice( string.ascii_uppercase ) for x in range( id_X ) )
			return filename_id
		else: return None
			
	def comment( self ):
		try:
			if self.data[ 'entrants' ].has_key( self.line.nick2 ) and ( self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] < 9994 or self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] == 9998 ) and ( self.data[ 'state' ] == raceStatus.BUSY or self.data[ 'state' ] == raceStatus.COMPLETE ):
				msg = " ".join( self.line.message.split ( ' ' )[ 1: ] )[ :140 ]
				params = json.dumps({ 'entrant': self.line.nick2, 'comment': msg })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
				self.send( 'PRIVMSG %s :Comment added.' % self.line.channel )
		except: pass
		
	def done_check( self ):
		self.data = getdata( self.id )
		race_done = True
		all_quit = True
		for x in self.data[ 'entrants' ]:
			if self.data[ 'entrants' ][ x ][ 'place' ] == playerStatus.READY or self.data[ 'entrants' ][ x ][ 'place' ] == playerStatus.ENTRY:
				race_done = False
				break
			elif self.data[ 'entrants' ][ x ][ 'place' ] < 9994:
				all_quit = False
		if race_done == True and all_quit == False: self.race_complete()
		elif race_done == True and all_quit == True: self.end()
		
	def dq( self ):
		try:
			if self.data[ 'state' ] > raceStatus.ENTRY and self.data[ 'state' ] < raceStatus.RECORDED:
				name = self.line.message.split( ' ' )[ 1 ].strip().lower()
				msg = self.line.nick + ': ' + " ".join( self.line.message.split ( ' ' )[ 2: ] )[ :140 ]
				if self.data[ 'entrants' ].has_key( name ):
					params = json.dumps({ 'disqualify': name })
					h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
					requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
					params = json.dumps({ 'entrant': name, 'comment': msg })
					requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
					self.send( 'PRIVMSG %s :%s has been disqualified from the race.' % ( self.line.channel, name ) )
					self.done_check()
		except: pass
		
	def end( self ):
		params = json.dumps({ 'state': raceStatus.RECORDED })
		h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
		requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
		self.send( 'PRIVMSG %s :Race terminated.' % self.line.channel )
		self.send( 'PRIVMSG #srl-%s :Race over! The channel will be cleared in 10 minutes!' % self.id )
		return self.id
		
	def enter( self ):
		if not self.data[ 'entrants' ].has_key( self.line.nick2 ) and self.data[ 'state' ] == raceStatus.ENTRY:
			params = json.dumps({ 'enter': self.line.nick2 })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
			if self.data['numentrants'] == 0: self.send( 'PRIVMSG %s :%s enters the race! %s entrant.' % ( self.line.channel, self.line.nick, self.data['numentrants'] + 1 ) )
			else: self.send( 'PRIVMSG %s :%s enters the race! %s entrants.' % ( self.line.channel, self.line.nick, self.data['numentrants'] + 1 ) )
			self.send( 'MODE %s +v %s' % ( self.line.channel, self.line.nick ) )
		else: pass
		
	def filename( self ):
		if self.data['state'] == raceStatus.ENTRY and self.data['filename'] == '': 
			params = json.dumps({ 'filename': 'True' })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
			self.send ( 'PRIVMSG %s :A filename will be randomly generated after the countdown.' % ( self.line.channel ) )
			
	def finish( self, option ):
		if self.data[ 'entrants' ].has_key( self.line.nick2 ) and self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] == playerStatus.READY and self.data[ 'state' ] == raceStatus.BUSY:
			if option == 1: 
				params = json.dumps({ 'done': self.line.nick2 })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
				self.data = getdata( self.id )
				self.send( 'PRIVMSG %s :%s has finished in %s place with a time of %s.' % ( self.line.channel, self.line.nick, fixplace( self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] ), time.strftime( "%H:%M:%S", time.gmtime( time.time() - self.data[ 'time' ] ) ) ) )
			elif option == 2:
				params = json.dumps({ 'forfeit': self.line.nick2 })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
				self.send( 'PRIVMSG %s :%s has forfeited from the race.' % ( self.line.channel, self.line.nick ) )
			self.done_check()
		elif self.data[ 'entrants' ].has_key( self.line.nick2 ) and self.data[ 'state' ] == raceStatus.ENTRY: self.unenter()
		
	def goal( self ):
		if self.data[ 'goal' ]: self.send( 'PRIVMSG %s :%s' % ( self.line.channel, self.data[ 'goal' ] ) )
		else: self.send( 'PRIVMSG %s :No goal.' % ( self.line.channel ) )
			
	def print_entrants( self ):
		if self.data['numentrants']:
			sorted_list = sort_players( self.data )
			entrants_e = ''
			entrants_i = 0
			for x in sorted_list:
				if entrants_i > 0: entrants_e += ' | '		
				info = entrantlist( x )		
				if len( entrants_e ) > 375: 
					self.send ( 'PRIVMSG %s  :%s' % ( self.line.channel, entrants_e ) )
					entrants_e = ''				
				entrants_e += '%s%s%s%s' % ( str( info.place ), info.name, info.time, info.message.decode('utf-8') )
				entrants_i += 1
				
			self.send ( 'PRIVMSG %s  :%s' % ( self.line.channel, entrants_e ) )
		else: self.send ( 'PRIVMSG %s  :No entrants.' % ( self.line.channel ) )
		
	def race_complete( self ):
		self.send( 'TOPIC #srl-%s :Status: Complete | Game: %s | Goal: %s' % ( self.id, self.data[ 'game' ][ 'name' ],self.data[ 'goal' ] ) )
		self.send ( 'PRIVMSG %s  :Race finished: %s - %s |4 #srl-%s | %s entrants' % ( raceChannel.CHANNEL, self.data[ 'game' ][ 'name' ], self.data[ 'goal' ], self.id, self.data[ 'numentrants' ] ) )
		params = json.dumps({ 'state': raceStatus.COMPLETE })
		h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
		requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
		
	def ready( self ):
		if self.data[ 'entrants' ].has_key( self.line.nick2 ) and self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] == playerStatus.ENTRY:
			if self.data[ 'goal' ] != '':
				params = json.dumps({ 'ready': self.line.nick2 })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
				if self.data[ 'numentrants' ] > 1:
					rcount = readycheck( self.data, None )
					self.send( 'PRIVMSG %s :%s is ready! %s remaining.' % ( self.line.channel, self.line.nick, rcount ) )
					if rcount == 0: 
						params = json.dumps({ 'state': raceStatus.CD })
						h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
						requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
						countdown( self.irc, self.line.channel, self.id, self.data['goal'], self.data['game']['name'], self.checkfilename() )
				else: self.send( 'PRIVMSG %s :%s is ready! Need more entrants!' % ( self.line.channel, self.line.nick ) )
			else: self.send( 'PRIVMSG %s :You must set a goal first!' % self.line.channel )
	
	def record( self ):
		if self.data[ 'state' ] == raceStatus.COMPLETE and goalcheck( self.data[ 'goal' ] ):
			if self.data[ 'game' ][ 'abbrev' ] == 'newgame':
				self.send( 'PRIVMSG #srl-%s :The game must be created with .creategame first!' % self.id )
				return None
			else:
				params = json.dumps({ 'record': 'true' })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
				self.send( 'PRIVMSG #srl-%s :Race recorded! The channel will be cleared in 10 minutes!' % self.id )
				self.print_entrants()
				self.send( 'PRIVMSG %s :Race recorded: http://speedrunslive.com/gamelist/#!/%s' % ( raceChannel.CHANNEL, self.data[ 'game' ][ 'abbrev' ] ) )
				return self.id
		else: return None
		
	def rematch( self ):
		if self.data[ 'state' ] == raceStatus.RECORDED:
			params = json.dumps({ 'rematch': 'true' })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
			self.removeallvoice()
			self.send( 'PRIVMSG #srl-%s :Rematch!' % self.id )
			self.send( 'TOPIC #srl-%s :Status: ENTRY OPEN | Game: %s | Goal: %s' % ( self.id, self.data[ 'game' ][ 'name' ], self.data[ 'goal' ] ) )
			self.send( 'PRIVMSG %s :Rematch initiated: %s -4 #srl-%s ' % ( raceChannel.CHANNEL, self.data[ 'game' ][ 'name' ], self.id ) )
			self.send( 'PRIVMSG %s-j :Rematch initiated: %s -4 #srl-%s ' % ( raceChannel.CHANNEL, self.data[ 'game' ][ 'name' ], self.id ) )
		else: pass
		
	def remove( self ):
		if self.data[ 'state' ] < raceStatus.RECORDED:
			if len( self.line.message.split( ' ' ) ) > 1: 
				name = self.line.message.split( ' ' )[ 1 ].lower()
				if self.data[ 'entrants' ].has_key( name ):
					params = json.dumps({ 'entrant': name })
					h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
					requests.delete( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
					self.send( 'PRIVMSG %s :%s has been removed from the race.' % ( self.line.channel, name ) )
					self.removevoice( name )
					self.done_check()
					self.all_ready(name.lower())
		
	def removevoice( self, name ):
		self.send( 'MODE %s -v %s' % ( self.line.channel, name ) )	
		
	def removeallvoice( self ):
		for x,i in enumerate(self.data['entrants']):
			self.send( 'MODE %s -v %s' % ( self.line.channel, i ) )
			
	def send( self, msg ):
		self.irc.send( '%s\r\n' % msg.encode('utf-8') )
		
	def setgame( self ):
		try:
			game = self.line.message.split ( ' ' )[ 1 ]
			params = json.dumps({ 'game': game })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
			self.data = getdata( self.id )
			self.send( 'PRIVMSG %s :Game Set: %s' % ( self.line.channel, self.data[ 'game' ][ 'name' ] ) )
			self.send( 'TOPIC #srl-%s :Status: %s | Game: %s | Goal: %s' % ( self.data[ 'id' ], self.data[ 'statetext' ], self.data[ 'game' ][ 'name' ] , self.data[ 'goal' ] ) )
		except: pass
		
	def setgoal( self ):
		goal = ' '.join( self.line.message.split ( ' ' ) [ 1: ] )
		params = json.dumps({ 'goal': goal })
		h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
		requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
		self.send( 'PRIVMSG %s :Goal Set: %s' % ( self.line.channel, goal ) )
		self.send( 'PRIVMSG %s :Goal Set: %s - %s |4 #srl-%s ' % ( raceChannel.CHANNEL, self.data[ 'game' ][ 'name' ], goal, self.data[ 'id' ] ) )
		self.send( 'PRIVMSG %s-j :Goal Set: %s - %s |4 #srl-%s ' % ( raceChannel.CHANNEL, self.data[ 'game' ][ 'name' ], goal, self.data[ 'id' ] ) )
		self.send( 'TOPIC #srl-%s :Status: %s | Game: %s | Goal: %s' % ( self.data[ 'id' ], self.data[ 'statetext' ], self.data[ 'game' ][ 'name' ] , goal ) )
		
	def time( self ):
		if self.data[ 'time' ] > 0: self.send( 'PRIVMSG %s :%s' % ( self.line.channel, time.strftime( "%H:%M:%S", time.gmtime( time.time() - self.data[ 'time' ] ) ) ) )	
		
			
	def undone( self ):
		if self.data[ 'entrants' ].has_key( self.line.nick2 ) and ( self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] < 9994 or self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] == 9998 ) and ( self.data[ 'state' ] == raceStatus.BUSY or self.data[ 'state' ] == raceStatus.COMPLETE ):
			params = json.dumps({ 'undone': self.line.nick2 })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
			self.send( 'PRIVMSG %s :%s has been undone from the race.' % ( self.line.channel, self.line.nick ) )
			if self.data[ 'state' ] == raceStatus.COMPLETE:
				params = json.dumps({ 'state': raceStatus.BUSY })
				requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
		
	def unenter( self ):
		if self.data[ 'entrants' ].has_key( self.line.nick2 ) and self.data[ 'state' ] == raceStatus.ENTRY:
			params = json.dumps({ 'entrant': self.line.nick2 })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.delete( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
			self.send( 'PRIVMSG %s :%s has been removed from the race.' % ( self.line.channel, self.line.nick ) )
			self.removevoice( self.line.nick )
			self.all_ready( self.line.nick2 )
		
	def unready( self ):
		if self.data[ 'entrants' ].has_key( self.line.nick2 ) and self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] == playerStatus.READY and self.data[ 'state' ] == raceStatus.ENTRY:
			params = json.dumps({ 'unready': self.line.nick2 })
			h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
			requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
			self.send( 'PRIVMSG %s :%s isn\'t ready!' % ( self.line.channel, self.line.nick ) )
			
	def undo( self ):
		try:
			name = self.line.message.split( ' ' )[ 1 ].strip().lower()
			if self.data[ 'entrants' ].has_key( name ) and ( self.data[ 'entrants' ][ name ][ 'place' ] < 9994 or self.data[ 'entrants' ][ self.line.nick2 ][ 'place' ] >= 9998 ) and ( self.data[ 'state' ] == raceStatus.BUSY or self.data[ 'state' ] == raceStatus.COMPLETE ):
				params = json.dumps({ 'undone': name })
				h = { 'X-SRL-API-KEY': '%s' % ( API.KEY ) }
				requests.put( 'http://%s/entrants/%s' % ( API.URL, self.id ), data=params, headers=h )
				self.send( 'PRIVMSG %s :%s has been undone from the race.' % ( self.line.channel, name ) )
				if self.data[ 'state' ] == raceStatus.COMPLETE:
					params = json.dumps({ 'state': raceStatus.BUSY })
					requests.put( 'http://%s/races/%s' % ( API.URL, self.id ), data=params, headers=h )
		except: pass
			
	
			
