import re, sys, pyjxi
"""
Author: David Sheldrick
Date: 2012-07-02
"""

###################
#### UTILITIES ####
###################

class JXIParseError(Exception):
	def __init__(self, message):
		msg = "JXIParseError: detected at "
		msg += "line %s char %s\n" % (line, index-line_start_char+1)
		msg += "\tMessage: " + message
		Exception.__init__(msg)

class FileWrapper(object):
	"""
	This class wraps a file-like object such that incremental indexing works
	as with a string.

	It only keeps 2kb worth of string in memory an any one time (obviously
	without regard for delay in GC).
	"""
	def __init__(self, fileobj):
		self.fo = fileobj
		self.start = 0
		self.end = 0
		self.buffer = ""
		self[0]

	def __len__(self):
		return self.end

	def __getitem__(self, key):
		if key == self.end:
			# Load the next chunk of text from the file into the buffer and
			# update the start/end indices
			self.start += len(self.buffer)

			self.buffer = self.fo.read(2048)
			if not self.buffer: raise IndexError()

			self.end += len(self.buffer)

			return self.buffer[0]

		return self.buffer[key-self.start]


##########################
#### LEXICAL ANALYSIS ####
##########################

# The regular expressions we'll be using
re_white = re.compile(r"[\s,]") # totally ignore commas
re_alpha = re.compile(r'[a-zA-Z]')
re_word = re.compile(r'\w')
re_num_start = re.compile(r'[\d\-]')
# this next regex with thanks to Doug Crockford or whoever drew 
# that diagram on the json website
re_num = re.compile(r'^-?(0|[1-9]\d*)(\.\d+)?((e|E)(\+|-)?\d+)?')

# the various symbols we need to recognise
symbols = set(['<','>','[',']','{','}',':','/', '='])
string_delimiters = set(['"', "'"])
raw_string_delimiters = set(["`"])
control_characters = {
	"b": "\b",
	"f": "\f",
	"n": "\n",
	"r": "\r",
	"t": "\t"
}

# the input data/metadata
input_text = ""
line = 1
line_start_char = 0
index = -1
c = ""

# get the next character
def next_char():
	global index, c
	index += 1
	c = input_text[index]
	return c

def lex(arg):
	"""
	This is obviously the jxi lexical analyser. It is of straightforward design
	"""
	global line, line_start_char, index, input_text

	# re-initialise variables in-case this gets called more than once
	line = 1
	line_start_char = 0
	index = -1

	# get text
	if isinstance(arg, basestring):
		input_text = arg
	else:
		# assume it's a file-like object. If not, let the caller handle the 
		# exception
		input_text = FileWrapper(arg)

	# set up one-character lookahead
	next_char()

	# now let's do some lexical analysis
	try:
		while True:
			# ignore whitespace
			while re_white.match(c):
				if c == "\n":
					line += 1
					line_start_char = index
				next_char()

			# now figure out what type of token we're dealing with

			## IDENTIFIERS ##
			if re_alpha.match(c):
				# build the indentifer from the input text
				ident = ""
				while re_word.match(c):
					ident += c
					next_char()

				# now check for reserved words
				if ident in ("true", "false"): yield ("bool", ident)
				elif ident == "null": yield ("null", "null")
				# not a reserved word, so it's an identifer
				else: yield ("ident", ident)

			## JSON STRING LITERALS ##
			elif c in string_delimiters:
				delim = c # save the delimiter
				next_char() # but don't add it to the string, obviously
				string = ""
				while c != delim:
					if c == "\\":
						# we might need to escape something
						next_char()

						if c in control_characters:
							string += control_characters[c]
							next_char()

						elif c == "u":
							# we've got a 4-hexit unicode thing
							charcode = 0
							next_char()
							for i in range(4):
								try:
									u = int(c, 16)
								except ValueError:
									raise JXIParseError("invalid unicode escape sequence")
								charcode = charcode * 16 + u
								next_char()
							string += unichr(charcode)

						else:
							string += c
							next_char()

					else:
						string += c
						next_char()

				# ignore final delimiter
				next_char()
				yield ("string", string)

			## RAW STRING LITERALS ##
			elif c in raw_string_delimiters:
				delim = c
				next_char()
				string = ""
				while c != delim:
					if c == "\\":
						next_char()
						# only escape the next character if it is the delimiter
						if c != delim:
							string += "\\"
					string += c
					next_char()

				# ignore final delimiter
				next_char()
				yield ("rawstring", string)

			## NUMBERS ##
			elif re_num_start.match(c):
				numtype = int
				# optional negative
				if c == "-":
					numstring = c
					next_char()
				else:
					numstring = ""

				# either 0 or 1-9
				if c == "0":
					numstring += 0
				else:
					if not "1" <= c <= "9":
						raise JXIParseError("invalid number '%s'" % numstring+c)
					numstring += c
					next_char()
					# if 1-9, any series of digits now
					while "0" <= c <= "9":
						numstring += c
						next_char()

				# optional decimal place with more digits
				if c == ".":
					numtype = float
					numstring += c
					next_char()
					if not "0" <= c <= "9":
						raise JXIParseError("invalid number '%s'" % numstring+c)

					while "0" <= c <= "9":
						numstring += c
						next_char()

				# optional exponent
				if c in ("e", "E"):
					numtype = float
					numstring += c
					next_char()
					# optional +/-
					if c in ("+", "-"):
						numstring += c
						next_char()
					# at least one digit for the exponent
					if not "0" <= c <= "9":
						raise JXIParseError("invalid number '%s'" % numstring+c)

					while "0" <= c <= "9":
						numstring += c
						next_char()

				# and that's the number finished
				strnumtype = re.match(r"^<type '(.*?)'>$", str(numtype)).group(1)
				yield (strnumtype, numtype(numstring))

			## SYMBOLS ##
			elif c in symbols:
				yield ("sym", c)
				next_char()

			## ILLEGAL CHARACTERS ##
			else:
				yield ("ill", c)
				next_char()

	except IndexError:
		while True:
			yield ("EOF", "EOF")

for token in lex(open("test.jxi")):
	if token[0] == "EOF": break
	print token

