# -*- coding: utf-8 -*-
# @Time: 2022/04/20 0:00
# @Author: Chloride
import re
from os import PathLike, path as _path
from typing import MutableMapping

from .types import Array, Bool

__all__ = ["INIClass", "CCINIClass",
           "INISectionClass",
           ]


class INISectionClass(MutableMapping):
    def __init__(self, section: str, _super=None, **kwargs):
        self.section = section
        self.parent = _super
        self._map = {}
        if kwargs:
            self.update(kwargs)

    def __setitem__(self, k, v):
        self._map[k] = (Bool.tostring(v)  # to be consistent with FA2.
                        if type(v) == bool
                        else str(v))

    def __delitem__(self, v):
        del self._map[v]

    def __getitem__(self, k):
        if k in self._map:
            return self.tryparse(k, self._map[k])
        elif (isinstance(self.parent, INISectionClass)
              and k in self.parent):
            return self.parent.tryparse(k, self.parent.get(k))
        else:
            raise KeyError(k)

    def __contains__(self, item):
        return item in self._map

    def __len__(self) -> int:
        return len(self._map)

    def __iter__(self):
        return iter(self._map)

    def __repr__(self):
        return f"Section {self.section}"

    def __str__(self):
        return self.section

    def tostring(self):
        _info = "[%s]" % self.section
        if self.parent:
            _info += ":[%s]" % self.parent
        return _info

    def get(self, key, default=None):
        if key in self._map:
            return self._map[key]
        elif (isinstance(self.parent, INISectionClass)
              and key in self.parent):
            return self.parent.get(key, default)
        else:
            return default

    def values(self, *, useraw=False):
        return self._map.values() if useraw else super().values()

    def items(self, *, useraw=False):
        return self._map.items() if useraw else super().items()

    def sortkeys(self, cond_expr=None):
        _items = sorted(self._map.keys(), key=cond_expr)
        _o_sect = {k: self._map[k] for k in _items}
        self._map = _o_sect

    def copydata(self, ienum_keyvalpair):
        if not isinstance(ienum_keyvalpair, MutableMapping):
            raise TypeError("ienum_keyvalpair")
        self._map = {str(k): str(v) for k, v in ienum_keyvalpair.items()}

    def copyfrom(self, inisection):
        if not isinstance(inisection, INISectionClass):
            raise TypeError("inisection")
        self.section = inisection.section
        self.parent = inisection.parent
        self._map = dict(inisection.items(useraw=True))

    def tryparse(self, option, fallback):
        try:
            value: str = self._map[option]
        except KeyError:
            return fallback

        if value.isdecimal():  # int
            return int(value)
        elif re.match(r"^-?\d+\.?\d+$", value):  # float
            return float(value)
        elif value.lower() in Bool.bool_like:  # bool
            return Bool.parse(value)
        elif value.lower() in ('none', '<none>'):  # NoneType
            return None
        elif re.findall(",+", value):  # Array
            return Array(i.strip() for i in re.split(",+", value))
        else:  # str itself
            return value


