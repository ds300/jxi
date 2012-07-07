# Copyright (C) 2012 David Sheldrick

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from jxitag import JXITag
from lex import lex, JXIParseError, line

class SymbolicLink(object):
	"""an absolute path to some element or attribute in the document"""
	def __init__(self, args):
		self.args = args
		self.line = line

class LinkEvaluator(object):
	def __init__(self, link):
		self.link = link

	def find_target(self, document):
		args = self.link.args
		target = document
		i = 0
		while i < len(args):
			operator, operand = args[i]
			print operator, operand
			if operator == ">":
				if type(target) not in (list, tagclass):
					msg = "Link not found. Unable to find tag name '%s'. Parent cannot contain tags." % operand
					raise JXIParseError(msg, self.link.line)
				tagname = operand
				# search for a specific tag
				if i < len(args) and args[i+1][0] == "[":
					# search by group index
					i += 1
					target_index = args[i][1]
					if type(target_index) != int:
						msg = "Link not found. Tag indices in symbolic links must be integers!"
						raise JXIParseError(msg, self.link.line)

					count = -1
					for elem in target:
						if type(elem) == tagclass and elem._tag_name == tagname:
							count += 1
							if count == target_index:
								target = elem
								break
					if count != target_index:
						msg = "Link not found. No tag with name '%s' and group index '%s'" % (tagname,target_index)
						raise JXIParseError(msg, self.link.line)
				else:
					# just fine the first element with that tag name
					for elem in target:
						if type(elem) == tagclass and elem._tag_name == tagname:
							target = elem
							break

			elif operator == ".":
				if type(target) != tagclass:
					msg = "Link not found. Non-tag element cannot have attribute '%s'" % operand
				elif not hasattr(target, operand):
					msg = "Link not found. No attribute '%s'" % operand
					raise JXIParseError(msg, self.link.line)

				target = getattr(target, operand)

			elif operator == "[":
				if type(target) in (list, tagclass):
					# ensure operand is an int
					if not type(operand) == int:
						msg = "Link not found. Lists and tags must be indexed by integers"
						raise JXIParseError(msg, self.link.line)
					elif operand < 0 or operand >= len(target):
						msg = "Link not found. Invalid index '%s'" % operand
						raise JXIParseError(msg, self.link.line)
				elif type(target) == dict:
					if operand not in target:
						msg = "Link not found. Invalid index '%s'" % operand
						raise JXIParseError(msg, self.link.line)
				else:
					msg = "Link not found. Invalid index '%s'. Parent unsubscriptable." % operand
					raise JXIParseError(msg, self.link.line)

				target = target[operand]

			i += 1

		return target


	def remove(self):
		scheduled_links.remove(self)

	def delay(self):
		self.remove()
		scheduled_links.append(self)

class ListLinkEvaluator(LinkEvaluator):
	def __init__(self, link, listobj, index):
		LinkEvaluator.__init__(self, link)
		self.listobj = listobj
		self.index = index

	def evaluate(self, document):
		target = self.find_target(document)
		if type(target) == SymbolicLink:
			self.delay()
		else:
			self.listobj[self.index] = target
			self.remove()
		

class TagLinkEvaluator(LinkEvaluator):
	def __init__ (self, link, obj, attr):
		LinkEvaluator.__init__(self, link)
		self.obj = obj
		self.attr = attr

	def evaluate(self, document):
		target = self.find_target(document)
		if type(target) == SymbolicLink:
			self.delay()
		else:
			setattr(self.obj, attr, target)
			self.remove()


class SetLinkEvaluator(LinkEvaluator):
	def __init__ (self, link, setobj):
		LinkEvaluator.__init__(self, link)
		self.setobj = setobj

	def evaluate(self, document):
		target = self.find_target(document)
		if type(target) == SymbolicLink:
			self.delay()
		else:
			self.setobj.remove(self.link)
			self.setobj.add(target)
			self.remove()

class DictLinkEvaluator(LinkEvaluator):
	def __init__ (self, link, dictobj, key):
		LinkEvaluator.__init__(self, link)
		self.dictobj = dictobj
		self.key = key

	def evaluate(self, document):
		target = self.find_target(document)
		if type(target) == SymbolicLink:
			self.delay()
		else:
			self.dictobj[self.key] = target
			self.remove()


scheduled_links = []

token = None
lexer = None
tagclass = JXITag

# retrieves the next token from the lexer
def next():
	global token
	token = lexer.next()
	print token


# recognises a symbol and moves on
def recognise(type, sym):
	if token == (type, sym):
		next()
	else:
		raise JXIParseError("expecting '%s', got '%s'" % (sym, token[1]))

