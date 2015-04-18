# vim:ts=4
import re
from CRC import do_crc
from select import select
import socket, logging
from time import time, sleep

asynchronous_responses = [	'400', '401', # door open/closed
				'610',        # switches changed
				'200', '201', '202', '203', '204', '205', '206',
				'207', '208', '209', '211', # key presses
			 ]
DOOR = 1
SWITCH = 2
KEY = 3
TICK = 4

class VendingException(Exception): pass

class VendingMachine:
	def __init__(self, rfh, wfh):
		self.events = []
		# Secret
		self.secret = 'SN4CKZ0RZZZZZZZZ'
		self.rfh = rfh
		self.wfh = wfh
		self.challenge = None
		# Initialise ourselves into a known state
		self.wfh.write('\n')
		self.await_prompt()
		self.wfh.write('echo off\n')
		self.await_prompt()
		self.wfh.write('PING\n')
		code = ''
		while code != '000':
			code = self.get_response()[0]
		self.get_switches()

	def await_prompt(self):
		self.wfh.flush()
		state = 1
		timeout = 0.5
		prefix = ''
		s = ''
		# mtearle - vending machine was dying wait for a response from
		# the hardware, suspect it was missing characters
		#
		# fixed by migration to pyserial - but future good place to start
		while True:
			try:
				s = self.rfh.read(1)
			except socket.error:
				raise VendingException('failed to read input from vending machine')
			if s == '': raise VendingException('nothing read!')
			if (s != '#' and s != '%') and state == 1: prefix += s
			if s == '\n' or s == '\r':
				state = 1
				prefix = ''
			if (s == '#' or s == '%') and state == 1: state = 2
			if s == ' ' and state == 2:
				if prefix == '':
					self.challenge = None
					return
				if re.search('^[0-9a-fA-F]{4}$', prefix):
					self.challenge = int(prefix, 16)
					return

	def get_response(self, async = False):
		self.wfh.flush()
		while True:
			s = ''
			while s == '':
				s = self.rfh.readline()
				if s == '':
					raise VendingException('Input socket has closed!')
				s = s.strip('\r\n')
			code = s[0:3]
			#print(code)
			text = s[4:]
			if code in asynchronous_responses:
				self.handle_event(code, text)
				if async: return None
			else:
				self.await_prompt()
				return (code, text)

	def get_switches(self):
		self.wfh.write('S\n')
		(code, text) = self.get_response()
		if code != '600':
			return (False, code, text)
		self.interpret_switches(text)
		return (True, code, text)

	def interpret_switches(self, text):
		self.switches = (int(text[0:2], 16) << 8) | int(text[3:5], 16)

	def handle_event(self, code, text):
		if code == '400':
			self.events.append((DOOR, 1))
		elif code == '401':
			self.events.append((DOOR, 0))
		elif code == '610':
			# NOP this. Nothing handles this yet.
			#self.events.append((SWITCH, None))
			self.interpret_switches(text)
		elif code[0] == '2':
			#print((KEY, int(code[1:3])))
			self.events.append((KEY, int(code[1:3])))
		else:
			logging.warning('Unhandled event! (%s %s)\n'%(code,text))

	def authed_message(self, message):
		if self.challenge == None:
			return message
		print 'self.challenge = %04x' % self.challenge
		crc = do_crc('%c%c'%(self.challenge >> 8, self.challenge & 0xff))
		crc = do_crc(self.secret, crc)
		crc = do_crc(message, crc)
		print 'output = "%s|%04x"' % (message, crc)
		return message+'|'+('%04x'%crc)

	def ping(self):
		self.wfh.write('PING\n')
		(code, string) = self.get_response()
		return (code == '000', code, string)

	def vend(self, item):
		if not re.search('^[0-9][0-9]$', item):
			return (False, 'Invalid item requested (%s)'%item)
		self.wfh.write(self.authed_message(('V%s'%item))+'\n')
		(code, string) = self.get_response()
		return (code == '100', code, string)

	def beep(self, duration = None, synchronous = True):
		msg = 'B'
		if synchronous: msg += 'S'
		if duration != None:
			if duration > 255: duration = 255
			if duration < 1: duration = 1
			msg += '%02x'%duration
		self.wfh.write(msg+'\n')
		(code, string) = self.get_response()
		return (code == '500', code, string)

	def silence(self, duration = None, synchronous = True):
		msg = 'C'
		if synchronous: msg += 'S'
		if duration != None:
			if duration > 255: duration = 255
			if duration < 1: duration = 1
			msg += '%02x'%duration
		self.wfh.write(msg+'\n')
		(code, string) = self.get_response()
		return (code == '501', code, string)

	def display(self, string):
		# display first ten characters of string, left aligned
		self.wfh.write('D%-10.10s\n' % string)

		(code, string) = self.get_response()
		return (code == '300', code, string)

	def next_event(self, timeout = None):
		# we don't want to buffer in the serial port, so we get all the events
		# we can ASAP.

		# Never have no timeout...
		if timeout == None: timeout = 60*60*24*365

		# Make sure we go through the loop at least once.
		if timeout < 0: timeout = 0

		while timeout >= 0:
			this_timeout = min(timeout, 0.2)
			timeout -= this_timeout

			(r, _, _) = select([self.rfh], [], [], this_timeout)
			if r:
				self.get_response(async = True)
				timeout = 0

			if timeout == 0:
				break

		if len(self.events) == 0: return (TICK, time())
		ret = self.events[0]
		del self.events[0]
		return ret

	def get_key(self):
		# Clear any current events
		self.events = []
		#self.get_response()
		event = self.next_event()
		while event[0] != 3:
			event = self.next_event()
		return event[1]

