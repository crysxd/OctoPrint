# coding=utf-8
from __future__ import absolute_import, unicode_literals, print_function, \
	division

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol.reprap.commands import Command

import re
import string

class GcodeCommand(Command):

	pattern = staticmethod(lambda x: GcodeCommand.command_regex.match(x))

	command_regex = re.compile("^\s*((?P<GM>[GM](?P<number>\d+))(\\.(?P<subcode>\d+))?|(?P<T>T(?P<tool>\d+))|(?P<F>F(?P<feedrate>\d+)))")
	parameter_regex = re.compile("(?P<key>[A-Z])((?P<value>[-+]?[0-9]*\.?[0-9]+)(?!\d)|(\s|$))")

	possible_params = tuple(string.ascii_lowercase) + ("subcode", "param", "tool", "feedrate", "original")

	@staticmethod
	def from_line(line, **kwargs):
		if isinstance(line, GcodeCommand):
			return line

		tags = kwargs.get(b"tags")
		if tags is None:
			tags = set()

		type = kwargs.get(b"type")

		line = line.strip()
		code = ""

		args = dict(original=line, type=type, tags=tags)

		match = GcodeCommand.command_regex.match(line)

		if match is None:
			raise ValueError("{!r} is not a Gcode line".format(line))

		if match.group(b"GM"):
			code = match.group(b"GM")

			if match.group(b"subcode"):
				args[b"subcode"] = int(match.group(b"subcode"))

			if match.group(0) != line:
				rest = line[len(match.group(0)):]

				while True:
					matched_param = GcodeCommand.parameter_regex.search(rest)
					if not matched_param:
						break

					key = matched_param.group(b"key").lower()
					if matched_param.group(b"value"):
						value = matched_param.group(b"value")
						if "." in value:
							value = float(value)
						else:
							value = int(value)
					else:
						value = True
					args[key] = value
					rest = rest[:matched_param.start()] + rest[matched_param.end():]

				rest = rest.lstrip()
				if rest:
					args[b"param"] = rest

		elif match.group(b"T"):
			code = "T"
			args[b"tool"] = int(match.group(b"tool"))

		elif match.group(b"F"):
			code = "F"
			args[b"feedrate"] = int(match.group(b"feedrate"))

		return GcodeCommand(code, **args)

	def __init__(self, code, **kwargs):
		self.code = code

		self.subcode = kwargs.pop(b"subcode", None)
		self.tool = kwargs.pop(b"tool", None)
		self.feedrate = kwargs.pop(b"feedrate", None)
		self.param = kwargs.pop(b"param", None)
		self.original = kwargs.pop(b"original", None)

		if self.original is None:
			line = self._to_line()
		else:
			line = self.original

		type = kwargs.pop(b"type", None)
		tags = kwargs.pop(b"tags", None)

		self.args = kwargs

		super(GcodeCommand, self).__init__(line, type=type, tags=tags)

		self._repr = self._to_repr()

	def __getattr__(self, item):
		if len(item) == 1:
			return self.args.get(item, None)
		raise AttributeError("'GcodeCommand' object has no attribute '{}'".format(item))

	def __repr__(self):
		return self._repr

	def _to_line(self):
		attr = []
		for key in string.ascii_lowercase:
			value = getattr(self, key, None)
			if value is not None:
				if value is True:
					attr.append(key.upper())
				else:
					attr.append("{}{!r}".format(key.upper(), value))
		attribute_str = " ".join(attr)
		return "{}{}{}".format(self.code.upper(), " " + attribute_str if attribute_str else "",
		                       " " + self.param if self.param else "")

	def _to_repr(self):
		args = [k + "=" + repr(getattr(self, k)) for k in self.possible_params if getattr(self, k, None) is not None]
		return "GcodeCommand({!r},{},type={!r},tags={!r})".format(self.code,
		                                                          ",".join(args),
		                                                          self.type,
		                                                          self.tags)