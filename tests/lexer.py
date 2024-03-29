# coding=utf-8
import unittest, sys, os, random, string
sys.path.append(os.path.abspath("../jxi/"))
from lex import lex, JXIParseError

# We're gonna do some proper white box testing here and attempt to get
# full statement coverage

# ok so the structure of the lexer's loop is like this:

# 1. skip whitespace
# 	1.1 increase line number/relative char index

# 2. symbols

# 3. idents
# 	3.1 idents with len > 1

# 4. json strings
# 	4.1 non-empty strings
# 		4.1.1 string of uninteresting chars
# 		4.1.2 backslash escape
# 			4.1.2.1 control characters
# 			4.1.2.2 unicode literals
# 				4.1.2.2.1 get 4 hex chars
# 					4.1.2.2.1.1 EXCEPTION: non-hex char
# 			4.1.2.3 EXCEPTION: invalid escape sequence
# 		4.1.3 EXCEPTION: unescaped somethingorother

# 5. numbers
# 	5.1 optional minus
# 	5.2 starts with 0
# 	5.3 starts with 1-9 followed by any number of other digits
# 	5.4 EXCEPTION: something other than 0-9 after initial minus
# 	5.5 optional "."
# 		5.5.1 EXCEPTION: "." not followed by digit
# 	5.6 optional exponent
# 		5.6.1 optional + or -
# 		5.6.2 EXCEPTION: no digits given

# 6. raw strings
# 	6.1 non-empty strings
# 		6.1.1 string of uninteresting chars
# 		6.1.2 possible backslash escape
# 			6.1.2 delimiter needs escaping
# 			6.1.2 backslash was meant as just a backslash

# places where index errors can occur, leading to EOF:
# 	1 file ends with whitespace
# 	3.1 file ends with ident
# 	4.1 file ends after valid backslash escape in string literal
# 	4.1.2 file ends during string literal
# 	4.1.2.2.1 \u escape with less than 4 digits
# 	5.2 file ends with a "-"
# 	5.3 file ends with integer
# 	5.5.1 file ends with a "."
# 	5.5 file ends with digits after a "."
# 	6.1 file ends after valid backslash escape in raw string literal
# 	6.1.2 file ends during raw string literal


whitespace_chars = [",", " ", "\v", "\t", "\n", "\r", "\f"]

# 1. skip whitespace
# 	1.1 increase line number/relative char index
class TestSkipWhitespace(unittest.TestCase):
	def test_skip(self):
		# check that whitespace chars get ignored with random orderings
		for i in range(1000):
			random.shuffle(whitespace_chars)
			string = "".join(whitespace_chars)
			self.assertEqual(lex(string).next(), ("EOF", "EOF"))

		# do the same thing for a really long string
		string = ""
		for i in range(10000):
			string += random.choice(whitespace_chars)
		self.assertEqual(lex(string).next(), ("EOF", "EOF"))

	def test_line_char_numbers(self):
		string = " \t  &" # '&' is the illegal character
		with self.assertRaises(JXIParseError) as cm:
			for token in lex(string):
				pass
		self.assertEqual(cm.exception.line, 1)
		self.assertEqual(cm.exception.char, 5)

		string = "\n\n\n   &"
		with self.assertRaises(JXIParseError) as cm:
			for token in lex(string):
				pass
		self.assertEqual(cm.exception.line, 4)
		self.assertEqual(cm.exception.char, 4)

		string = "\n    \n    \t\t   \n \n  &"
		with self.assertRaises(JXIParseError) as cm:
			for token in lex(string):
				pass
		self.assertEqual(cm.exception.line, 5)
		self.assertEqual(cm.exception.char, 3)

		string = "&"
		with self.assertRaises(JXIParseError) as cm:
			for token in lex(string):
				pass
		self.assertEqual(cm.exception.line, 1)
		self.assertEqual(cm.exception.char, 1)

		string = "\n&"
		with self.assertRaises(JXIParseError) as cm:
			for token in lex(string):
				pass
		self.assertEqual(cm.exception.line, 2)
		self.assertEqual(cm.exception.char, 1)

