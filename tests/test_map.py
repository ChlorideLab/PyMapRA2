# -*- coding: utf-8 -*-
# @Time: 2022/04/27 1:12
# @Author: Chloride
import _context

import relertpy as rpy

wither = rpy.CCMap('.\\awither.map')
for i in wither.teams:
    print(i)
wither.save()

# wither_c = rpy.CCMap("D:\\wither.map")
# print(len(wither) == len(wither_c))
