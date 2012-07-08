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

#############################################################
##### JXITag is the base entity object of the jxi world #####
#############################################################

class JXITag(object):
	"""Represents a tag in the tree"""
	def __init__(self, name="", attrs={}, children=[]):
		self._children = children
		self._tag_name = name

		# assign attributes
		for key, val in attrs.items():
			object.__setattr__(self, key, val)

	def _add(self, tag, position=None):
		if type(tag) == JXITag:
			if position == None:
				self._children.append(tag)
			else:
				self._children[position:position] = [tag]
		else:
			raise TypeError("a jxi tag's children must be other jxi tags")

	def _remove(self, tag):
		if type(tag) == int:
			del self[tag]
		elif type(tag) == JXITag:
			del self[_children.index(tag)]
		else:
			raise KeyError("invalid key type")

	def __getitem__(self, key):
		return self._children[key]

	def __delitem__(self, key):
		if type(key) == int:
			child = self._children[key]
			del self._children[key]
		elif type(key) == JXITag:
			self._children.remove(key)
		else:
			raise IndexError("Deletion key must have type in {str, int, JXITag}")

	def __len__(self):
		return len(self._children)