# 2. symbols
class TestSymbols(unittest.TestCase):
	def test_symbols(self):
		symbols = ['<','>','[',']','{','}',':','/', '=', "@"]
		for symbol in symbols:
			self.assertEqual(lex(symbol).next(), ("sym", symbol))

		badsymbols = ['+', "|", "\\", "˙", "µ", "*", "$",
		              "!", "£", "?", "~", "^", "%"]
		for symbol in badsymbols:
			with self.assertRaises(JXIParseError):
				print lex(symbol).next()


# 3. idents
class TestIdents(unittest.TestCase):
	def test_single_char_idents(self):
		for c in string.lowercase+string.uppercase:
			self.assertEqual(lex(c).next(), ("ident", c))

		# check that single underscore doesn't work
		with self.assertRaises(JXIParseError):
			lex("_ ").next()

# 	3.1 idents with len > 1
	def test_lengthy_idents(self):
		idents = [
			"a9",
			"a_",
			"b____________",
			"P89020e9r80",
			"KKKKKKKKKKKKK",
			"x_2_4F_J_7_9a"
		]
		for ident in idents:
			self.assertEqual(lex(ident).next(), ("ident", ident))
			with self.assertRaises(JXIParseError):
				lex("_"+ident).next()

#	3.1.2 reserved words
	def test_reserved_words(self):
		bools = ["true", "false"]
		for b in bools:
			self.assertEqual(lex(b+" ").next(), ("bool", b))
		self.assertEqual(lex("null ").next(), ("null",  "null"))


# 4. json strings
class TestJsonStrings(unittest.TestCase):
	def test_empty_strings(self):
		self.assertEqual(lex("''").next(), ("string",  ""))
		self.assertEqual(lex('""').next(), ("string",  ""))
# 	4.1 non-empty strings
# 		4.1.1 string of uninteresting chars
	def test_uninteresting_chars(self):
		for delim in ["'", '"']:
			interesting_chars = set(["\b", "\f", "\n", "\r", 
			                         "\t", "\\", delim])
			for i in xrange(100):
				text = u""
				for j in xrange(random.randint(1,1000)):
					c = unichr(random.randint(0,65535))
					if c not in interesting_chars:
						text+=c

				self.assertEqual(lex(delim+text+delim).next(), ("string", text.encode("utf-8")))

# 		4.1.2 backslash escape
# 			4.1.2.1 control characters
	def test_escape_sequences(self):
		input_string = "bnananas\\b and \\n ann\\f\\rn\\\"nd coff\\\\ee\\'are\\n\\t\\ttasty"
		expected = "bnananas\b and \n ann\f\rn\"nd coff\\ee'are\n\t\ttasty"

		for delim in ["'",'"']:
			self.assertEqual(lex(delim+input_string+delim).next(), ("string", expected))

# 			4.1.2.3 EXCEPTION: invalid escape sequence
		invalid_string = "banana \\ in my eye"
		with self.assertRaises(JXIParseError) as e:
			lex("'%s'" % invalid_string).next()

# 		4.1.3 EXCEPTION: unescaped somethingorother
		with self.assertRaises(JXIParseError):
			lex("'blahblah blah\n blah'").next()

		# also check unterminated string
		with self.assertRaises(JXIParseError):
			lex('"blahblahblah').next()


# 			4.1.2.2 unicode literals
	def test_unicode_literals(self):
# 				4.1.2.2.1 get 4 hex chars
		input_string = u"主要提供网页、音乐、图片、新闻搜索，同时有帖吧和WAP搜索功 टठडणष\nཏ ཐདནཤ"
		def strip_and_pad(hexstr):
			if hexstr.startswith("0x"):
				hexstr = hexstr[2:]
			while len(hexstr) < 4:
				hexstr = "0" + hexstr
			return hexstr
		hexes = [strip_and_pad(hex(ord(c))) for c in input_string]
		escaped = "'\\u%s'" % "\\u".join(hexes)
