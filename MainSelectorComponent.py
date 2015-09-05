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
from TranslationSelectorComponent import TranslationSelectorComponent
from SpecialMixerComponent import SpecialMixerComponent
from SpecialTransportComponent import SpecialTransportComponent
from StepSequencerComponent import StepSequencerComponent
import time


class MainSelectorComponent(ModeSelectorComponent):
	""" Class that reassigns the buttons on the Spark to different functions """

	def __init__(self, launch_buttons, mode_buttons, pads, transport_buttons, select_button, translate_button, mute_button, solo_button, tempo_control, volume_control, param_controls, copy_button, erase_button, rewind_button, forward_button, browser_control, browser_button, pattern_leds, track_leds, divide_control, move_control, parent):
		"verifies that the buttons given are compatible with the selector component"
		assert isinstance(launch_buttons, tuple)
		assert (len(launch_buttons) == 16)
		assert isinstance(mode_buttons, tuple)
		assert (len(mode_buttons) == 4)
		assert isinstance(pads, tuple)
		assert (len(pads) == 8)
		assert (len(transport_buttons) == 4)
		assert (len(param_controls) == 3)
		ModeSelectorComponent.__init__(self)

		"the parent atribute allows us to control the control surface component"
		"it can be used for example to get the currently selected track"
		self._parent = parent

		"definition of all the components we will map buttons with"
		self._session = SpecialSessionComponent(8, 16)
		self._session.name = 'Session_Control'
		self._mixer = SpecialMixerComponent(8)
		self._mixer.name = 'Mixer_Control'
		self._transport = SpecialTransportComponent(self)
		self._transport.name = 'Transport_Control'
		self._device = DeviceComponent()
		self._device.name = 'Device_Control'

		"definition of all the buttons that will be used"
		self._launch_buttons = launch_buttons
		self._mode_buttons = mode_buttons
		self._pads = pads
		self._all_buttons = []
		self._select_button = select_button
		self._translate_button = translate_button
		self._mute_button = mute_button
		self._solo_button = solo_button
		self._transport_buttons = transport_buttons
		self._copy_button = copy_button
		self._erase_button = erase_button
		self._rewind_button = rewind_button
		self._forward_button = forward_button
		self._browser_control = browser_control
		self._browser_button = browser_button
		self._divide_control = divide_control
		self._move_control = move_control
		self._track_leds = track_leds
		self._pattern_leds = pattern_leds

		"definition of all the controls that will be used"
		self._tempo_control = tempo_control
		self._volume_control = volume_control
		self._param_controls = param_controls

		for button in self._launch_buttons + self._mode_buttons + self._pads + self._transport_buttons + self._track_leds + self._pattern_leds:
			self._all_buttons.append(button)
		self._all_buttons.append(self._select_button)
		self._all_buttons.append(self._translate_button)
		self._all_buttons.append(self._mute_button)
		self._all_buttons.append(self._solo_button)
		self._all_buttons.append(self._copy_button)
		self._all_buttons.append(self._erase_button)
		self._all_buttons.append(self._rewind_button)
		self._all_buttons.append(self._forward_button)

		self._stepseq = StepSequencerComponent(self, self._launch_buttons,self._pads, self._translate_button, self._select_button, self._mute_button, self._solo_button, tuple(self._transport_buttons), forward_button, rewind_button, pattern_leds)
		self._translation_selector = TranslationSelectorComponent(tuple(self._launch_buttons), tuple(self._pads), self._translate_button, self)

		self._init_session()
		self._all_buttons = tuple(self._all_buttons)
		self._mode_index=0
		self._previous_mode_index=-1
		self.set_mode_buttons(mode_buttons)
		self._parent = parent
		self._selected_track_index=0
		self._previous_track_index=0
		self._parent.set_device_component(self._device)
		for button in self._all_buttons:
			button.send_value(0,True)

	def disconnect(self):
		for button in self._mode_buttons:
			button.remove_value_listener(self._mode_value)
		for button in self._all_buttons:
			button.send_value(0,True)

		self._session = None
		self._mixer = None
		self._transport = None
		self._launch_buttons = None
		self._mode_buttons = None
		self._pads = None
		self._transport_buttons = None
		ModeSelectorComponent.disconnect(self)

	def _update_mode(self):
		"""check if the mode selected is a new mode and if so update the controls"""
		mode = self._modes_heap[-1][0]
		assert mode in range(self.number_of_modes())
		if self._mode_index==mode or (mode == 2 and not self.song().view.selected_track.has_midi_input):
			self._previous_mode_index=self._mode_index
		else:
			self._mode_index = mode
			for button in self._all_buttons:
				button.send_value(0,True)
			self.update()
	
	def set_mode(self, mode):
		self._clean_heap()
		self._modes_heap = [(mode, None, None)]

	def number_of_modes(self):
		return 4

	def _update_mode_buttons(self):
		"""lights up the mode buttons if selected"""
		for index in range(4):
			if (index == self._mode_index):	
				self._modes_buttons[index].turn_on()
			else:
				self._modes_buttons[index].turn_off()

	def update(self):
		"""main method of the class that calls the assignation methods corresponding to the current mode"""
		"""it is called when the mode changes and when the selected track changes"""
		assert (self._modes_buttons != None)
		"links the session to the mixer, so that when change the selected track the session also changes position"
		self._session.set_mixer(self._mixer)
		if self.is_enabled():
			self._update_mode_buttons()
			self._translation_selector.update()
			
			as_active = True
			as_enabled = True
			self._session.set_allow_update(False)#we dont want the controlls to change while we are updating the assignations

			if (self._mode_index == 0):
				"A: Transport mode"
				"we activate the transport buttons and tha launch scenes buttons"
				#self._parent.log_message("Launching mode")
				self._setup_step_sequencer(not as_active)
				self._setup_launch_clips(not as_active,not as_enabled)
				self._setup_track_controls(not as_active)
				self._setup_device_buttons(not as_active)
				self._set_scale_control(not as_active)
				self._setup_transport_buttons(as_active)
				self._setup_launch_scenes(as_active, as_enabled)
				self._setup_master_controls(as_active)
				self._set_browser_control(as_active)
				self._set_browser_button(as_active)
				self._setup_select_buttons(as_active)

			elif (self._mode_index == 1):
				"B: Mixer mode"
				"we activate the track selection, arm, and mute buttons and the launch clips buttons"
				#self._parent.log_message("Launching clips mode")
				self._setup_step_sequencer(not as_active)
				self._setup_launch_scenes(not as_active, not as_enabled)
				self._setup_master_controls(not as_active)
				self._setup_device_buttons(not as_active)
				self._set_scale_control(not as_active)
				self._setup_transport_buttons(as_active)
				self._setup_launch_clips(as_active, as_enabled)
				self._setup_track_controls(as_active)
				self._setup_select_buttons(as_active)
				self._set_browser_control(as_active)
				self._set_browser_button(as_active)

			elif (self._mode_index == 2):
				"C: Step sequencer mode"
				self._setup_launch_scenes(not as_active, not as_enabled)
				self._setup_launch_clips(not as_active,not as_enabled)
				self._setup_track_controls(not as_active)
				self._setup_master_controls(not as_active)
				self._setup_select_buttons(not as_active)
				self._setup_device_buttons(not as_active)
				self._setup_transport_buttons(not as_active)
				self._set_scale_control(not as_active)
				self._setup_step_sequencer(as_active)
				self._set_browser_control(as_active)
				self._set_browser_button(as_active)

			else:
				"D: Instrument mode"
				"the keyboard now control the selected midi instrument"
				self._setup_step_sequencer(not as_active)
				self._setup_launch_clips(not as_active,not as_enabled)
				self._setup_launch_scenes(not as_active, not as_enabled)
				self._setup_track_controls(not as_active)
				self._setup_master_controls(not as_active)
				self._setup_select_buttons(not as_active)
				self._set_browser_control(as_active)
				self._set_browser_button(as_active)
				self._setup_device_buttons(as_active)
				self._setup_transport_buttons(as_active)
				self._set_scale_control(as_active)

			self._update_session_translation()
			self._session.set_allow_update(True)
			self._previous_mode_index=self._mode_index

			#self._parent.log_message("Updated")
			

	
	def _setup_launch_scenes(self, as_active, as_enabled):
		"if as_active, we'll assignate the keyboard notes to the launch scene buttons"
		assert isinstance(as_active, type(False))

		#launch_buttons
		for scene_index in range(16):
			scene = self._session.scene(scene_index)
			if as_active:
				scene_button = self._launch_buttons[scene_index]
				scene_button.turn_off()
				scene.set_launch_button(scene_button)
			else:
				scene.set_launch_button(None)

	def _setup_launch_clips(self, as_active, as_enabled):
		"if as_active, we'll assignate the keyboard notes to the launch clip buttons"
		assert isinstance(as_active, type(False))

		#launch_buttons
		for scene_index in range(16):
			scene = self._session.scene(scene_index)
			for track_index in range(8):
				if as_active and track_index==self._selected_track_index:
					clip_button = self._launch_buttons[scene_index]
					clip_button.turn_off()
					scene.clip_slot(track_index).set_launch_button(clip_button)
				else:
					scene.clip_slot(track_index).set_launch_button(None)

	def _setup_select_buttons(self, as_active):
		"if as_active, we'll assign the pads to track selection and track control buttons"
		"pads 15 and 16 will shift and arm tha selected track"
		for index in range(8):
			select_button = self._pads[index]
			if as_active:
				if self._selected_track_index == index: 
					"we only assign the arm and mute buttons of the selected track"
					#self._parent.log_message("set arm on "+str(index))
					self._mixer.channel_strip(index).set_arm_button(select_button)
					self._mixer.channel_strip(index).set_mute_button(self._mute_button)
					self._mixer.channel_strip(index).set_solo_button(self._solo_button)
					self._mixer.channel_strip(index).set_select_button(None)
					self._mixer.channel_strip(index).set_shift_button(self._select_button)
					self._track_leds[index].send_value(127,True)
				else:
					self._mixer.channel_strip(index).set_arm_button(None)
					self._mixer.channel_strip(index).set_select_button(select_button)
					self._mixer.channel_strip(index).set_mute_button(None)
					self._mixer.channel_strip(index).set_solo_button(None)
					self._mixer.channel_strip(index).set_shift_button(None)
					self._track_leds[index].send_value(0,True)
			else:
				self._mixer.channel_strip(index).set_select_button(None)
				self._mixer.channel_strip(index).set_arm_button(None)
				self._mixer.channel_strip(index).set_mute_button(None)
				self._mixer.channel_strip(index).set_mute_button(None)
				self._mixer.channel_strip(index).set_solo_button(None)
				self._track_leds[index].turn_off()

	def _setup_transport_buttons(self, as_active):
		"if as_active, we'll assign the pads to the transport buttons"
		if as_active:
			self._transport.set_play_button(self._transport_buttons[2])
			self._transport.set_stop_button(self._transport_buttons[1])
			self._transport.set_record_button(self._transport_buttons[0])
			self._transport.set_loop_button(self._transport_buttons[3])
			self._transport.set_tempo_encoder(self._tempo_control)
			self._transport.set_undo_button(self._erase_button)
			self._transport.set_redo_button(self._copy_button)
		else:
			self._transport.set_play_button(None)
			self._transport.set_stop_button(None)
			self._transport.set_record_button(None)
			self._transport.set_loop_button(None)
			self._transport.set_tempo_encoder(None)
			self._transport.set_undo_button(None)
			self._transport.set_redo_button(None)

	def _setup_master_controls(self, as_active):
		"if as_active, we'll assign the control knobs to the master track parameters"
		if as_active:
			self._mixer.master_strip().set_volume_control(self._volume_control)
			self._mixer.master_strip().set_pan_control(self._param_controls[0])
			self._mixer.set_prehear_volume_control(self._param_controls[1])
			self._mixer.set_crossfader_control(self._param_controls[2])
			self._transport.set_seek_buttons(self._forward_button,self._rewind_button)
		else:
			self._mixer.master_strip().set_volume_control(None)
			self._mixer.master_strip().set_pan_control(None)
			self._mixer.set_prehear_volume_control(None)
			self._mixer.set_crossfader_control(None)
			self._transport.set_seek_buttons(None,None)

	def _setup_track_controls(self, as_active):
		"if as_active, we'll assign the control knobs to the master track parameters"
		if as_active:
			self._parent.log_message(self._previous_track_index)
			self._mixer.channel_strip(self._previous_track_index).set_volume_control(None)
			self._mixer.channel_strip(self._previous_track_index).set_pan_control(None)
			self._mixer.channel_strip(self._previous_track_index).set_send_controls(None)
			self._parent.log_message(self._selected_track_index)
			self._mixer.channel_strip(self._selected_track_index).set_volume_control(self._volume_control)
			self._mixer.channel_strip(self._selected_track_index).set_pan_control(self._param_controls[0])
			self._mixer.channel_strip(self._selected_track_index).set_send_controls(self._param_controls[1:])
		else:
			self._mixer.channel_strip(self._selected_track_index).set_volume_control(None)
			self._mixer.channel_strip(self._selected_track_index).set_pan_control(None)
			self._mixer.channel_strip(self._selected_track_index).set_send_controls(None)


		
	def _setup_device_buttons(self, as_active):
		"if as_active, we'll assign the pads to the device selection and activation buttons"
		if as_active:
			self._device.set_parameter_controls(self._param_controls)
			self._device.set_bank_nav_buttons(self._rewind_button, self._forward_button)
		else:
			self._device.set_parameter_controls(None)
			self._device.set_bank_nav_buttons(None, None)


	def _init_session(self):
		for scene_index in range(len(self._launch_buttons)):
			scene = self._session.scene(scene_index)
			scene.set_triggered_value(127)
			scene.name = 'Scene_' + str(scene_index)
			for track_index in range(8):
				"TODO: this still doesn't light the launch clip buttons when supposed to..."
				clip_slot = scene.clip_slot(track_index)
				clip_slot.set_triggered_to_play_value(127)
				clip_slot.set_triggered_to_record_value(127)
				clip_slot.set_stopped_value(0)
				clip_slot.set_started_value(127)
				clip_slot.set_recording_value(127)
				clip_slot.name = str(track_index) + '_Clip_Slot_' + str(scene_index)

	def _mode_value(self, value, sender):
		"method called each time the value of the mode selection changed"
		"it's been momentary overriden to avoid dysfunctionnement in the framework method"
		new_mode = self._modes_buttons.index(sender)
		if sender.is_momentary():
			#self._parent.log_message(sender.message_identifier())
			if value > 0:
				#self._parent.log_message("value = "+str(value))
				mode_observer = MomentaryModeObserver()
				mode_observer.set_mode_details(new_mode, self._controls_for_mode(new_mode), self._get_public_mode_index)
				self._modes_heap.append((new_mode, sender, mode_observer))
				self._update_mode()
			elif self._modes_heap[-1][1] == sender and not self._modes_heap[-1][2].is_mode_momentary():
				#self._parent.log_message("sender trouve")
				self.set_mode(new_mode)
			else:
				#TODO: comprendre comment le framework est sense fonctionner et remplacer supprimer cet modif du framework
				self.set_mode(new_mode)
				self._update_mode()
		else:
			#self._parent.log_message("boutton pas trouve")
			self.set_mode(new_mode)

	def _setup_step_sequencer(self, as_active):
		if(self._stepseq!=None):
				if as_active: 
					self._stepseq._force_update = True
					self._stepseq._is_active = True
					self._stepseq.set_enabled(True)
					self._stepseq._on_notes_changed()
					self._stepseq._update_seq_buttons()
				else:
					self._stepseq._is_active = False
					self._stepseq.set_enabled(False)

	def _set_browser_control(self, as_active):
		self._browser_control.remove_value_listener(self._browser_control_value)
		if as_active:
			self._browser_control.add_value_listener(self._browser_control_value)



	def _browser_control_value(self, value):
		if value != 64:
			all_scenes = self.song().scenes
			selected_scene = self.song().view.selected_scene
			selected_scene_index = list(all_scenes).index(selected_scene)
			new_selected_scene_index = max(0, min(selected_scene_index + (value-64), len(list(all_scenes))-1) )
			self.song().view.selected_scene = all_scenes[new_selected_scene_index]
			session_offset = self._session.scene_offset()
			if new_selected_scene_index > session_offset + 15:
				self._session.set_offsets(self._session.track_offset(), new_selected_scene_index - 15)
			if new_selected_scene_index < session_offset:
				self._session.set_offsets(self._session.track_offset(), new_selected_scene_index)

	def _set_browser_button(self, as_active):
		self._browser_button.remove_value_listener(self._browser_button_value)
		if as_active:
			self._browser_button.add_value_listener(self._browser_button_value)

	def _browser_button_value(self, value):
		if value != 0:
			if self._mode_index == 2:
				self.song().view.highlighted_clip_slot.fire()
			else:
				self.song().view.selected_scene.fire_as_selected()



	def _set_scale_control(self, as_active):
		self._divide_control.remove_value_listener(self._translation_selector._scale_index_value)
		self._move_control.remove_value_listener(self._translation_selector._scale_offset_value)
		if as_active:
			self._divide_control.add_value_listener(self._translation_selector._scale_index_value)
			self._move_control.add_value_listener(self._translation_selector._scale_offset_value)

	def _update_session_translation(self):
		if self._mode_index == 0 or self._mode_index == 1:
			if self._translation_selector.mode():
				self._session.set_offsets(8,self._session.scene_offset())
			else:
				self._session.set_offsets(0,self._session.scene_offset())

	def on_selected_track_changed(self):
		all_tracks = ((self.song().tracks + self.song().return_tracks))
		selected_track = self.song().view.selected_track
		self._previous_track_index = self._selected_track_index
		self._selected_track_index = list(all_tracks).index(selected_track)
		self.update()