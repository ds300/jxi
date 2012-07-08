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
import lex


######################
##### LINK STUFF #####
######################

class SymbolicLink(object):
	"""an absolute path to some element or attribute in the document"""
	def __init__(self, args, line):
		self.args = args
		self.line = line

class LinkEvaluator(object):
	"""
	Abstract class. Finds the target of a symbolic link. If the target is another
	symbolic link, pushes itself to the end of the link evaluation queue. If no 
	target is found, a JXIParseError is raised.
	"""
	def __init__(self, link):
		self.link = link

	# iterates over the link argumemts to find the target. 
	def find_target(self, document):
		args = self.link.args
		target = document
		i = 0
		while i < len(args):
			operator, operand = args[i]

			### TAG NAME & POSSIBLE INDEX ###
			if operator == ">":
				# tag names are only considered for list-like elements
				if type(target) not in (list, tagclass):
					msg = "Link not found. Unable to find tag name '%s'. Parent cannot contain tags." % operand
					raise lex.JXIParseError(msg, lineoverride=self.link.line)
				
				tagname = operand

				# check if we've been given an index
				if i < len(args) and args[i+1][0] == "[":
					# search by group index
					i += 1
					target_index = args[i][1]

					# tags can only be indexed by integers
					if type(target_index) != int:
						msg = "Link not found. Tag indices in symbolic links must be integers!"
						raise lex.JXIParseError(msg, lineoverride=self.link.line)

					count = -1 # we use this to match against the target index

					# iterate over elements in current target
					for elem in target:
						# only consider eliments with the specified tag name
						if type(elem) == tagclass and elem._tag_name == tagname:
							count += 1
							if count == target_index:
								target = elem
								break

					if count != target_index:
						msg = "Link not found. No tag with name '%s' and group index '%s'" % (tagname,target_index)
						raise lex.JXIParseError(msg, lineoverride=self.link.line)

				else:
					# just fine the first element with that tag name
					for elem in target:
						if type(elem) == tagclass and elem._tag_name == tagname:
							target = elem
							break

			### TAG ATTRIBUTE ###
			elif operator == ".":
				if type(target) != tagclass:
					msg = "Link not found. Non-tag element cannot have attribute '%s'" % operand
				elif not hasattr(target, operand):
					msg = "Link not found. No attribute '%s'" % operand
					raise lex.JXIParseError(msg, lineoverride=self.link.line)

				target = getattr(target, operand)

			### INDEX OF SOME KIND ###
			elif operator == "[":
				# lists and tags can only be indexed by integers
				if type(target) in (list, tagclass):
					# ensure int
					if not type(operand) == int:
						msg = "Link not found. Lists and tags must be indexed by integers"
						raise lex.JXIParseError(msg, lineoverride=self.link.line)
					# ensure valid index
					elif operand < 0 or operand >= len(target):
						msg = "Link not found. Invalid index '%s'" % operand
						raise lex.JXIParseError(msg, lineoverride=self.link.line)

				# only other indexable type is dict
				elif type(target) == dict:
					# just check that the key exists (can be int, string, ident)
					if operand not in target:
						msg = "Link not found. Invalid index '%s'" % operand
						raise lex.JXIParseError(msg, lineoverride=self.link.line)
				else:
					msg = "Link not found. Invalid index '%s'. Parent unsubscriptable." % operand
					raise lex.JXIParseError(msg, lineoverride=self.link.line)

				target = target[operand]

			i += 1

		return target

	# find target and decide whether to delay or finish and delegate to subclass
	def evaluate(self, document):
		target = self.find_target(document)
		if type(target) == SymbolicLink:
			self.delay()
		else:
			self.remove()
			self.set_target(target) # implemented in sub-classes

	def remove(self):
		scheduled_links.remove(self)

	def delay(self):
		self.remove()
		scheduled_links.append(self)

# evaluate a link which was declared in a list-like element
class ListLinkEvaluator(LinkEvaluator):
	def __init__(self, link, listobj, index):
		LinkEvaluator.__init__(self, link)
		self.listobj = listobj
		self.index = index

	def set_target(self, target):
		self.listobj[self.index] = target

