# -*- coding:utf-8 -*-

import api
import tones
import winUser


class Adapter:
	gestures = {
		"kb:control+h": "hideWindow",
		"kb:escape": "hideWindow",
		"kb:alt+f4": "hideWindow",
		"kb:control+w": "hideWindow",
		"kb:alt+m": "focusMessageList",
		"kb:alt+s": "focusMessageInput",
		"kb:alt+l": "focusSessionList",
	}

	def __init__(self):
		self.currentWindowHandle = None
		self.activeWindowHandle = None
		self.messageInput = None
		self.messageList = None
		self.sessionList = None

	def event_NVDAObject_init(self, obj):
		self._remember(obj)

	def _windowHandle(self, obj):
		try:
			return obj.windowHandle
		except Exception:
			return None

	def _hasClass(self, obj, className):
		try:
			value = (getattr(obj, "IA2Attributes", None) or {}).get("class", "")
		except Exception:
			return False
		return isinstance(value, str) and className in value.split()

	def _remember(self, obj):
		if self._hasClass(obj, "ExEditor-qq-msg-editor"):
			self.messageInput = obj
		elif self._hasClass(obj, "chat-msg-area__vlist"):
			self.messageList = obj
		elif self._hasClass(obj, "recent-contact-list"):
			self.sessionList = obj

	def event_gainFocus(self, obj, nextHandler):
		windowHandle = self._windowHandle(obj)
		if windowHandle and self.activeWindowHandle and windowHandle != self.activeWindowHandle:
			self.messageInput = None
			self.messageList = None
		self.activeWindowHandle = windowHandle or self.activeWindowHandle
		self._remember(obj)
		if self._hasClass(obj, "ExEditor-qq-msg-editor"):
			self.currentWindowHandle = windowHandle
		nextHandler()

	def _focus(self, obj):
		if obj is None or (self.activeWindowHandle and self._windowHandle(obj) != self.activeWindowHandle):
			return
		try:
			obj.setFocus()
		except Exception:
			pass

	def _findMessageList(self):
		current = self.messageInput
		for _ in range(6):
			if current is None:
				break
			if self._hasClass(current, "chat-msg-area__vlist"):
				return current
			try:
				child = current.simpleFirstChild
			except Exception:
				child = None
			for _ in range(64):
				if child is None:
					break
				if self._hasClass(child, "chat-msg-area__vlist"):
					return child
				try:
					child = child.simpleNext
				except Exception:
					break
			try:
				current = current.parent
			except Exception:
				break
		return None

	def script_focusMessageList(self, gesture):
		inputHandle = self._windowHandle(self.messageInput)
		if self._windowHandle(self.messageList) != inputHandle:
			self.messageList = None
		if self.messageList is None and self.messageInput is not None:
			self.messageList = self._findMessageList()
		if self._hasClass(self.messageList, "chat-msg-area__vlist"):
			self._focus(self.messageList)

	def script_focusMessageInput(self, gesture):
		self._focus(self.messageInput)

	def script_focusSessionList(self, gesture):
		self._focus(self.sessionList)

	def script_hideWindow(self, gesture):
		focus = api.getFocusObject()
		hwnd = getattr(focus, "windowHandle", None)
		if not hwnd:
			return
		rootHwnd = winUser.user32.GetAncestor(hwnd, winUser.GA_ROOTOWNER)
		if not rootHwnd:
			rootHwnd = hwnd
		if self.currentWindowHandle == hwnd:
			winUser.user32.PostMessageW(rootHwnd, 0x0010, 0, 0)
		else:
			winUser.user32.ShowWindowAsync(rootHwnd, winUser.SW_HIDE)
		tones.beep(80, 20)
