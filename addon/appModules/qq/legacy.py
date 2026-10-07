# -*- coding:utf-8 -*-

import tones
import ui
import winUser
import api
from controlTypes.state import State
from controlTypes.role import Role
from logHandler import log
from NVDAObjects.IAccessible import chromium

from . import chat, faces


class Adapter:
	alertFilter = (
		"已阅读并同意",
		"服务协议",
		"和",
		"QQ隐私保护指引",
		"登录中",
		"电脑管家正在进行安全检测",
		".",
	)

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		if obj.windowClassName == "WebAccessbilityHost":
			clsList.insert(0, chromium.Document)
		return clsList

	def script_speechToText(self, gesture):
		focusObj = api.getFocusObject()
		if focusObj.role == Role.PANE:
			chat.clickButton("转为文字显示", obj=focusObj)
		else:
			gesture.send()

	def shouldSkip(self, child):
		return (
			not child.name
			or child.name in self.alertFilter
			or child.role in (Role.BUTTON, Role.CHECKBOX)
			or State.INVISIBLE in child.states
			or not child.states
		)

	def event_gainFocus(self, obj, nextHandler):
		# 处理消息列表内的文件上传/下载窗格聚焦
		if (
			obj.role == Role.PANE
			and obj.simpleFirstChild is not None
			and obj.simpleFirstChild.role == Role.GRAPHIC
		):
			try:
				info_parts = []
				max_info_count = 3
				current_child = obj.simpleFirstChild
				while current_child and len(info_parts) < max_info_count:
					if (
						current_child.role == Role.STATICTEXT
						and current_child.name
						and current_child.name.strip()
					):
						info_parts.append(current_child.name.strip())
					current_child = current_child.simpleNext
				if info_parts:
					obj.name = " ".join(info_parts)
					obj.value = ""
			except Exception as e:
				log.debugWarning(f"Error processing file pane focus with practical scan: {e}")

		# 处理语音消息窗格聚焦
		if obj.role == Role.PANE and obj.value == "语音控件":
			try:
				duration = obj.simpleLastChild.name
				if duration:
					parts = [f"语音消息 {duration}秒"]
					speechToTextResult = (
						obj.simpleFirstChild.name if obj.simpleFirstChild.role == Role.STATICTEXT else ""
					)
					if speechToTextResult:
						parts.append(speechToTextResult)
					parts.append("按空格键或回车键可播放")
					speechToTextTip = (
						"按 Shift+回车键可转文字"
						if obj.simpleFirstChild.simpleNext.description == "转为文字显示"
						else ""
					)
					if speechToTextTip:
						parts.append(speechToTextTip)
					obj.name = " ".join(parts)
					obj.value = ""
			except (AttributeError, TypeError):
				pass

		if obj.role == Role.BUTTON and not obj.name:
			obj.name = obj.description
		try:
			nextHandler()
		except Exception:
			pass

	def event_selection(self, obj, nextHandler):
		if obj.role == Role.TAB:
			if State.SELECTED in obj.states:
				ui.message(obj.name)
				return
			tones.beep(100, 30)
			return
		if obj.windowText == "FaceSelector":
			faces.onSelected(obj)
			return
		nextHandler()

	def event_valueChange(self, obj, nextHandler):
		faces.onInput(obj)
		nextHandler()

	def event_nameChange(self, obj, nextHandler):
		if Role.PANE == obj.role:
			self.event_alert(obj, nextHandler)
			return
		nextHandler()

	def event_alert(self, obj, nextHandler):
		children = obj.recursiveDescendants
		if not children:
			nextHandler()
			return
		for child in children:
			if self.shouldSkip(child):
				continue
			ui.message(child.name)

	def event_foreground(self, obj, nextHandler):
		ws = obj.windowStyle
		if not (ws & winUser.WS_EX_APPWINDOW or ws & winUser.WS_GROUP):
			self.event_alert(obj, nextHandler)
			return
		nextHandler()

	def event_liveRegionChange(self, obj, nextHandler):
		if obj and obj.name.startswith("更新时间："):
			return
		nextHandler()

	def script_voiceChat(self, gesture):
		chat.clickButton("发起语音通话")

	def script_videoChat(self, gesture):
		chat.clickButton("发起视频通话")

	def script_voiceMsgRecord(self, gesture):
		chat.clickButton("更多", lambda x: x.next)
		chat.expectPopupMenu(lambda: chat.clickMenu("语音消息"))

	def script_voiceMsgSend(self, gesture):
		chat.clickButton("发送语音")

	def script_voiceMsgCancel(self, gesture):
		chat.clickButton("取消发送语音")
