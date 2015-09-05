from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface #main class of the Live framework
from _Framework.InputControlElement import *
from _Framework.ButtonElement import ButtonElement 
from _Framework.EncoderElement import EncoderElement
from _Framework.Util import find_if
from MainSelectorComponent import MainSelectorComponent #this class will allow us to handle several modes
from ConfigurableButtonElement import ConfigurableButtonElement

class SparkLE(ControlSurface):
	""" Script for Arturia's SparkLE Controller """
	
	def __init__(self, c_instance):
		ControlSurface.__init__(self, c_instance)
		with self.component_guard(): # this line allows you to instanciate framework classes
			is_momentary = True # all our controlls will be momentary
			self._suggested_input_port = 'px700'
			self._suggested_output_port = 'px700'

			"definition of buttons represented by the keyboard notes"
			launch_buttons = [] # row of buttons launching the clips of a track
			for index in range(16):
				button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, index)
				button.name = '_Clip_' + str(index) + '_Button'
				launch_buttons.append(button)

			"buttons A, B, C, D are the buttons choosing he mode"
			mode_buttons = [ ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 16+index) for index in range(4) ]
			mode_buttons[0].name = 'A_mode'
			mode_buttons[1].name = 'B_mode'
			mode_buttons[2].name = 'C_mode'
			mode_buttons[3].name = 'D_mode'

			"pad controls definition"
			select_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 20)
			select_button.name = '_Select_Button' 
			translate_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 21)
			translate_button.name = '_Translate_Button'
			mute_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 22)
			mute_button.name = '_Mute_Button'
			solo_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 23)
			solo_button.name = '_Solo_Button'
			copy_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 28)
			copy_button.name = '_Copy_Button'
			erase_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 29)
			erase_button.name = '_Erase_Button'
			rewind_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 36)
			rewind_button.name = '_Rewind_Button'
			forward_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 37)
			forward_button.name = '_Forward_Button'

			"pads definition"
			pads = []
			for index in range(8):
				pad = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 60+index)
				pad.name = '_Clip_' + str(index) + '_Button'
				pads.append(pad)

			"transport buttons"
			transport_buttons = []
			for index in range(4):
				button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 24+index)
				button.name = '_Transport_Button_'+str(index)
				transport_buttons.append(button)

			"knobs definition"
			tempo_control = EncoderElement(MIDI_CC_TYPE, 0, 48, Live.MidiMap.MapMode.relative_binary_offset)
			tempo_control.name = "_Tempo_controller_"
			volume_control = EncoderElement(MIDI_CC_TYPE, 0, 47, Live.MidiMap.MapMode.relative_binary_offset)
			tempo_control.name = "_Volume_controller_"
			param_controls = []
			for index in range(3):
				control = EncoderElement(MIDI_CC_TYPE, 0, 49+index, Live.MidiMap.MapMode.relative_binary_offset)
				control.name = "_Param_"+str(index)+"_control"
				param_controls.append(control)

			"browser knob definition"
			browser_control = EncoderElement(MIDI_CC_TYPE, 0, 54, Live.MidiMap.MapMode.relative_binary_offset)
			browser_control.name = "_Browser_controller_"

			"browser button definition"
			browser_button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 56)
			browser_button.name = "_Browser_button_"
			"pattern leds definition"
			pattern_leds = []
			for index in range(4):
				led = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 41+index)
				led.name = str(index) + 'Pattern_Led'
				pattern_leds.append(led)

			"divide knob definition"
			divide_control = EncoderElement(MIDI_CC_TYPE, 0, 52, Live.MidiMap.MapMode.relative_binary_offset)
			divide_control.name = "_divide_controller_"

			"move knob definition"
			move_control = EncoderElement(MIDI_CC_TYPE, 0, 53, Live.MidiMap.MapMode.relative_binary_offset)
			move_control.name = "_move_controller_"

			"track leds definition"
			track_leds = []
			for index in range(8):
				led = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 68+index)
				led.name = str(index) + 'Track_Led'
				track_leds.append(led)

			self._selector = MainSelectorComponent(tuple(launch_buttons), tuple(mode_buttons), tuple(pads), tuple(transport_buttons), select_button, translate_button, mute_button, solo_button, tempo_control, volume_control, tuple(param_controls), copy_button, erase_button, rewind_button, forward_button, browser_control, browser_button, tuple(pattern_leds), tuple(track_leds), divide_control, move_control, self)
			self._selector.name = 'Main_Modes'
			self.set_highlighting_session_component(self._selector._session)

			self.log_message("SparkLE Loaded !")


	def disconnect(self):
		ControlSurface.disconnect(self)

	def handle_sysex(self, midi_bytes):
		result = find_if(lambda (id, _): midi_bytes[:len(id)] == id, self._forwarding_long_identifier_registry.iteritems())
		if result != None:
			id, control = result
			control.receive_value(midi_bytes[len(id):-1])
		else:
			self.log_message('Got unknown sysex message: ', midi_bytes)
