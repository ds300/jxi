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
