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

import re, StringIO

class RawString(str):
	pass

######################################################
##### Entity is the base object of the jxi world #####
######################################################

class Entity(object):
	"""Represents a tag in the tree"""
	def __init__(self, name="", attrs={}, children=[]):
		self._children = children
		self._tag_name = name
		self._parent = None

		# assign attributes
		for key, val in attrs.items():
			object.__setattr__(self, key, val)

	def _append(self, elem):
		self._children.append(elem)

	def _extend(self, elems):
		self._children.extend(elems)

	def _insert(self, i, elem):
		self._children.insert(i, elem)

	def _remove(self, elem):
		self._children.remove(elem)

	def _pop(self, i):
		return self._children.pop(i)

	def _count(self, elem):
		return self._children.count(elem)

	def _index(self, elem):
		return self._children.index(elem)

	def _sort(self):
		self._children.sort()

	def _reverse(self):
		self._children.reverse()

	def _attrs(self):
		return [attr for attr in dir(self) if not attr.startswith("_")]

	def __getitem__(self, key):
		if isinstance(key, basestring):
			# search by tag name
			if key.startswith("."):
				# find all matches
				key = key[1:]
				if not re.match(r'^[a-zA-Z]\w+$', key):
					raise KeyError("'%s' is not a valid tag name" % key)
				elems = []
				for elem in self:
					if type(elem) == type(self) and elem._tag_name == key:
						elems.append(elem)
				return elems
			else:
				# find first match
				if not re.match(r'^[a-zA-Z]\w+$', key):
					raise KeyError("'%s' is not a valid tag name" % key)
				for elem in self:
					if type(elem) == type(self) and elem._tag_name == key:
						return elem
				raise KeyError("No tag with name '%s'" % key)
		else:
			return self._children[key]

	def __delitem__(self, key):
		if isinstance(key, basestring):
			# search by tag name
			if key.startswith("."):
				# find all matches
				key = key[1:]
				if not re.match(r'^[a-zA-Z]\w+$', key):
					raise KeyError("'%s' is not a valid tag name" % key)
				elems_to_remove = []
				for elem in self:
					if type(elem) == type(self) and elem._tag_name == key:
						elems_to_remove.append(elem)
				for elem in elems_to_remove:
					self._children.remove(elem)
			else:
				# find first match
				if not re.match(r'^[a-zA-Z]\w+$', key):
					raise KeyError("'%s' is not a valid tag name" % key)
				for elem in self:
					if type(elem) == type(self) and elem._tag_name == key:
						self._children.remove(elem)
						return
				raise KeyError("No tag with name '%s'" % key)
		else:
			del self._children[key]

	def __len__(self):
		return len(self._children)

	def __lt__(self, other):
		return type(other) != type(self) or self._tag_name < other._tag_name

	def __gt__(self, other):
		if type(other) == type(self):
			return self._tag_name > other._tag_name
		else:
			return false

	def __eq__(self, other):
		return type(other) == type(self) and self._tag_name == other._tag_name

	def __le__(self, other):
		return type(other) != type(self) or self._tag_name <= other._tag_name

	def __ge__(self, other):
		if type(other) == type(self):
			return self._tag_name >= other._tag_name
		else:
			return false

	def __ne__(self, other):
		return type(other) != type(self) or self._tag_name != other._tag_name

	def __str__(self):
		return dumps(self)


######################
### ENCODING STUFF ###
######################

class ObjectVisitor(object):
	def visit(self, obj, depth):
		# copy current object stack
		if obj in seen_objects:
			out.write(make_link(seen_objects[obj]))
		else:
			seen_objects[obj] = [o for o in object_stack]
			object_stack.append(obj)
			self.encode(obj, depth) # implemented in subclasses
			assert object_stack.pop() == obj


element_encoders = {
	list: None,
	dict: None,
	str: None,
	unicode: None,
	Entity: None,
	int: None,
	float: None,
	RawString: None
}

dict_separator = ":"
separator = " "
seen_objects = dict()
object_stack = []
out = None
string_keys=False
string_escapes= {
	'\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t'
}

def dumps(elem, buffer=None, 
		use_commas=False,
		dynamic=False,
		width=80,
		skip_keys=False,
		string_keys=False,
		separators=None
		):
	global seen_objects, out, separator, dict_separator

	seen_objects = dict()
	out = buffer or StringIO.StringIO()

	separator, dict_separator = separators or (" ",":")

	element_encoders[str] = EncodeJsonString()
	element_encoders[list] = EncodeListFlat()
	element_encoders[float] = element_encoders[int] = element_encoders[long] = EncodeNumber()
	element_encoders[dict] = EncodeDictFlat()
	element_encoders[RawString] = EncodeRawString() 
	if type(elem) == list:
		for e in elem:
			encode_element(e, 0)
			out.write("\n")
	else:
		encode_element(elem, 0)
	if not buffer:
		c = out.getvalue()
		out.close()
		return c

def encode_element(elem, depth):
	if type(elem) in element_encoders:
		element_encoders[type(elem)].visit(elem, depth)

class EncodeListFlat(ObjectVisitor):
	def encode(self, ls, depth):
		out.write("[")
		for item in ls[:-1]:
			encode_element(item, depth+1)
			out.write(separator)
		for item in ls[-1:]:
			encode_element(item, depth+1)
		out.write("]")

class EncodeSetFlat(object):
	def encode(self, s, depth):
		out.write("(")
		items = [e for e in s]
		for item in items[:-1]:
			encode_element(item, depth+1)
			out.write(separator)
		for item in items[-1:]:
			encode_element(item, depth+1)
		out.write(")")

class EncodeDictFlat(ObjectVisitor):
	def encode(self, d, depth, string_keys=string_keys):
		out.write("{")
		items = d.items()
		def write(k,v):
			if isinstance(k, basestring):
				if not string_keys and re.match(r"[a-zA-Z]\w+", k):
					out.write(k)
				else:
					encode_element(k, depth)
			out.write(dict_separator)
			encode_element(v, depth+1)
		for k, v in items[:-1]:
			write(k,v)
			out.write(separator)
		for k, v in items[-1:]:
			write(k,v)
		out.write("}")

class EncodeRawString(ObjectVisitor):
	def encode(self, string, depth):
		out.write("`")
		out.write(string.replace("`", "\\`"))
		out.write("`")

class EncodeJsonString(object):
	def encode(self, string, depth, string_escapes=string_escapes):
		out.write('"')
		for c in string:
			out.write(string_escapes.get(c, c))
		out.write('"')

class EncodeNumber(object):
	def encode(self, num, depth):
		if num in (float("inf"), float("-inf"), float("nan")):
			raise ValueError("cannot encode '%s'" % num)
		else:
			out.write(str(num))

print dumps({"thing":[1,2,3,4,5e26,6,"hekkis"]}, separators=(", ",": "))

