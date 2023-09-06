#-*- coding:utf-8 -*-
# QQEnhancement addon for NVDA
# Copyright 2023 SmileSky, NVDA Chinese Community and other contributors
# released under GPL.
# This code is borrowed from the original add-on NVBox: https://gitee.com/sscn.byethost3.com/nvbox

import time
import api, gui, IAccessibleHandler, mouseHandler, tones, ui, winUser, wx
from controlTypes.role import Role

def clickButton(name, onChoice = lambda x: True):
    # 点击按钮
    obj = api.getForegroundObject()
    if not obj:
        # 没有获取到窗口对象就直接返回
        tones.beep(500, 50)
        return
    tones.beep(800, 50)
    # 找到按钮
    for child in obj.recursiveDescendants:
        if child.role == Role.BUTTON and child.description == name and onChoice(child):
            click(child)
def hasObject(name):
    # 判断是否有某个对象
    obj = api.getForegroundObject()
    if not obj: return
    for child in obj.recursiveDescendants:
        if child.name and name in child.name or child.description and name in child.description:
            return True
def expectPopupMenu (callback, timeout = 5):
    # 等待一个弹出菜单
    ts = time.time ()
    def cb ():
        if ts + timeout < time.time (): return
        focus = api.getFocusObject ()
        if focus.name == 'TXMenuWindow':
            wx.CallLater(0.5, callback)
            return
        wx.CallLater (0.1, cb)
    cb ()
def clickMenu (name):
    # 点击菜单
    obj = api.getFocusObject()
    if not obj:
        # 没有获取到焦点对象就直接返回
        tones.beep(500, 50)
        return
    tones.beep(800, 50)
    # 找到菜单项
    for child in obj.recursiveDescendants:
        if child.role == Role.MENUITEM and child.name == name:
            click(child)
def click(obj):
    # 点击操作
    l, t, w, h = obj.location
    x, y = int(l + w / 2), int(t + h / 2)
    winUser.setCursorPos(x, y)
    mouseHandler.executeMouseMoveEvent(x, y)
    mouseHandler.doPrimaryClick()