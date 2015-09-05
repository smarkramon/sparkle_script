from _Framework.ModeSelectorComponent import ModeSelectorComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ButtonSliderElement import ButtonSliderElement
from _Framework.ClipSlotComponent import ClipSlotComponent
from _Framework.ChannelStripComponent import ChannelStripComponent
from _Framework.SceneComponent import SceneComponent
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.MomentaryModeObserver import MomentaryModeObserver
from _Framework.TransportComponent import TransportComponent
from _Framework.DeviceComponent import DeviceComponent
from _Framework.EncoderElement import EncoderElement
from _Framework.ToggleComponent import ToggleComponent
from SpecialSessionComponent import SpecialSessionComponent
from SpecialMixerComponent import SpecialMixerComponent
from SpecialTransportComponent import SpecialTransportComponent
import time

SCALES = 	{'Session':[0,1,2,3,4,5,6,7,8,9,10,11],
			'Auto':[0,1,2,3,4,5,6,7,8,9,10,11],
			'Chromatic':[0,1,2,3,4,5,6,7,8,9,10,11],
			'DrumPad':[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
			'Major':[0,2,4,5,7,9,11],
			'Minor':[0,2,3,5,7,8,10],
			'Dorian':[0,2,3,5,7,9,10],
			'Mixolydian':[0,2,4,5,7,9,10],
			'Lydian':[0,2,4,6,7,9,11],
			'Phrygian':[0,1,3,5,7,8,10],
			'Locrian':[0,1,3,4,7,8,10],
			'Diminished':[0,1,3,4,6,7,9,10],
			'Whole-half':[0,2,3,5,6,8,9,11],
			'Whole Tone':[0,2,4,6,8,10],
			'Minor Blues':[0,3,5,6,7,10],
			'Minor Pentatonic':[0,3,5,7,10],
			'Major Pentatonic':[0,2,4,7,9],
			'Harmonic Minor':[0,2,3,5,7,8,11],
			'Melodic Minor':[0,2,3,5,7,9,11],
			'Dominant Sus':[0,2,5,7,9,10],
			'Super Locrian':[0,1,3,4,6,8,10],
			'Neopolitan Minor':[0,1,3,5,7,8,11],
			'Neopolitan Major':[0,1,3,5,7,9,11],
			'Enigmatic Minor':[0,1,3,6,7,10,11],
			'Enigmatic':[0,1,4,6,8,10,11],
			'Composite':[0,1,4,6,7,8,11],
			'Bebop Locrian':[0,2,3,5,6,8,10,11],
			'Bebop Dominant':[0,2,4,5,7,9,10,11],
			'Bebop Major':[0,2,4,5,7,8,9,11],
			'Bhairav':[0,1,4,5,7,8,11],
			'Hungarian Minor':[0,2,3,6,7,8,11],
			'Minor Gypsy':[0,1,4,5,7,8,10],
			'Persian':[0,1,4,5,6,8,11],
			'Hirojoshi':[0,2,3,7,8],
			'In-Sen':[0,1,5,7,10],
			'Iwato':[0,1,5,6,10],
			'Kumoi':[0,2,3,7,9],
			'Pelog':[0,1,3,4,7,8],
			'Spanish':[0,1,3,4,5,6,8,10]
			}

class TranslationSelectorComponent(ModeSelectorComponent):
	"""this class will use the 1-8/9-16 button to chose how to translate midi notes of the drumpads and of the sequencer buttons"""

	def __init__(self, keys, pads, translate_button, parent):
		ModeSelectorComponent.__init__(self)
		self._keys = keys
		self._pads = pads
		self._translate_button = translate_button
		self._scales = SCALES.keys()
		self._scale_index = 0
		self._scale_offset = 0
		self._parent = parent
		self.set_mode_toggle(translate_button)

	def disconnect(self):
		self._translate_button.remove_value_listener(self._mode_value)
		self._keys = None
		self._pads = None
		self._translate_button = None
		self._parent = None
		ModeSelectorComponent.disconnect(self)

	def number_of_modes(self):
		return 2

	def mode(self):
		return self._mode_index

	def update(self):
		self._setup_keys_translation()
		self._translate_button.set_light(self._mode_index==1)
		self._parent._update_session_translation()

	def _scale_index_value(self, value):
		if value != 64:
			self._scale_index = (self._scale_index + (value - 64)) % len(self._scales)
			self._parent._parent.show_message('Scale: '+str(self._scale_index)+' - '+self._scales[self._scale_index])
			self.update()

	def _scale_offset_value(self, value):
		if value != 64:
			self._scale_offset = (self._scale_offset + (value - 64))
			self._parent._parent.show_message('Offset: '+str(self._scale_offset))
			self.update()

	def _setup_keys_translation(self):
		"setup the keys associated to the sequencer"
		if self._parent._mode_index == 3:
			scale = SCALES[self._scales[self._scale_index]]
			for index in range(len(self._keys)):
				translated_index = index + 16*self._mode_index
				note = scale[translated_index%len(scale)] + 12*(translated_index//len(scale)) + self._scale_offset
				self._keys[index].set_identifier(24+note)
				self._keys[index].set_channel(1)
			for index in range(len(self._pads)):
				translated_index = index + 8*self._mode_index
				note = scale[translated_index%len(scale)] + 12*(translated_index//len(scale)) + self._scale_offset
				self._pads[index].send_value(0,True)
				self._pads[index].set_identifier(36+note)
				self._pads[index].set_channel(2)
		else:
			for index in range(len(self._keys)):
				self._keys[index].use_default_message()
			for index in range(len(self._pads)):
				translated_index = index + 8*self._mode_index
				self._pads[index].set_identifier(36+translated_index)
				self._pads[index].set_channel(2)