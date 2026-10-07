# -*- coding:utf-8 -*-
# QQEnhancement addon for NVDA
# Copyright 2023-2024 SmileSky, Cary-rowen, NVDA Chinese Community and other contributors
# released under GPL.
# This code is borrowed from the original add-on NVBox: https://gitee.com/sscn.byethost3.com/nvbox

import appModuleHandler
from NVDAObjects.IAccessible import chromium
from scriptHandler import script


def _isNewQQFramework(productVersion: str) -> bool:
	try:
		major, minor = (int(part) for part in productVersion.split(".", 2)[:2])
	except (TypeError, ValueError):
		return False
	return (major, minor) >= (9, 9)


class QQDocumentTreeInterceptor(chromium.ChromeVBuf):
	def _get_isAlive(self):
		try:
			return (
				super(QQDocumentTreeInterceptor, self).isAlive
				and self.rootNVDAObject.shouldCreateTreeInterceptor
			)
		except AttributeError:
			return False

	def __contains__(self, obj):
		if obj and "TXGuiFoundation" == obj.windowClassName and isinstance(obj, QQDocument):
			# 本来想支持一下消息列表的光标浏览，结果多少有些小问题，所以尚未实现
			return True
		return super().__contains__(obj)


# QQ 网页文档类
class QQDocument(chromium.Document):
	treeInterceptorClass = QQDocumentTreeInterceptor

	def _get_shouldCreateTreeInterceptor(self):
		return True


# QQ的一些特殊处理
class AppModule(appModuleHandler.AppModule):
	__gestures = {
		"kb:shift+enter": "speechToText",
	}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if _isNewQQFramework(self.productVersion):
			from .modern import Adapter as adapterClass
		else:
			from .legacy import Adapter as adapterClass
		self.adapter = adapterClass()
		if getattr(self.adapter, "gestures", None):
			self.clearGestureBindings()
			self.bindGestures(self.adapter.gestures)

	def _dispatchEvent(self, name, obj, nextHandler):
		handler = getattr(self.adapter, name, None)
		return handler(obj, nextHandler) if handler else nextHandler()

	def _dispatchScript(self, name, gesture):
		handler = getattr(self.adapter, name, None)
		return handler(gesture) if handler else gesture.send()

	def event_NVDAObject_init(self, obj):
		handler = getattr(self.adapter, "event_NVDAObject_init", None)
		if handler:
			handler(obj)

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		handler = getattr(self.adapter, "chooseNVDAObjectOverlayClasses", None)
		return handler(obj, clsList) if handler else clsList

	def event_gainFocus(self, obj, nextHandler):
		return self._dispatchEvent("event_gainFocus", obj, nextHandler)

	def event_selection(self, obj, nextHandler):
		return self._dispatchEvent("event_selection", obj, nextHandler)

	def event_valueChange(self, obj, nextHandler):
		return self._dispatchEvent("event_valueChange", obj, nextHandler)

	def event_nameChange(self, obj, nextHandler):
		return self._dispatchEvent("event_nameChange", obj, nextHandler)

	def event_alert(self, obj, nextHandler):
		return self._dispatchEvent("event_alert", obj, nextHandler)

	def event_foreground(self, obj, nextHandler):
		return self._dispatchEvent("event_foreground", obj, nextHandler)

	def event_liveRegionChange(self, obj, nextHandler):
		return self._dispatchEvent("event_liveRegionChange", obj, nextHandler)

	def script_speechToText(self, gesture):
		return self._dispatchScript("script_speechToText", gesture)

	@script(gesture="kb:f11")
	def script_voiceChat(self, gesture):
		return self._dispatchScript("script_voiceChat", gesture)

	@script(gesture="kb:f10")
	def script_videoChat(self, gesture):
		return self._dispatchScript("script_videoChat", gesture)

	@script(gesture="kb:f9")
	def script_voiceMsgRecord(self, gesture):
		return self._dispatchScript("script_voiceMsgRecord", gesture)

	@script(gesture="kb:shift+f9")
	def script_voiceMsgSend(self, gesture):
		return self._dispatchScript("script_voiceMsgSend", gesture)

	@script(gesture="kb:control+f9")
	def script_voiceMsgCancel(self, gesture):
		return self._dispatchScript("script_voiceMsgCancel", gesture)

	@script(description="隐藏 QQ 窗口", category="QQEnhancement")
	def script_hideWindow(self, gesture):
		return self._dispatchScript("script_hideWindow", gesture)

	@script(description="聚焦消息列表", category="QQEnhancement")
	def script_focusMessageList(self, gesture):
		return self._dispatchScript("script_focusMessageList", gesture)

	@script(description="聚焦消息输入框", category="QQEnhancement")
	def script_focusMessageInput(self, gesture):
		return self._dispatchScript("script_focusMessageInput", gesture)

	@script(description="聚焦会话列表", category="QQEnhancement")
	def script_focusSessionList(self, gesture):
		return self._dispatchScript("script_focusSessionList", gesture)

	def terminate(self):
		super().terminate()