def parse(text, tagclass=JXITag):
	"""
	parse will parse you some JXI and return a list of all the top-level elements
	in the given text.
	"""
	global lexer, scheduled_links
	scheduled_links = []
	lexer = lex(text)
	next()
	result = parse_file()
	safety_counter = (len(scheduled_links)**2)/2 + 1
	while len(scheduled_links) > 0 and safety_counter > 0:
		print "doing it"
		scheduled_links[0].evaluate(result)
		safety_counter -= 1
	return result

def parse_file():
	elems = []
	while not token[0] == "EOF":
		elem = parse_element()
		elems.append(elem)
		if type(elem) == SymbolicLink:
			scheduled_links.append(ListLinkEvaluator(elem, elems, len(elems)-1))
	return elems

def parse_element():
	if token == ("sym", "<"):
		next()
		return parse_tag()
	else:
		return parse_attribute()

def parse_tag():
	attrs = {}
	children = []

	# require tag name
	if not token[0] == "ident":
		raise JXIParseError("expecting tag name, got '%s'" % str(token))

	name = token[1]
	next()
	# optional value for tag name
	if token == ("sym", "="):
		next()
		attrs[name] = parse_element()

	# get proper attributes
	while token[0] == "ident":
		attrname = token[1]
		next()
		recognise("sym", "=")
		attrs[attrname] = parse_element()

	# check whether childless tag
	if token == ("sym", "/"):
		next()
		recognise("sym", ">")
	else:
		# if not, get children
		recognise("sym", ">")

		while True:
			if token == ("sym", "<"):
				next()
				if token == ("sym", "/"):
					break
				else:
					children.append(parse_tag())
			else:
				elem = parse_attribute()
				children.append(elem)
				if type(elem) == SymbolicLink:
					scheduled_links.append(ListLinkEvaluator(elem, children, len(children)-1))

		recognise("sym", "/")
		recognise("ident", name)
		recognise("sym", ">")

	return tagclass(name, attrs, children)


def parse_attribute():
	if token[0] in ("int", "float", "string", "rawstring", "bool", "null"):
		val = token[1]
		next()
		return val
	elif token == ("sym","["):
		return parse_list()
	elif token == ("sym","{"):
		return parse_dict()
	elif token == ("sym", "("):
		return parse_set()
	elif token == ("sym", "@"):
		return parse_link()
	else:
		raise JXIParseError("expecting attribute literal, got '%s'" % token[1])

def parse_list():
	thelist = []
	recognise("sym","[")
	while token != ("sym", "]"):
		elem = parse_element()
		thelist.append(elem)
		if type(elem) == SymbolicLink:
			scheduled_links.append(ListLinkEvaluator(elem, thelist, len(thelist)-1))
	recognise("sym", "]")
	return thelist

def parse_dict():
	thedict = {}
	recognise("sym","{")
	while token != ("sym", "}"):
		if token[0] in ("string", "rawstring", "int", "ident"):
			name = token[1]
			next()
			recognise("sym", ":")
			elem = parse_element()
			thedict[name] = elem
			if type(elem) == SymbolicLink:
				scheduled_links.append(DictLinkEvaluator(elem, thedict, name))
		else:
			raise JXIParseError("expecting attribute literal")
	recognise("sym","}")
	return thedict

def parse_set():
	theset = set()
	recognise("sym", "(")
	while token != ("sym", ")"):
		elem = parse_element()
		theset.add(elem)
		if type(elem) == SymbolicLink:
			scheduled_links.append(SetLinkEvaluator(elem, theset))
	recognise("sym", "(")

def parse_link():
	recognise("sym", "@")

	if token[0] != "sym" or token[1] not in (">", "["):
		raise JXIParseError("Bad symbolic link syntax. Expecting ':' or index")

	link = []

	while token[0] == "sym" and token[1] in (">", ".", "["):
		if token[1] == ">":
			# tag name
			next()
			if token[0] != "ident": 
				raise JXIParseError("'>' should be followed by a tag name")
			link.append((">", token[1]))
			next()

		elif token[1] == ".":
			# tag attribute
			next()
			if token[0] != "ident": 
				raise JXIParseError("'.' should be followed by an attribute name")
			link.append((".", token[1]))
			next()

		elif token[1] == "[":
			# index of something
			next()
			if token[0] not in ("ident", "int", "string", "rawstring"): 
				raise JXIParseError("'.' should be followed by an attribute name")
			link.append(("[", token[1]))
			next()
			recognise("sym", "]")

	recognise("sym", ";")

	return SymbolicLink(link)


print parse("""

<steve time=6 />
<steve banana={hello:true, death:"ohyesindeed"} />
@>steve.time;
@[0].time;
@>steve[1].banana[death];

""")



