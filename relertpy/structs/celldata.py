# -*- coding: utf-8 -*-
# @Time: 2022/04/25 20:01
# @Author: Chloride
"""
Cell data could be anything on that cell. Basically,
there could be these following items on a cell:

- Waypoint
- Terrain object
- CellTag
- Smudge
- Tile (won't parse)
- Overlay (won't parse)
- Object instance(s) (Infantries, Units, etc.)

WPs, Terrains, CellTags are all recorded as a tuple:
one is Coord, the other is celldata, which isn't ordered.

The remaining items are expressed as a list of instances,
with a useless numbering (gamemd uses array index actually)
as key, and an Array-like string as value.
"""
import abc
from ..types import Array, Coord


class Waypoint(Array):
    __CHARS = list(map(lambda x: chr(x), range(ord('A'), ord('Z') + 1)))

    def __init__(self, kv: tuple):
        self.pid = int(kv[0])
        super().__init__(Coord.split(kv[1]))

    @staticmethod
    def tostring(num):
        ret = []
        if num > 25:
            while True:
                d = int(num / 26)
                remainder = num % 26
                if d <= 26:
                    ret.insert(0, Waypoint.__CHARS[remainder])
                    ret.insert(0, Waypoint.__CHARS[d - 1])
                    break
                else:
                    ret.insert(0, Waypoint.__CHARS[remainder])
                    num = d - 1
        else:
            ret.append(Waypoint.__CHARS[num])
        return "".join(ret)

    @staticmethod
    def toint(wp: str):
        length = len(wp)
        ret = 0
        if length > 1:
            for i in range(length - 1):
                index = Waypoint.__CHARS.index(wp[i])
                # print(index)
                num = pow(26, length - 1) * (index + 1)
                # print(num)
                length -= 1
                ret += num
            ret += Waypoint.__CHARS.index(wp[-1])
        else:
            ret += Waypoint.__CHARS.index(wp[-1])
        return ret

    def apply(self):
        return str(self.pid), Coord.join(self)

    def __repr__(self) -> str:
        return f'WP {self.pid}: {tuple(self)}'


class Terrain(Array):
    def __init__(self, kv: tuple):
        self.terrain = kv[1]
        super().__init__(Coord.split(kv[0]))

    def apply(self):
        return Coord.join(self), self.terrain

    def __repr__(self) -> str:
        return f'Terrain {self.terrain}: {tuple(self)}'


class CellTag(Array):
    def __init__(self, kv: tuple):
        super().__init__(Coord.split(kv[0]))
        self.tagof = kv[1]

    def apply(self):
        return Coord.join(self), self.tagof

    def __repr__(self) -> str:
        return f'Tag {self.tagof}: {tuple(self)}'


class Smudge:
    def __init__(self, args: str | Array):
        if type(args) == str:
            args = args.split(',')
        self.typeof = args[0]
        self.coord = Array(map(int, args[1:3]))
        self.ignored = args[3] == '1'

    def apply(self):
        return ",".join(
            map(str,
                [self.typeof, self.coord, int(self.ignored)])
        )

    def __repr__(self) -> str:
        return f'{self.typeof} TopCell({self.coord})'


class FootClass(metaclass=abc.ABCMeta):
    owner = 'Neutral House'
    typeof = ""
    health = 256
    coord = Array(0, 0)
    mission = 'Guard'
    facing = 0
    tag = None
    veteran = 0
    group = -1
    autocreate_no = False
    autocreate_yes = True

    @abc.abstractmethod
    def __init__(self):
        pass

    @abc.abstractmethod
    def apply(self):
        pass

    @classmethod
    @abc.abstractmethod
    def fromvalue(cls, args: str | Array):
        pass

    def __repr__(self) -> str:
        return f'{self.typeof} ({self.coord})'


class FootUtil:
    @staticmethod
    def newobject(ins, args: str | Array):
        ins.owner = args[0]
        ins.typeof = args[1]
        ins.health = int(args[2])
        ins.coord = Array(map(int, args[3:5]))
        return ins

    @staticmethod
    def newunit(ins, args: str | Array):
        ins = FootUtil.newobject(ins, args)
        ins.facing = int(args[5])
        ins.mission = args[6]
        ins.tag = None if args[7] == 'None' else args[7]
        ins.veteran = int(args[8])
        ins.group = int(args[9])
        return ins