class INIClass:
    """C&C INI handler.

    Support the following features Ares implemented:

    - section inheritance: '[A]:[B]'
    - fast append: '+= C'
    - include sub inis: '[#include]' (NOT directly)

    """
    __diff = 0  # for multiple inis processing

    def __init__(self):
        """Initialize an empty INI structure."""
        self._raw: dict[str, INISectionClass] = {}

    def __getitem__(self, item):
        return self._raw[item]

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("Section name should always be str.")
        if isinstance(value, INISectionClass):
            self._raw[key].copyfrom(value)
        else:
            self._raw[key].copydata(value)

    def __delitem__(self, key):
        del self._raw[key]

    def __len__(self):
        return len(self._raw)

    def __iter__(self):
        return iter(self._raw)

    @property
    def sections(self):
        return list(self._raw.values())

    def hassection(self, section):
        return section in self._raw

    def hasoption(self, section, option):
        return section in self._raw and option in self._raw[section]

    def addnew(self, section):
        if not self.hassection(section):
            self._raw[section] = INISectionClass(section)

    def remove(self, section):
        if self.hassection(section):
            del self._raw[section]

    def rename(self, _old, _new):
        if self.hassection(_new) or _old == _new:
            raise KeyError(f'Section "{_new}" already exists!')
        self[_new] = self[_old]
        self[_new].section = _new
        del self._raw[_old]

    def getsection(self, section):
        return self._raw.get(section,
                             INISectionClass(section))

    def getvalue(self, section, key, fallback=None):
        return (self._raw[section][key]
                if self.hasoption(section, key) else fallback)

    def gettypelist(self, section, fallback=Array()):
        return (list(self._raw[section].values(useraw=True))
                if self.hassection(section) else fallback)

    def setvalue(self, section, key, value):
        self.addnew(section)
        self._raw[section][key] = value

    def clear(self):
        return self._raw.clear()

    def sort(self, cond_expr=None, *, reverse=False):
        _sects = sorted(self._raw.keys(), key=cond_expr, reverse=reverse)
        _o_raw = {k: self._raw[k] for k in _sects}
        self._raw = _o_raw

    def load(self, *ccinis, encoding='utf-8'):
        """
        Load C&C ini(s).

        Basically we recommend the recursive way to support [#include],
        instead of just 'os.walk' or blabla files collection.

        :param ccinis: INI file path(s), make sure the order of them.
        :param encoding: text encoding.
        """
        for ref in ccinis:
            try:
                with open(ref, 'r', encoding=encoding) as fp:
                    self.__fread(fp)
            except OSError:
                continue

    def save(self, dst: PathLike | str, encoding='utf-8',
             withspace=False, blankline=1):
        """
        Save as a C&C ini.

        :param dst: target ini path.
        :param encoding: text encoding.
        :param withspace: shall we use spaces around '='?
        :param blankline: how many lines between sections?
        """
        _eq = ' = ' if withspace else '='

        with open(dst, 'w', encoding=encoding) as fs:
            for i in self.sections:
                fs.write(f"{i.tostring()}\n")
                for key, value in i.items(useraw=True):
                    fs.write(f"{key}{_eq}{value}\n")
                fs.write("\n" * blankline)

    def __fread(self, stream):
        if not self._raw:
            sections, options = [], []
            curopt = maxopt = -1
        else:
            sections = list(self._raw.keys())
            options = list(self._raw.values())
            curopt = maxopt = len(options) - 1

        while True:
            i = stream.readline()
            if len(i) == 0:
                break
            if i[0] == '[':
                cursect = [j.strip()[1:-1] for j in
                           i.split(';')[0].split(':')]
                if cursect[0] in sections:
                    curopt = sections.index(cursect[0])
                else:
                    sections.append(cursect[0])
                    options.append(INISectionClass(cursect[0]))
                    maxopt += 1
                    curopt = maxopt
                # ares struct: [a]:[b]
                if len(cursect) > 1:
                    options[curopt].parent = (
                        options[sections.index(cursect[1])]
                        if cursect[1] in sections else cursect[1]
                    )
            elif '=' in i:
                j = i.split('=', 1)
                if ';' not in j[0]:
                    j[0] = j[0].strip()
                    j[1] = j[1].split(";")[0].strip()
                    # ares struct: += a
                    if j[0] == '+':
                        j[0] = f"+{self.__diff}"
                        self.__diff += 1
                    options[curopt].update([j])

        self._raw = dict(zip(sections, options))
        return len(sections), len(options)


class CCINIClass(INIClass):
    def __init__(self, ccini: PathLike | str, encoding='utf-8'):
        """
        Initialize with a given INI file.

        :param ccini: INI file path.
        :param encoding: text encoding.
        """
        # private props
        self.__full = _path.abspath(ccini)
        self.__codec = encoding

        if not _path.exists(ccini):
            raise FileNotFoundError(ccini)

        super().__init__()
        self.load(ccini, encoding=encoding)

    def save(self, dst=None, encoding=None, withspace=False, blankline=1):
        """
        Save as a C&C ini.

        :param dst: target path, overwrite the source by default
        :param encoding: by default using the encoding when initialize
        :param withspace: shall we use spaces around '='?
        :param blankline: how many lines between sections?
        """
        dst = self.__full if dst is None else dst
        encoding = self.__codec if encoding is None else encoding

        super().save(dst, encoding, withspace, blankline)

    def __repr__(self):
        return "%s: %s" % (self.__full, self.__codec)

    def __str__(self):
        return _path.split(self.__full)[-1]
