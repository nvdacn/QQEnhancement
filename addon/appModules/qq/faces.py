#-*- coding:utf-8 -*-
# QQEnhancement addon for NVDA
# Copyright 2023 SmileSky, NVDA Chinese Community and other contributors
# released under GPL.
# This code is borrowed from the original add-on NVBox: https://gitee.com/sscn.byethost3.com/nvbox

import api, tones, ui
faceMap={} # 保存表情代码与描述的映射字典
with open(f'{__file__[0:-3]}.txt', 'r', encoding='utf-8') as f:
    # 读取表情映射表文件
    lines=f.readlines()
    for i in range(0, len(lines), 2):
        k=lines[i].strip().split(' ')
        v=lines[i + 1].strip().split(' ')
        for j in range(len(k)):
            faceMap[k[j]]=v[j]
# 表情面板的显示状态
hasFaceSelector = False
# 当某个表情选中时，朗读表情代码对应的描述
def onSelected(obj):
    global hasFaceSelector
    hasFaceSelector = True
    tones.beep(400 + obj.IAccessibleChildID * 10, 50, 10, 10)
    ui.message(faceMap[obj.name[1:]])
    # 把焦点的持有权交给列表，这样就不会朗读输入框本身的内容了
    try:
        api.setFocusObject(obj)
    except:pass
def onInput(obj):
    global hasFaceSelector
    # 当表情选择完毕，把焦点切回输入框
    if hasFaceSelector:
        hasFaceSelector=False
        try:
            api.setFocusObject(obj)
        except:pass