# coding=utf-8
import re, StringIO
# the various regular expressions the lexer uses
_re_alpha = re.compile(r'^[a-zA-Z]$') # $ to avoid matching "EOF"
_re_word = re.compile(r'^\w')
_re_white = re.compile(r'^\s')
_re_num_start = re.compile(r'[\d\-]')
_re_num = re.compile(r'^-?(0|[1-9]\d*)(\.\d+)?((e|E)(\+|-)?\d+)?')


# the various symbols we need to recognise
_symbols = set(['<','>',',','[',']','{','}',':','/', '='])
_string_delimeters = set(['"',"'"])


class _Lexer(object):
	"""Lexical analyser for this pseudo-xml format"""
	def __init__(self, text):
		"""Initilises the lexer with some string"""
		self.text = text
		self.line = 1
		self.index = -1
		self.c = "" # current character
		self.next()

	def next(self):
		self.index += 1
		try:
			self.c = self.text[self.index]
		except IndexError:
			self.c = "EOF"

	# returns a string starting with a letter and containing 
	# characters in the \w character class
	def get_name(self):
		i = self.index
		self.next()
		while _re_word.match(self.c) and self.index < len(self.text):
			self.next()
		return self.text[i:self.index]

	def get_number(self):
		match = _re_num.match(self.text[self.index:])
		if match:
			num = match.group(0)
			# skip over the number in the file
			self.index += match.end(0) - 1
			self.next()
			# decide if we're returning a float or an int
			if num.isdigit() or num.startswith("-") and num[1:].isdigit():
				return ("int", int(num))
			else:
				return ("float", float(num))
		else:
			illegal = self.c
			self.next() # maintain lookahead
			return ("ill", illegal)

	# returns a string literal (sans delimeters and with escapes removed)
	def get_string_literal(self):
		delim = self.c
		ends = set([delim, "EOF"])
		i = self.index + 1 # +1 to not capture string delimeter
		self.next()
		chars = []
		while self.c not in ends:
			if self.c == '\\':
				# backslash so skip over
				self.next()
			chars.append(self.c)
			self.next()
		self.next() # maintain lookahead
		return ''.join(chars)

	def get_next_token(self):
		"""returns the next available token from the given text"""
		# skip over whitespace
		while _re_white.match(self.c):
			if self.c == "\n": self.line += 1
			self.next()
		# determine token type
		if _re_alpha.match(self.c):
			# alpha character so tag or attribute name
			name = self.get_name()
			if name in ("true", "false"):
				return ("bool", name == "true")
			elif name == "null": return ("null", None)
			else:
				return ("name", name)
		elif _re_num_start.match(self.c):
			# digit so integer of some sort
			return self.get_number()
		elif self.c in _symbols:
			sym = self.c
			self.next() # maintain lookahead
			return ("sym", sym)
		elif self.c in _string_delimeters:
			# string literal
			try:
				return ("str", self.get_string_literal())
			except IndexError:
				return ("EOF", "EOF")
		elif self.c == "EOF":
			return ("EOF", "EOF")
		else:
			# nothing fits so its an illegal character
			illegal = self.c
			self.next() # maintain lookahead
			return ("ill", illegal)
	

#############################################################
##### JXITag is the base entity object of the jxi world #####
#############################################################