# 					4.1.2.2.1.1 EXCEPTION: non-hex char
		with self.assertRaises(JXIParseError):
			lex("'helloth\uab4xere'").next()
		with self.assertRaises(JXIParseError):
			lex("'helloth\ugb41ere'").next()
		with self.assertRaises(JXIParseError):
			lex("'helloth\uabv0ere'").next()
		with self.assertRaises(JXIParseError):
			lex("'helloth\uat6fxere'").next()

class TestNumbers(unittest.TestCase):
# 5. numbers
	def test_numbers(self):
# 	5.1 optional minus
		self.assertEqual(lex("-5").next(), ("int", -5))
		self.assertEqual(lex("-5.01234").next(), ("float", -5.01234))
# 	5.2 starts with 0
		self.assertEqual(lex("0").next(), ("int", 0))
		self.assertEqual(lex("0.124").next(), ("float", 0.124))

		# check preceding 0s get stripped
		self.assertEqual(lex("00").next(), ("int", 0))
		self.assertEqual(lex("000004").next(), ("int", 4))
		self.assertEqual(lex("00000").next(), ("int", 0))
		self.assertEqual(lex("00000.124").next(), ("float", 0.124))
		self.assertEqual(lex("00000.0").next(), ("float", 0))
		self.assertEqual(lex("00000001.124").next(), ("float", 1.124))
# 	5.5 optional "."
		# already taken care of
# 		5.5.1 EXCEPTION: "." not followed by digit
		with self.assertRaises(JXIParseError):
			lex("000234.").next()
		with self.assertRaises(JXIParseError):
			lex("000234.s").next()
		with self.assertRaises(JXIParseError):
			lex("000234.#").next()
# 	5.6 optional exponent
		self.assertEqual(lex("10e4").next(), ("float", 10e4))
		self.assertEqual(lex("0.3e42").next(), ("float", 0.3e42))
		self.assertEqual(lex("0.312342e3").next(), ("float", 0.312342e3))
# 		5.6.1 optional + or -
		self.assertEqual(lex("10e-4").next(), ("float", 10e-4))
		self.assertEqual(lex("00.3e-42").next(), ("float", 0.3e-42))
		self.assertEqual(lex("0.312342e+3").next(), ("float", 0.312342e+3))
# 		5.6.2 EXCEPTION: no digits given
		with self.assertRaises(JXIParseError):
			lex("000234.4e").next()
		with self.assertRaises(JXIParseError):
			lex("000234.5e-").next()
		with self.assertRaises(JXIParseError):
			lex("000234e+").next()

# 6. raw strings
class TestRawStrings(unittest.TestCase):
	def test_empty_strings(self):
		self.assertEqual(lex("``").next(), ("rawstring", ""))
# 	6.1 non-empty strings
	def test_nonempty_strings(self):
		self.assertEqual(lex("`hello i am a\n string`").next(), ("rawstring", "hello i am a\n string"))
# 		6.1.1 string of uninteresting chars
	def test_uninteresting_chars(self):
		interesting_chars = set(["\\", "`"])
		for i in xrange(100):
			text = u""
			for j in xrange(random.randint(1,1000)):
				c = unichr(random.randint(0,65535))
				if c not in interesting_chars:
					text+=c

			self.assertEqual(lex(u"`%s`" % text).next(), ("rawstring", text.encode("utf-8")))
# 		6.1.2 possible backslash escape
	def test_backslash_escape(self):
		# backslashes only escape backticks. The rest of the time they are kept in
		noescape = "blahblah\\blahfun\\nblahetc"
		escape = "blahblahblah\\`somethingblah"
		escape_expected = "blahblahblah`somethingblah"

# 			6.1.2 backslash was meant as just a backslash
		self.assertEqual(lex("`%s`" % noescape).next(), ("rawstring", noescape))
# 			6.1.2 delimiter needs escaping
		self.assertEqual(lex("`%s`" % escape).next(), ("rawstring", escape_expected))



if __name__ == "__main__":
	unittest.main()
