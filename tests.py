# coding=utf-8
import unittest, random
from jxi import _Lexer, JXITag, parse, _symbols, JXIParseError

###########################
##### WHITE BOX TESTS #####
###########################



class TestLexer(unittest.TestCase):

	############################
	##### HELPER FUNCTIONS #####
	############################

	def token_comparison(self, inputs, expected):
		lex = _Lexer(" ".join(inputs))
		for t in expected:
			self.assertEqual(t, lex.get_next_token())
		self.assertEqual(("EOF","EOF"), lex.get_next_token())

	############################
	##### test valid stuff #####
	############################

	def test_integers(self):
		inputs = [str(random.randint(-500,500)) for i in range(100)]
		expected = [("int", int(val)) for val in inputs]
		self.token_comparison(inputs, expected)

	def test_floats(self):
		handmade = ["0.435", "12395932.0", "10e3", "5E0"]
		randoms = [str(random.random()*random.randint(-5000,5000)) for i in range(100)]
		for i in random.sample(range(100), 50): # give half of the randoms an exponent
			randoms[i] += random.choice(["e","E"]) + str(random.randint(-500,500))
		inputs = handmade + randoms
		expected = [("float", float(val)) for val in inputs]
		self.token_comparison(inputs, expected)

	def test_string_literals(self):
		handmade = [
			"blahd skls   kjflsk",
			"slkj<df>js'sldkf''sdfjss'''fsd",
			'sdk>fj<lsk  jdf"s  dfs"" Sdfsdfs"""sd',
			'sdfsk  d""df\'\'d ""SD"FS"',
			'•¢•¢ª¢ ˙∆¢∆¢˚∆∆ ˙©¬¬˚∂∫∂\'√ß""å√ \n "≈ç˚∆\n ∂\t\r\vππ“π“ π…æ«æ…«…ææ«∂æ«¬∆©∂4',
			"\\\'\"\a\b\f \n\r\t \v "
		]
		expected = [("str", val) for val in handmade]
		inputs = []
		for s in handmade:
			# use both double and single quotes
			if round(random.random()) == 0:
				inputs.append("'%s'" % s.replace("\\","\\\\").replace("'","\\'"))
			else:
				inputs.append('"%s"' % s.replace("\\","\\\\").replace('"','\\"'))

		self.token_comparison(inputs, expected)

	def test_names(self):
		inputs = ["banana", "Yanana", "g4_eas32T4_dkdk5", "e_sdg"]
		expected = [("name", val) for val in inputs]
		self.token_comparison(inputs, expected)

	def test_symbols(self):
		symbols = [s for s in _symbols]
		inputs = []
		expected = []
		for i in range(1000):
			inp = ""
			for i in range(random.randint(1,10)):
				c = random.choice(symbols)
				inp += c
				expected.append(("sym", c))
			inputs.append(inp)
		self.token_comparison(inputs, expected)

	##############################
	##### test invalid stuff #####
	##############################

	def test_illegals(self):
		inputs = [r"-", r"*", r"%", r"_", r"&÷\\", r"$€¢#", r"§ª+"]
		expected = []
		for s in inputs:
			expected.extend([("ill", c) for c in s])
		self.token_comparison(inputs, expected)



###########################
##### BLACK BOX TESTS #####
###########################

