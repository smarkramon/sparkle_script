import Live
import math
from _Framework.TransportComponent import TransportComponent
from _Framework.SubjectSlot import subject_slot 

class SpecialTransportComponent(TransportComponent):
	
	def __init__(self, parent):
		super(SpecialTransportComponent, self).__init__() 
		self._undo_button = None 
		self._redo_button = None
		self._tempo_encoder_control = None
		self._parent = parent

	def set_tempo_encoder(self, control, fine_control = None):
		self._tempo_encoder_control = control != self._tempo_encoder_control and control
		self._tempo_encoder_value.subject = control
		self.update() 

	@subject_slot('value')	
	def _tempo_encoder_value(self, value):
		if self.is_enabled():
			assert (self._tempo_encoder_control != None)
			assert (value in range(128))
			backwards = (value <= 64)
			amount = value - 64
			if backwards:
				amount = -amount
			amount = math.pow(amount,3)
			step = 0.1 #step = 1.0 #reduce this for finer control; 1.0 is 1 bpm
			if backwards:
				step = -step
			tempo = max(20, min(999, (self.song().tempo + (amount * step))))
			self.song().tempo = tempo

	def set_undo_button(self, undo_button): 
		if undo_button != self._undo_button: 
			self._undo_button = undo_button 
			self._undo_value.subject = undo_button 
			self._update_undo_button() 

	def set_redo_button(self, redo_button): 
		if redo_button != self._redo_button: 
			self._redo_button = redo_button 
			self._redo_value.subject = redo_button 
			self.update()

	@subject_slot('value')	
	def _undo_value(self, value): 
		if self.is_enabled(): 
			if value != 0 or not self._undo_button.is_momentary(): 
				if self.song().can_undo: 
					self.song().undo() 
				elif self.song().can_redo: 
					self.song().redo() 
			self._update_undo_button() 

	def _update_undo_button(self): 
		if self.is_enabled() and self._undo_button: 
			self._undo_button.set_light(self._undo_button.is_pressed()) 

	@subject_slot('value') 
	def _redo_value(self, value): 
		if self.is_enabled(): 
			if value != 0 or not self._redo_button.is_momentary(): 
				if self.song().can_redo: 
					self.song().redo() 
			self._update_redo_button()

	def _update_redo_button(self): 
		if self.is_enabled() and self._redo_button: 
			self._redo_button.set_light(self._redo_button.is_pressed()) 