class JXITag(object):
	"""Represents a tag in the tree"""
	def __init__(self, name="", attrs={}, children=[]):
		self._children = children
		self._tag_name = name

		self._refresh_child_groups()

		# assign attributes
		for key, val in attrs.items():
			object.__setattr__(self, key, val)

	def _add(self, tag, position=None):
		if type(tag) == JXITag:
			if position == None:
				self._children.append(tag)
				self.__add_child_to_groups(tag)
			else:
				self._children[position:position] = [tag]
				self.__add_child_to_groups(tag, position)
		else:
			raise TypeError("a jxi tag's children must be other jxi tags")

	def _remove(self, tag):
		if type(tag) == int:
			del self[tag]
		elif type(tag) == JXITag:
			del self[_children.index(tag)]
		else:
			raise KeyError("invalid key type")


	def __add_child_to_groups(self, child, position=None):
		if child._tag_name not in self._child_groups:
			self._child_groups[child._tag_name] = []
		
		if position == None or len(self._child_groups[child._tag_name]) == 0:
			self._child_groups[child._tag_name].append(child)
		else:
			group = self._child_groups[child._tag_name]
			for i in range(len(group)):
				if self._children.index(group[i]) > position:
					group.insert(i, child)
					return

	@classmethod
	def _parse(cls, text):
		return _parse(text, cls)
			

	def _refresh_child_groups(self):
		self._child_groups = {}

		# group children by tag name
		for child in self._children:
			self.__add_child_to_groups(child)
			

	def __getitem__(self, key):
		if type(key) == str:
			return self._child_groups[key]
		else:
			return self._children[key]

	def __delitem__(self, key):
		if type(key) == int:
			child = self._children[key]
			del self._children[key]
			self._child_groups[child._tag_name].remove(child)
		elif type(key) == JXITag:
			self._child_groups[key._tag_name].remove(key)
			
			self._children.remove(key)
		elif type(key) == str:
			for child in self._child_groups[key]:
				self._children.remove(child)
			del self._child_groups[key]
		else:
			raise IndexError("Deletion key must have type in {str, int, JXITag}")
			
	def __len__(self):
		return len(self._children)

	def _encode(self, buffer=None, options={}):
		global seen_objects_stack
		if not buffer: return self.__str__(options)
		seen_objects_stack = []
		# OPTIONS
		# attributes all on one line
		# attributes on multiple lines
		# lists all on one line
		# lists on multiple lines
		# same for dicts and children
		indent = options.get("indent", "tab")
		list_commas = options.get("list_commas", False)
		dict_commas = options.get("dict_commas", False)
		options = {
			"attributes": options.get("attributes", "inline"),
			"lists": options.get("lists", "inline"),
			
			"dicts": options.get("dicts", "inline"),
			
			"children": options.get("children", "block")
		}
		if type(indent) == int and indent >= 0:
			indent = indent * " "
		else:
			indent = "\t"
		self.__encode(buffer, options, indent)


	def __encode(self, buffer, options, indent, depth=0):
		if self in seen_objects_stack:
			raise JXIEncodeError("Circular dependency detected.")

		seen_objects_stack.append(self)

		buffer.write("<%s" % (getattr(self, "_tag_name", "")))

		for attribute in [a for a in dir(self) if not a.startswith("_")]:
			buffer.write(" " + attribute + "=")
			_encode_item(getattr(self, attribute), buffer)

		if len(self) == 0:
			buffer.write("/>\n")
		else:
			buffer.write(">\n")
			for child in self._children:
				child.__encode(buffer, options, indent, depth + 1)
			buffer.write("</%s>\n" % getattr(self, "_tag_name", ""))
		assert seen_objects_stack.pop() == self, "encode stack pop mismatch"


	def __str__(self, options={}):
		b = StringIO.StringIO()
		self._encode(b, options)
		c = b.getvalue()
		b.close()
		return c

class JXIEncodeError(Exception):
	pass

