#-*- coding:utf-8 -*-
# QQEnhancement addon for NVDA
# Copyright 2023 SmileSky, NVDA Chinese Community and other contributors
# released under GPL.
# This code is borrowed from the original add-on NVBox: https://gitee.com/sscn.byethost3.com/nvbox

import appModuleHandler, tones, ui, winUser
from controlTypes.role import Role
from controlTypes.state import State
from NVDAObjects.IAccessible import chromium
from scriptHandler import script
from . import chat, faces
# QQ内嵌网页树拦截器类
class QQDocumentTreeInterceptor(chromium.ChromeVBuf):
    def _get_isAlive(self):
        try:
            return super(QQDocumentTreeInterceptor,self).isAlive and self.rootNVDAObject.shouldCreateTreeInterceptor
        except AttributeError as e:
            return False
    def __contains__(self, obj):
        if obj and 'TXGuiFoundation' == obj.windowClassName and isinstance(obj, QQDocument):
            # 本来想支持一下消息列表的光标浏览，结果多少有些小问题，所以尚未实现
            return True
        return super().__contains__(obj)
# QQ 网页文档类
class QQDocument(chromium.Document):
    treeInterceptorClass=QQDocumentTreeInterceptor
    def _get_shouldCreateTreeInterceptor(self):
        return True
# QQ的一些特殊处理
class AppModule(appModuleHandler.AppModule):
    def event_NVDAObject_init(self, obj):pass
    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        if obj.windowClassName=='WebAccessbilityHost':
            # 用于支持QQ内嵌网页的光标浏览
            clsList.insert(0, chromium.Document)
        # elif Role.LISTITEM == obj.role and '消息' == obj.parent.name:
            # 尚未实现
            # clsList.insert(0, QQDocument)
        return clsList
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def terminate(self):
        super().terminate()
    def event_gainFocus(self, obj, nextHandler):
        # 修正 QQ 按钮标题播报问题
        if obj.role == Role.BUTTON and not obj.name:
            obj.name = obj.description
        try:
            nextHandler()
        except:pass
    def event_selection(self, obj, nextHandler):
        # 针对 QQ 的 Ctrl+tab 切换聊天窗口做了支持
        if obj.role == Role.TAB:
            # tab 选中的事件
            if State.SELECTED in obj.states:
                ui.message(obj.name)
                return
            # tab 去除选中的事件
            tones.beep(100, 30)
            return
        # 支持 QQ 表情选择的朗读
        if obj.windowText == 'FaceSelector':
            faces.onSelected(obj)
            return
        nextHandler()
    def event_valueChange(self, obj, nextHandler):
        # 表情输入处理
        faces.onInput(obj)
        nextHandler()
    def event_nameChange(self, obj, nextHandler):
        # 处理 QQ 的 alert 对话框
        if Role.PANE == obj.role:
            self.event_alert(obj, nextHandler)
            return
        nextHandler()
    def event_alert(self, obj, nextHandler):
        # 获取 obj 的子孙
        children = obj.recursiveDescendants
        # 如果没有子孙，就跳过
        if not children:
            nextHandler()
            return
        # 朗读对话框的内容
        for child in children:
            if child.role in (Role.BUTTON, Role.CHECKBOX):continue
            else:
                ui.message(child.name)
    def event_foreground(self, obj, nextHandler):
        # 判断当前窗口是不是一个对话框
        ws = obj.windowStyle
        if not (ws & winUser.WS_EX_APPWINDOW or ws & winUser.WS_GROUP):
            self.event_alert(obj, nextHandler)
            return
        nextHandler()
    def event_liveRegionChange(self, obj, nextHandler):
        # 禁止QQ下载群文件一直吵个不停
        if obj and obj.name.startswith('更新时间：'):return
        nextHandler()

    @script(gesture="kb:f11")
    def script_voiceChat(self, gesture):
        # 语音聊天
        chat.clickButton('发起语音通话')
    @script(gesture="kb:f10")
    def script_videoChat(self, gesture):
        # 视频聊天
        chat.clickButton('发起视频通话')
    @script(gesture="kb:f9")
    def script_voiceMsgRecord(self, gesture):
        # 开始录音
        chat.clickButton('更多', lambda x: x.next)
        chat.expectPopupMenu (lambda: chat.clickMenu ('语音消息'))
    @script(gesture="kb:shift+f9")
    def script_voiceMsgSend(self, gesture):
        # 发送语音消息
        chat.clickButton ('发送语音')
    @script(gesture="kb:control+f9")
    def script_voiceMsgCancel(self, gesture):
        # 取消录音
        chat.clickButton ('取消发送语音')