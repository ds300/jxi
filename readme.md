jxi
===

Officially pronounced "jay-ex-eye" (personally I like "jack-see"), the acronym JXI stands for 'Some Kind of Funky **(J)**SON/**(X)**ML Hybrid/Mashup Data **(I)**nterchange Format Thing'.

jxi was originally designed to be a nice way to serialise readable data from python, but I think it could be useful for other languages too.

It is a superset of JSON, but not XML, and the gist of its raison d'être is this:

* JSON is much more difficult to read than XML when dealing with lots of different entity types.
* XML is hardcore awful for dealing with complex attribute types like lists and dictionaries.
* Because of the above, using XML can turn attributes into entities which is just weird and not fun to deal with when you want to do operations on your data.

Ok so here's the high level description of what jxi does to solve these problems; you take XML, disallow text inbetween tags (i.e. &lt;lol&gt;hahaha&lt;/lol&gt; is a no-no. The only thing that can go between tags is other tags), then you let arbitrary JSON expressions be attributes of the xml tags. Let's look at a quick example:

    <wizard beard="white" level=6 spells_learned=["invisibility", "fireball", "aura of erotic mystery"]>
    	<hat pointy=true angle_of_incline_degrees=7.23e1 />
    	<hat pointy=false occasion_suitability={
    		parties: "adequate",
    		"foraging for berries": "dismal",
    		funerals: "perfect"
    	} />
    </wizard>

The first thing to note is that commas are optional. I've only included them here so as not to scare away the timid. Whitespace is somewhat optional too, but that gets really freaky so I'll leave it to your imagination and recommend that you put spaces between things (actually I'll explain it later on).

One thing XML geniuses might pick up on is that there are underscores in the attribute names instead of dashes. Yes! This is because, in programming languages, dashes between two words tend to mean you want to subtract the value of the second one from the value of the first. The whole point of these attribute names is to map directly to variable names in a programming language, so they follow the standard variable name format (except that they can't start with an underscore for reasons which will become clear as we move on).

Here's the regex if you like that kind of thing:

            /[a-zA-Z][a-zA-Z0-9_]*/

Tag names follow the same syntax and, unlike JSON, dictionary keys can be unquoted if they follow it too.

Speaking of quotes, strings are delimited by either single or double quotes. Backslashes and whichever delimiter you're using have to be escaped with a backslash if you want them to form part of the string. Apart from that, strings can span multiple lines and contain any unicode character.

    <person firstName="John" lastName="Smith" age=25
    	address={
    		streetAddress:"21 2nd Street"
    		city:"New York"
    		state:"NY"
    		postalCode:"10021"
    	}
    	phoneNumbers=[
    		{ type:"home" number:"212 555-1234" }
    		{ type:"fax" number:"646 555-4567" }
    	]
    />