class Infantry(FootClass):
    def __init__(self):
        self.typeof = 'E1'
        self.subcell = 0
        self.onbridge = False

    @classmethod
    def fromvalue(cls, args: str | Array):
        if type(args) == str:
            args = args.split(',')
        ret = FootUtil.newobject(cls(), args)
        ret.subcell = int(args[5])
        ret.mission = args[6]
        ret.facing = int(args[7])
        ret.tag = None if args[8] == 'None' else args[8]
        ret.veteran = int(args[9])
        ret.group = int(args[10])
        ret.onbridge = args[11] == '1'
        ret.autocreate_no = args[12] == '1'
        ret.autocreate_yes = args[13] == '1'
        return ret

    def apply(self):
        return ",".join(map(str, [
            self.owner, self.typeof, self.health, self.coord, self.subcell,
            self.mission, self.facing, self.tag, self.veteran, self.group,
            int(self.onbridge),
            int(self.autocreate_no), int(self.autocreate_yes)
        ]))


class Aircraft(FootClass):
    def __init__(self):
        self.typeof = 'ORCA'

    @classmethod
    def fromvalue(cls, args: str | Array):
        if type(args) == str:
            args = args.split(',')
        ret = FootUtil.newunit(cls(), args)
        ret.autocreate_no = args[10] == '1'
        ret.autocreate_yes = args[11] == '1'
        return ret

    def apply(self):
        return ",".join(map(str, [
            self.owner, self.typeof, self.health,
            self.coord, self.facing, self.mission,
            self.tag, self.veteran, self.group,
            int(self.autocreate_no),
            int(self.autocreate_yes)
        ]))


class Vehicle(FootClass):
    def __init__(self):
        self.typeof = 'AMCV'
        self.onbridge = False
        self.followid = -1

    @classmethod
    def fromvalue(cls, args: str | Array):
        if type(args) == str:
            args = args.split(',')
        ret = FootUtil.newunit(cls(), args)
        ret.onbridge = args[10] == '1'
        ret.followid = int(args[11])
        ret.autocreate_no = args[12] == '1'
        ret.autocreate_yes = args[13] == '1'
        return ret

    def apply(self):
        return ",".join(map(str, [
            self.owner, self.typeof, self.health, self.coord, self.facing,
            self.mission, self.tag, self.veteran, self.group,
            int(self.onbridge), self.followid,
            int(self.autocreate_no), int(self.autocreate_yes)
        ]))


class Building:
    def __init__(self):
        self.owner = 'Neutral House'
        self.typeof = 'GAPOWR'
        self.health = 256
        self.coord = Array(0, 0)  # only consider the top
        self.facing = 0
        self.tag = None
        self.ai_sellable = False
        self.ai_rebuildable = False  # obsolete, as base node implemented
        self.powered = True
        self.upgrades = []
        self.spotlight = 0
        self.ai_repair = True
        self.norminal = False  # EnemyUIName doesn't work until Ares 0.b.

    @classmethod
    def loadbuilding(cls, args: str):
        if type(args) == str:
            args = args.split(',')
        ret = FootUtil.newobject(cls(), args)  # still fit even not FootClass.
        ret.facing = int(args[5])
        ret.tag = None if args[6] == 'None' else args[6]
        ret.ai_sellable = args[7] == '1'
        ret.ai_rebuildable = args[8] == '1'
        ret.powered = args[9] == '1'
        ret.upgrades = [args[12:15][i]
                        for i in range(int(args[10]))
                        if args[12:15][i] != 'None']
        ret.spotlight = int(args[11])
        ret.ai_repair = args[15] == '1'
        ret.norminal = args[16] == '1'
        return ret

    def apply(self):
        ups = self.upgrades.copy()
        ups.extend('None' for _ in range(3 - len(self.upgrades)))
        return ",".join(map(str, [
            self.owner, self.typeof, self.health, self.coord, self.facing,
            self.tag, int(self.ai_sellable), int(self.ai_rebuildable),
            int(self.powered), len(self.upgrades), self.spotlight,
            ",".join(ups), int(self.ai_repair), int(self.norminal)
        ]))

    def __repr__(self) -> str:
        return f'{self.typeof} TopCell({self.coord})'