def _encode_item(obj, buffer, indent="", depth=0):
	if isinstance(obj, basestring):
		buffer.write('"')
		buffer.write(obj.replace("\\","\\\\").replace('"','\\"'))
		buffer.write('"')

	elif type(obj) == bool:
		if obj:
			buffer.write("true")
		else:
			buffer.write("false")

	elif isinstance(obj, (int, float, long)): 
		buffer.write(str(obj))

	elif obj == None:
		buffer.write("null")

	elif isinstance(obj, list):
		if len(obj) == 0: buffer.write("[]")
		else:
			# iterate over list and recurse
			buffer.write("[")
			_encode_item(obj[0], buffer)
			for item in obj[1:]:
				buffer.write(", ")
				_encode_item(item, buffer)
			buffer.write("]")

	elif isinstance(obj, dict):
		# iterate over key, val pairs and recurse
		buffer.write("{")
		pairs = obj.items()
		for i in range(len(pairs)):
			k, v = pairs[i]
			# don't put quotes around legal names
			if isinstance(k, basestring) and re.match(r'([a-zA-Z]\w+|\d+)', str(k)):
				buffer.write(k)
			else:
				_encode_item(k, buffer)
			buffer.write(": ")
			_encode_item(v, buffer)
			if i < len(pairs) - 1:
				buffer.write(", ")
		buffer.write("}")
	else:
		return _encode_item(str(obj))

##########################
##### parsing stuffs #####
##########################

class JXIParseError(Exception):
	def __init__(self, msg):
		self.msg = "stopped on line %s: %s" % (_lexer.line, msg)
	def __str__(self):
		return self.msg

_lexer = None
_token = None

def _parse(text, cls=JXITag):
	"""parses some given text, converting to jxi objects"""
	global _lexer
	_lexer = _Lexer(text)
	_next() # setup lookahead
	_recognise("sym", "<")
	return _tag(cls)

# retrieves the next token from the lexer
def _next():
	global _token
	_token = _lexer.get_next_token()
	

def _token_is(type, sym):
	return _token == (type, sym)

# recognises a symbol and moves on
def _recognise(type, sym):
	if _token_is(type, sym):
		_next()
	else:
		raise JXIParseError("expecting '%s', got '%s'" % (sym, _token[1]))

def _tokentype(type):
	return _token[0] == type

def _tag(cls):
	attrs = {}
	children = []
	name = _name()
	# get attributes
	while _tokentype("name"):
		attrname = _token[1]
		_next()
		_recognise("sym", "=")
		attrs[attrname] = _attribute()

	# check whether childless tag
	if _token_is("sym", "/"):
		_next()
		_recognise("sym", ">")
	else:
		# get children
		_recognise("sym", ">")
		_recognise("sym", "<")
		while (_tokentype("name")):
			children.append(_tag(cls))
			_recognise("sym", "<")
		_recognise("sym", "/")
		_recognise("name", name)
		_recognise("sym", ">")
	return cls(name, attrs, children)

def _name():
	if not _tokentype("name"):
		raise JXIParseError("expecting tag name, got '%s'" % str(_token))
	name = _token[1]
	_next()
	return name

def _attribute():
	if _token[0] in ("int", "float", "str", "bool", "null"):
		val = _token[1]
		_next()
		return val
	elif _token_is("sym","["):
		return _list()
	elif _token_is("sym","{"):
		return _dict()
	else:
		raise JXIParseError("expecting attribute literal, got '%s'" % _token[1])

def _list():
	thelist = []
	_recognise("sym","[")
	if not _token_is("sym", "]"):
		thelist.append(_attribute())
		while not _token_is("sym", "]") and _token[0] != "EOF":
			if _token_is("sym", ","): _next()
			thelist.append(_attribute())
			if _token_is("sym", ","): _next()
	_recognise("sym", "]")
	return thelist

def _dict():
	thedict = {}
	_recognise("sym","{")
	if not _token_is("sym", "}"):
		if _token[0] in ("str", "int"):
			name = _token[1]
			_next()
		else:
			name = _name()
		_recognise("sym", ":")
		thedict[name] = _attribute()
		while not _token_is("sym", "}") and _token[0] != "EOF":
			if _token_is("sym", ","): _next()
			if _token[0] in ("str", "int"):
				name = _token[1]
				_next()
			else:
				name = _name()
			_recognise("sym", ":")
			thedict[name] = _attribute()
			if _token_is("sym", ","): _next()
	_recognise("sym","}")
	return thedict