# evaluate a link which was declared as a tag attribute
class TagLinkEvaluator(LinkEvaluator):
	def __init__ (self, link, obj, attr):
		LinkEvaluator.__init__(self, link)
		self.obj = obj
		self.attr = attr

	def set_target(self, target):
		setattr(self.obj, self.attr, target)

# evaluate a link which was declared in a set literal
class SetLinkEvaluator(LinkEvaluator):
	def __init__ (self, link, setobj):
		LinkEvaluator.__init__(self, link)
		self.setobj = setobj

	def set_target(self, target):
		self.setobj.remove(self.link)
		self.setobj.add(target)

# evaluate a link which was declared in a dict literal
class DictLinkEvaluator(LinkEvaluator):
	def __init__ (self, link, dictobj, key):
		LinkEvaluator.__init__(self, link)
		self.dictobj = dictobj
		self.key = key

	def set_target(self, target):
		self.dictobj[self.key] = target


# the link evaluation queue
scheduled_links = []


######################################
### RECURSIVE DESCENT PARSING BITS ###
######################################

# this is the only publicly visible function
def parse(text, tagclass=JXITag):
	"""
this function will parse you some jxi and return a list of all the top-level elements
in the given text.
Synatx: 
	parse(text [, tagclass=JXITag])
text is some string of (hopefully legal) jxi markup
tagclass can be used if you've implemented you own tag class or extended JXITag"""
	global lexer, scheduled_links
	scheduled_links = []
	lexer = lex.lex(text)
	next()
	result = parse_file()

	# in the worst case, only one link gets evaluated per iteration, so we
	# have n*(n+1)/2 possible evaluations. set safety counter to (n*(n+1)/2) + 1
	# so that we can tell for definites if an infinite loop has been encountered
	safety_counter = (len(scheduled_links)*(len(scheduled_links) + 1))//2 + 1
	while len(scheduled_links) > 0 and safety_counter > 0:
		scheduled_links[0].evaluate(result)
		safety_counter -= 1

	if safety_counter == 0:
		msg = "Infinite symbolic link cycle detected. What is this i don't even"
		raise lex.JXIParseError(msg, lineoverride=scheduled_links[0].link.line)

	return result


token = None
lexer = None
tagclass = JXITag

# retrieves the next token from the lexer
def next():
	global token
	token = lexer.next()

# recognises a symbol and moves on. Raises an error if the args don't match
# the token
def recognise(type, sym):
	if token == (type, sym):
		next()
	else:
		raise lex.JXIParseError("expecting '%s', got '%s'" % (sym, token[1]))


# used at the top level of the document
def parse_file():
	elems = []
	while not token[0] == "EOF":
		elem = parse_element()
		elems.append(elem)
		if type(elem) == SymbolicLink:
			scheduled_links.append(ListLinkEvaluator(elem, elems, len(elems)-1))
	return elems

# parses a tag or an attribute
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
		raise lex.JXIParseError("expecting tag name, got '%s'" % str(token))

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
		raise lex.JXIParseError("expecting attribute literal, got '%s'" % token[1])

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
			raise lex.JXIParseError("expecting attribute literal")
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
	line = lex.line

	if token[0] != "sym" or token[1] not in (">", "["):
		raise lex.JXIParseError("Bad symbolic link syntax. Expecting ':' or index")

	link = []

	while token[0] == "sym" and token[1] in (">", ".", "["):
		if token[1] == ">":
			# tag name
			next()
			if token[0] != "ident": 
				raise lex.JXIParseError("'>' should be followed by a tag name")
			link.append((">", token[1]))
			next()

		elif token[1] == ".":
			# tag attribute
			next()
			if token[0] != "ident": 
				raise lex.JXIParseError("'.' should be followed by an attribute name")
			link.append((".", token[1]))
			next()

		elif token[1] == "[":
			# index of something
			next()
			if token[0] not in ("ident", "int", "string", "rawstring"): 
				raise lex.JXIParseError("'.' should be followed by an attribute name")
			link.append(("[", token[1]))
			next()
			recognise("sym", "]")

	recognise("sym", ";")

	return SymbolicLink(link, line)
