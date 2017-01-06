#!/usr/bin/python
# -*- coding: utf-8 -*-

# Add bingos??
# team SRL requests
# Delete removestream

import socket
import sys
import raceProcess
from threading import Thread
import time

class raceChannel:
	CHANNEL = '#speedrunslive'
	
class botName:
	NAME = 'RaceBot'

def connect():
	# Connect to the IRC initially and if the bot ever disconnects
	network = 'irc.speedrunslive.com'
	port = 6667
	irc = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	irc.connect( ( network, port ) )
	trash = irc.recv( 4096 )
	trash = irc.recv( 4096 )
	irc.send( 'NICK %s\r\n' % ( botName.NAME ) )
	irc.send( 'USER %s %s %s :scooby poopy \r\n' % ( botName.NAME, botName.NAME, botName.NAME ) )
	ping = irc.recv( 4096 )
	print ping
	line = Line( ping )
	irc.send( 'PONG %s' % line.message )
	irc.send( 'PRIVMSG nickserv identify rocksoftly\r\n' )
	irc.send( 'OPER %s Cann0nl3ss\r\n' % ( 'ok' ) )
	irc.send( 'JOIN %s\r\n' % ( raceChannel.CHANNEL ) )
	irc.send( 'JOIN %s-j\r\n' % ( raceChannel.CHANNEL ) )
	print 'Connected!'
	return irc
	
class Line:
	def __init__( self, line ):
		# This class parses the data into an easy to use object
		try:
			if line.split( ' ' )[ 0 ] == 'PING':
				if len( line.split( ' ' ) ) > 1: 
					self.message = line.split( ':' )[ 1 ]
				else: self.server = line.split( ' ' )[ 1 ]
				self.cmd = 'PING'
			else: 
				self.nick = line.split( ' ' )[ 0 ].split( '!' )[ 0 ][ 1: ]
				self.nick2 = self.nick.lower()
				self.cmd = line.split( ' ' )[ 1 ]
				self.channel = line.split( ' ' )[ 2 ]
				if self.cmd == 'QUIT' or self.cmd == 'PART' or self.cmd == 'KICK' or self.cmd == 'MODE': self.message = ' '.join( line.split( ' ' )[ 3: ] )
				else: 
					self.message = ' '.join( line.split( ' ' )[ 3: ] )[ 1: ].strip()
					self.message = self.message.decode('utf-8')
		except: self.cmd = ''
		
class RaceBot:
	def __init__( self ):
		self.irc = connect()
		self.rp = raceProcess.Process( self.irc )
		connect_thread = Thread( target=self.thing )
		connect_thread.daemon = True
		connect_thread.start()
		self.rejoin()
		self.send( 'NAMES %s' % ( raceChannel.CHANNEL ) )
				
		while True:
			try:
				 # The data can come in as multiple lines so it needs to be split
				 # The last index is always blank so it must be deleted
				 # Loops through the data list and parses it
				data = self.irc.recv( 4096 ).split( '\r\n' )[ :-1 ]
				print data
				try:
					for x in data:
						line = Line( x ) # Store the line in an object
						if line.cmd == 'PRIVMSG':
							self.rp.process( line )
						elif line.cmd == 'JOIN': 
							line.channel = line.channel[ 1: ]
							self.rp.join( line )
						elif line.cmd == 'QUIT': self.rp.quit( line )
						elif line.cmd == '353': self.rp.names( line )
						elif line.cmd == 'MODE': self.rp.mode( line )
						elif line.cmd == 'PART': self.rp.quit( line )
						elif line.cmd == 'NICK': 
							line.channel = line.channel[ 1: ]
						elif line.cmd == 'KICK':
							tempnick = line.message.split( ' ' )[ 0 ]
							tempchan = line.channel
							line.channel = '%s from %s' % ( line.message.split( ' ' )[ 0 ], line.channel )
							line.message = line.message.split( ':' )[ 1 ]
							line.channel = '%s by %s' % ( tempchan, line.nick )
							line.nick = tempnick
							line.cmd = 'KICKED'
						elif line.cmd == 'PING':
							self.send( 'PONG %s' % line.server )
				except: self.send( 'PRIVMSG %s :ERROR' % ( raceChannel.CHANNEL ) )
						
						
			except socket.error, msg:
				# If the bot gets disconnected then this exception will
				# run every 30s until it reconnects
				self.irc.close()
				self.irc = connect()
				self.rp.irc = self.irc
				self.rejoin()
		
	def thing( self ):
		# Stay connected
		while True:
			try:
				time.sleep( 30 )
				self.send ( 'PING 204.45.18.66' )
			except: pass
			
	def send( self, msg ):
		self.irc.send( '%s\r\n' % msg.encode('utf-8') )
		
	def rejoin( self ):
		races = raceProcess.getraces()
		for x in races[ 'races' ]:
			self.send( 'JOIN #srl-%s' % x[ 'id' ] )
			self.send( 'MODE #srl-%s +o %s' % ( x[ 'id' ], botName.NAME ) )
		
RaceBot()
