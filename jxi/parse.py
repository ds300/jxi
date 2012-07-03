import string
"""
Author: David Sheldrick
Date: 2012-07-03
"""

###################
#### UTILITIES ####
###################

class JXIParseError(Exception):
	def __init__(self, message, line, line_start_char, index):
		self.line = line
		self.char = index-line_start_char+1
		msg = "Error detected at "
		msg += "line %s char %s\n" % (self.line, self.char)
		msg += "\tMessage: " + message
		self.msg = msg
	def __str__(self):
		return self.msg


##########################
#### LEXICAL ANALYSIS ####
##########################

def lex(input_text):
	"""
	This is obviously the jxi lexical analyser. It is of straightforward design
	"""

	whitespace = set([",", " ", "\v", "\t", "\n", "\r", "\f"])
	symbols = set(['<','>','[',']','{','}',':','/', '='])

	digits = set([str(i) for i in range(10)])
	digits_sans_zero = set([str(i) for i in range(1,10)])
	number_start_chars = digits | set(["-"])
	
	letters = set([c for c in string.lowercase + string.uppercase])
	word_chars = letters | set(["_"]) | digits

	json_string_escapes = {}
	for delim in ['"', "'"]:
		json_string_escapes[delim] = set(["\b", "\f", "\n", "\r", "\t", "\\", delim])

	control_characters = {
		"b": "\b",
		"f": "\f",
		"n": "\n",
		"r": "\r",
		"t": "\t",
		"\\": "\\",
		"/": "/"
	}

	for delim in json_string_escapes:
		control_characters[delim] = delim

	raw_string_escapes = {}
	for delim in ["`"]:
		raw_string_escapes[delim] = set(["\\", delim])

	reserved_word_types = {"null":"null", "true":"bool", "false":"bool"}

	line = 1
	line_start_char = 0

	inp = input_text
	i = 0

	size = len(input_text)

	# right! let's iterate over this text and do some lexical analysis
	while i < size:
		# skip over whitespace
		while inp[i] in whitespace:
			if inp[i] == "\n":
				line += 1
				line_start_char = i
			i += 1

		# figure out what type of token we're dealing with

		### SYMBOLS ###
		if inp[i] in symbols:
			yield ("sym", inp[i])
			i += 1

		### IDENTS ###
		elif inp[i] in letters:
			j = i+1
			while inp[j] in word_chars:
				j += 1
			yield (reserved_word_types.get(inp[i:j], "ident"), inp[i:j])
			i = j

		### JSON STRINGS ###
		elif inp[i] in json_string_escapes:
			# get the delimiter being used and the corresponding escape chars
			delim = inp[i]
			escapes = json_string_escapes[delim]

			# skip over delimiter
			i += 1
			text = ""

			# keep going until we see the delimiter again
			while inp[i] != delim:
				# get the next sequence of chars not containing escapes and concat
				j = i
				while inp[j] not in escapes:
					j += 1
				text += inp[i:j]
				i = j

				# now we're at a character that requires action to be taken
				if inp[i] == "\\":
					# we need to escape something
					i += 1

					### CONTROL CHARS ###
					if inp[i] in control_characters:
						# put the control character in the string
						text += control_characters[inp[i]]
						i += 1

					### UNICODE STUFFS ###
					elif inp[i] == "u":
						# do the 4-hexit unicode thing
						# this algorithm shamelessly stolen from Doug Crockford's 
						# javascript json parser (the one that doesn't use eval)
						charcode = 0
						i += 1
						for j in range(4):
							try:
								u = int(inp[i], 16)
							except ValueError:
								msg = "invalid unicode hexadecimal format"
								raise JXIParseError(msg, line, line_start_char, i)
							charcode = charcode * 16 + u
							i += 1
						text += unichr(charcode).encode("utf-8")

					else:
						msg = "Invalid escape sequence '\\%s'" % inp[i]
						raise JXIParseError(msg, line, line_start_char, i)

				elif inp[i] != delim:
					msg = "Unescaped %s detected in string literal" % repr(inp[i])
					raise JXIParseError(msg, line, line_start_char, i)

			# skip over final delimiter
			i += 1
			yield ("string", text)

		### NUMBERS ###
		elif inp[i] in number_start_chars:
			numtype = int
			j = i
			# optional minus
			if inp[j] == "-":
				j += 1
			
			# either 0 or 1-9
			if inp[j] == "0":
				j += 1
			elif inp[j] in digits_sans_zero:
				# if 1-9, then any other digits may follow
				while inp[j] in digits:
					j += 1
			else:
				msg = "Expecting digit after '-', got %s" % repr(inp[j])
				raise JXIParseError(msg, line, line_start_char, j)

			# optional . followed by more digits
			if inp[j] == ".":
				numtype = float
				j += 1
				if inp[j] not in digits:
					msg = "Expecting digit after '.', got %s" % repr(inp[j])
					raise JXIParseError(msg, line, line_start_char, j)

				while inp[j] in digits:
					j += 1

			# optional exponent
			if inp[j] in ("E", "e"):
				numtype = float
				j += 1

				# optional + or -
				if inp[j] in ("+", "-"):
					j += 1

				# at least one digit
				if inp[j] not in digits:
					msg = "Expecting exponent value, got %s" % repr(inp[j])
					raise JXIParseError(msg, line, line_start_char, j)

				while inp[j] in digits:
					j += 1

			yield ("int" if numtype == int else "float", inp[i:j])
			i = j

		### RAW STRINGS ###
		elif inp[i] in raw_string_escapes:
			# get delimiter and related escapes
			delim = inp[i]
			escapes = raw_string_escapes[delim]

			# skip over delimiter
			i += 1
			text = ""

			# keep going until we see the delimiter again
			while inp[i] != delim:
				# get the next string of uninteresting chars and concat
				j = i
				while inp[j] not in escapes:
					j += 1
				text += inp[i:j]
				i = j

				# now we're at an interesting char
				if inp[i] == "\\":
					i += 1
					# only need to escape if it's the delimiter
					if inp[i] == delim:
						text += delim
					else:
						# otherwise, that backslash was meant to be there
						# better put it back in
						text += "\\"

			# ignore final delimiter
			i += 1
			yield ("rawstring", text)

		else:
			msg = "Illegal character %s" % repr(inp[i])
			raise JXIParseError(msg, line, line_start_char, i)

	yield ("EOF", "EOF")