class TestParserOutput(unittest.TestCase):
	def setUp(self):
		
		text = """<tag_1 list=[2,3,4,5,56 -4,] str="some kind of
cool s\\"tring thing">
	<tag_2 dict={"_yoma 7&m a":["yes" 5 7 ]  5:"funtimes", hello:958e40, }>
		<tag_3 attr=3940e10/>
	</tag_2>
	<tag_2 banana = 'she\\'s on fire!' yes=true />
</tag_1>"""
		
		self.root = parse(text)
	def test_encode(self):

		alist = [2,3,4,5,56,-4]
		adict = {"_yoma 7&m a":["yes",5,7], 5:"funtimes", "hello":958e40}
		astr = "some kind of\ncool s\"tring thing"
		# check that values and data structures are what they should be

		self.assertEqual(self.root._tag_name, "tag_1")
		self.assertEqual(self.root.list, alist)
		self.assertEqual(self.root.str, astr)
		self.assertEqual(self.root["tag_2"][0].dict, adict)
		self.assertEqual(self.root["tag_2"][0]["tag_3"][0].attr, 3940e10)
		self.assertEqual(self.root["tag_2"][1].banana, "she's on fire!")
		self.assertEqual(self.root["tag_2"][1].yes, True)

		self.assertEqual(len(self.root), 2)
		self.assertEqual(len(self.root[0]), 1)
		self.assertEqual(len(self.root[0][0]), 0)

		

	def test_decode(self):
		self.root = parse(str(self.root))
		self.test_encode()
		self.test_adding_and_removing_stuff()

	def test_adding_and_removing_stuff(self):
		# check that stuff gets deleted properly
		del self.root["tag_2"][0][0] # delete tag_3
		self.assertEqual(len(self.root[0]), 0)
		del self.root["tag_2"]
		self.assertEqual(len(self.root), 0)

		with self.assertRaises(IndexError):
			del self.root[0]

		with self.assertRaises(KeyError):
			del self.root["tag_2"]

		# now try adding stuffs
		for i in range(10):
			self.root._add(parse("<item id=%d />" % i))

		# print self.root[0]._tag_name
		# check they're all there
		for i in range(10):
			self.assertEqual(self.root[i].id, i)
			self.assertEqual(self.root["item"][i].id, i)


		# add some in the middle or something.
		# do it backwards to check if the reordering thingy works
		for i in range(4, -1, -1):
			self.root._add(parse("<otheritem id=%d/>" % i), 5)

		# check that they're in the right place
		for i in range(5):
			self.assertEqual(self.root[i+5].id, i)
			self.assertEqual(self.root[i+5]._tag_name, "otheritem")
			self.assertEqual(self.root["otheritem"][i].id, i)
			
		# now do a weird one just to be sure
		self.root._add(parse("<otheritem weird=true />"), 8)
		self.assertTrue(self.root[8].weird)
		self.assertTrue(self.root["otheritem"][3].weird)






class TestParserErrors(unittest.TestCase):
	def test_bad_closing_tag(self):
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something">""")

		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something"><tag>""")

		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something"<tag>""")

	def test_unclosed_string(self):
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something'></tag>""")

		with self.assertRaises(JXIParseError):
			parse("""<tag arrt='something"></tag>""")

	def test_bad_attribute(self):
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt=something></tag>""")

		parse("""<tag arrt=[1,2,"hello",true]></tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt=[1,2,"hello",blah]></tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt=[1,2,"hello",-]></tag>""")

		parse("""<tag arrt={name:true, name2:false}></tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt={name:true, name2:blah}></tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt={name:true, name2:_}></tag>""")

	def test_bad_attribute_name(self):
		with self.assertRaises(JXIParseError):
			parse("""<tag _arrt="something"></tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag 4arrt="something"></tag>""")

	def test_bad_stuff_in_tag(self):
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something">s</tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something">#</tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something"><</tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something">4</tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something">"s"</tag>""")
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something">'yo'</tag>""")

	def test_mismatched_tags(self):
		with self.assertRaises(JXIParseError):
			parse("""<tag arrt="something"><tag></tag></targ>""")

		parse("""
    <person 
    	firstName="John"
    	lastName="Smith"
    	age=25
    	address={
    		streetAddress:"21 2nd Street"
    		city:"New York"
    		state:"NY"
    		postalCode:"10021"
    	}
    	phoneNumbers=[
    		{ type:"home" number:"212 555-1234" }
    		{ type:"fax"  number:"646 555-4567" }
    	]
    />
""")

if __name__ == "__main__":
	unittest.main()