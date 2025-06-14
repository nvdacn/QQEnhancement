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
from logHandler import log
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
        # 处理消息列表内的文件上传/下载窗格聚焦
        if obj.role == Role.PANE and obj.simpleFirstChild is not None and obj.simpleFirstChild.role == Role.GRAPHIC:
            try:
                info_parts = []
                max_info_count = 3  # 我们最多只关心前3条静态文本信息
                # 从窗格的第一个子对象开始顺序扫描
                current_child = obj.simpleFirstChild
                # 循环，直到没有更多兄弟节点，或者我们已经找到了所需数量的信息
                while current_child and len(info_parts) < max_info_count:
                    # 只关心角色为 STATICTEXT 且有有效名称的对象
                    if current_child.role == Role.STATICTEXT and current_child.name and current_child.name.strip():
                        info_parts.append(current_child.name.strip())
                    current_child = current_child.simpleNext
                if info_parts:
                    obj.name = " ".join(info_parts)
                    obj.value = "" # 清空 value，防止 NVDA 朗读重复或无关内容
                else:
                    log.debugWarning("File pane focus (practical scan): No STATICTEXT info found.")
            except Exception as e:
                log.debugWarning(f"Error processing file pane focus with practical scan: {e}")
                pass
           
        # 处理语音消息窗格聚焦
        if obj.role == Role.PANE and obj.value == "语音控件":
            try:
                duration = obj.simpleLastChild.name
                # 只有在获取到时长时才继续处理，因为时长是核心信息
                if duration:
                    # 构建朗读内容的各个部分
                    parts = [f"语音消息 {duration}秒"]
                   
                    speechToTextResult = obj.simpleFirstChild.name if obj.simpleFirstChild.role == Role.STATICTEXT else ""
                    if speechToTextResult:
                        parts.append(speechToTextResult)
                  
                    parts.append("按空格键或回车键可播放")
                    speechToTextTip = "按 Shift+回车键可转文字" if obj.simpleFirstChild.simpleNext.description == "转为文字显示" else ""
                    if speechToTextTip:
                        parts.append(speechToTextTip)
                    obj.name = " ".join(parts)
                    obj.value = ""
                else:
                    # 如果时长获取不到，记录日志
                    log.debugWarning("Voice message focus: Could not retrieve message duration.")
            except (AttributeError, TypeError):
                # 如果对象树结构不符，安静地忽略
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

