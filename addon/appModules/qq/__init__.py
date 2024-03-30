#-*- coding:utf-8 -*-
# QQEnhancement addon for NVDA
# Copyright 2023-2024 SmileSky, Cary-rowen, NVDA Chinese Community and other contributors
# released under GPL.
# This code is borrowed from the original add-on NVBox: https://gitee.com/sscn.byethost3.com/nvbox

import appModuleHandler
import tones
import ui
import winUser
import api
from controlTypes.state import State
from controlTypes.role import Role
from displayModel import DisplayModelTextInfo
from NVDAObjects.IAccessible import IA2TextTextInfo
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

    def script_speechToText(self, gesture):
        focusObj = api.getFocusObject()
        if focusObj.role == Role.PANE:
            chat.clickButton('转为文字显示', obj=focusObj)
        else:
            gesture.send()

    # 执行语音转文字的手势
    __gestures={
        "kb:shift+enter": "speechToText"
    }

    # 排除的对话框朗读内容
    alertFilter = ("已阅读并同意", "服务协议", "和", "QQ隐私保护指引", "登录中", "电脑管家正在进行安全检测", ".")
    def shouldSkip(self, child):
        return (
            not child.name or 
            child.name in self.alertFilter or 
            child.role in (Role.BUTTON, Role.CHECKBOX) or 
            State.INVISIBLE in child.states or 
            not child.states
        )

    def event_gainFocus(self, obj, nextHandler):
        # 处理消息列表内的文件上传窗格聚焦
        if obj.role == Role.PANE and obj.simpleFirstChild is not None and obj.simpleFirstChild.role == Role.GRAPHIC:
            try:
                fileName = obj.firstChild.firstChild.next.name
                fileSize = obj.firstChild.firstChild.next.next.name
                obj.name = f"{fileName} {fileSize}"
            except: pass
        # 处理语音消息窗格聚焦
        if obj.role == Role.PANE and obj.value == "语音控件":
            try:
                duration = obj.simpleLastChild.name
                speechToTextResult = obj.simpleFirstChild.name if obj.simpleFirstChild.role == Role.STATICTEXT else ""
                speechToTextTip = "按 Shift+回车键可转文字" if obj.simpleFirstChild.simpleNext.description == "转为文字显示" else ""
                obj.name = f"语音消息 {duration}秒 {speechToTextResult} 按空格键或回车键可播放 {speechToTextTip}"
                obj.value = ""
            except: pass
        # 处理微软输入法上屏后不能朗读消息输入框内容
        poss=api.getReviewPosition().copy()
        obj=api.getFocusObject()
        if poss is not None and isinstance(poss, IA2TextTextInfo):
            if obj.name is not None and obj.name.startswith(u"\u8f93\u5165"):
                self.pos=poss
                self.obj=obj
        elif isinstance(poss, DisplayModelTextInfo):
            try:
                if self.pos and self.pos is not None:
                    api.setFocusObject(self.obj)
            except:
                pass

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
            if self.shouldSkip(child): continue
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

    def terminate(self):
        super().terminate()

