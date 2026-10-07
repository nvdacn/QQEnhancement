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
		self.activeRootHandle = None
		self.messageInput = None
		self.messageList = None
		self.messageListContext = None
		self.sessionList = None

	def event_NVDAObject_init(self, obj):
		self._remember(obj)

	def _remember(self, obj):
		try:
			className = (getattr(obj, "IA2Attributes", None) or {}).get("class", "")
		except Exception:
			className = ""
		if "ExEditor-qq-msg-editor" in className:
			self.messageInput = obj
		elif "chat-msg-area__vlist" in className:
			self.messageList = obj
			self.messageListContext = self.messageInput
		elif "recent-contact-list" in className:
			self.sessionList = obj
		elif getattr(obj, "name", "") == "消息列表":
			self.messageList = obj
			self.messageListContext = None
		elif getattr(obj, "name", "") == "会话列表":
			self.sessionList = obj

	def event_gainFocus(self, obj, nextHandler):
		rootHandle = getattr(obj, "windowHandle", None)
		if rootHandle and self.activeRootHandle and rootHandle != self.activeRootHandle:
			self.messageInput = None
			self.messageList = None
		self.activeRootHandle = rootHandle or self.activeRootHandle
		className = ""
		try:
			className = (getattr(obj, "IA2Attributes", None) or {}).get("class", "")
		except Exception:
			pass
		if "ExEditor-qq-msg-editor" in className and self.messageInput is not obj:
			self.messageList = None
			self.messageListContext = None
		self._remember(obj)
		if "ExEditor-qq-msg-editor" in className:
			self.currentWindowHandle = obj.windowHandle
		nextHandler()

	def _findFocusable(self, root):
		queue = [root]
		seen = set()
		fallback = None
		index = 0
		while index < len(queue) and len(seen) < 128:
			obj = queue[index]
			index += 1
			for child in self._simpleChildren(obj, 128 - len(seen)):
				if id(child) in seen:
					continue
				seen.add(id(child))
				try:
					hasFocus = child.hasFocus
				except Exception:
					hasFocus = False
				if hasFocus:
					return child
				try:
					isFocusable = child.isFocusable
				except Exception:
					isFocusable = False
				if fallback is None and isFocusable:
					fallback = child
				queue.append(child)
		return fallback

	def _simpleChildren(self, root, limit):
		try:
			child = root.simpleFirstChild
		except Exception:
			return
		for _ in range(limit):
			if child is None:
				return
			yield child
			try:
				child = child.simpleNext
			except Exception:
				return

	def _focus(self, obj):
		if obj is None:
			return
		if self.activeRootHandle and getattr(obj, "windowHandle", None) != self.activeRootHandle:
			return
		try:
			isFocusable = obj.isFocusable
		except Exception:
			isFocusable = False
		target = obj if isFocusable else self._findFocusable(obj)
		if target is None:
			return
		try:
			target.setFocus()
		except Exception:
			pass

	def _findMessageList(self):
		current = self.messageInput
		for _ in range(6):
			if current is None:
				break
			try:
				attrs = getattr(current, "IA2Attributes", None) or {}
			except Exception:
				attrs = {}
			if "chat-msg-area__vlist" in attrs.get("class", ""):
				return current
			for child in self._simpleChildren(current, 64):
				try:
					attrs = getattr(child, "IA2Attributes", None) or {}
				except Exception:
					attrs = {}
				if "chat-msg-area__vlist" in attrs.get("class", ""):
					return child
			try:
				current = current.parent
			except Exception:
				break
		return None

	def script_focusMessageList(self, gesture):
		if self.messageListContext is not self.messageInput:
			self.messageList = None
		if self.messageList is None and self.messageInput is not None:
			messageList = self._findMessageList()
			if messageList is not None:
				self.messageList = messageList
				self.messageListContext = self.messageInput
		className = (getattr(self.messageList, "IA2Attributes", None) or {}).get("class", "")
		if "chat-msg-area__vlist" in className:
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
