import Live
from _Framework.ButtonElement import *

class ConfigurableButtonElement(ButtonElement):
	""" Special button class that can be configured with custom on- and off-values """

	def __init__(self, is_momentary, msg_type, channel, identifier):
		ButtonElement.__init__(self, is_momentary, msg_type, channel, identifier)
		self._on_value = 127
		self._off_value = 0
		self._is_enabled = True
		self._is_notifying = False
		self._force_next_value = False
		self._pending_listeners = []

	def set_on_off_values(self, on_value, off_value):
		assert (on_value in range(128))
		assert (off_value in range(128))
		self.clear_send_cache()
		self._on_value = on_value
		self._off_value = off_value

	def set_force_next_value(self):
		self._force_next_value = True

	def set_enabled(self, enabled):
		self._is_enabled = enabled

	def turn_on(self):
		self.send_value(self._on_value)

	def turn_off(self):
		self.send_value(self._off_value)

	def reset(self):
		self.send_value(4)

	def add_value_listener(self, callback, identify_sender = False):
		if not self._is_notifying:
			ButtonElement.add_value_listener(self, callback, identify_sender)
		else:
			self._pending_listeners.append((callback, identify_sender))

	def receive_value(self, value):
		self._is_notifying = True
		ButtonElement.receive_value(self, value)
		self._is_notifying = False
		for listener in self._pending_listeners:
			self.add_value_listener(listener[0], listener[1])

		self._pending_listeners = []

	def send_value(self, value, force = False):
		ButtonElement.send_value(self, value, force or self._force_next_value)
		self._force_next_value = False

	def install_connections(self, install_translation_callback, install_mapping_callback, install_forwarding_callback):
		if self._is_enabled:
			ButtonElement.install_connections(self, install_translation_callback, install_mapping_callback, install_forwarding_callback)
		elif self._msg_channel != self._original_channel or self._msg_identifier != self._original_identifier:
			install_translation_callback(self._msg_type, self._original_identifier, self._original_channel, self._msg_identifier, self._msg_channel)

	def _do_send_value(self, value, channel = None):
		data_byte1 = self._original_identifier
		data_byte2 = value
		status_byte = self._status_byte(channel or self._original_channel)
		#added to send a note_off signal
		if value == 0:
			status_byte -= 16
		if self._msg_type == 2:
			data_byte1 = value & 127
			data_byte2 = value >> 7 & 127
		if self.send_midi((status_byte, data_byte1, data_byte2)):
			self._last_sent_message = (value, channel)
			if self._report_output:
				is_input = True
				self._report_value(value, not is_input)
		self._delayed_value_to_send = None
		self._delayed_channel = None