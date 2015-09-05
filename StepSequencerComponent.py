# http://remotescripts.blogspot.com
"""
8*8 Step Sequencer for launchpad

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

based on APC stepsquencer by by Hanz Petrov, itslef based on  
LiveControl Sequencer module by ST8 <http://monome.q3f.org>
and the CS Step Sequencer Live API example by Cycling '74 <http://www.cycling74.com>
"""

import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.SessionComponent import SessionComponent
from _Framework.ButtonMatrixElement import ButtonMatrixElement
import time



class StepSequencerComponent(ControlSurfaceComponent):
	__module__ = __name__
	__doc__ = ' Generic Step Sequencer Component '

	def __init__(self, parent, seq_buttons,pads, translate_button, select_button, mute_button, solo_button, transport_buttons, forward_button, rewind_button, pattern_leds):
		ControlSurfaceComponent.__init__(self)
				
		self._is_active = False
		self._parent = parent
		self._mode = 1
		self._step_offset = 0
		self._drum_group_device = None
		self._all_drum_pads = []

		#fill the cache
		self._grid_buffer = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
		self._grid_back_buffer = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
		


		#buttons
		self._seq_buttons = None
		self._pads = None
		self._translate_button = None
		self._select_button = None
		self._mute_button = None
		self._solo_button = None
		self._record_button = None
		self._play_button = None
		self._stop_button = None
		self._forward_button = None
		self._rewind_button = None
		self._pattern_leds = None

		self._width = 0
		self._height = 0
		self._selected_pad = 0

		#notes
		self._bank_index = 0 #bank index;
		self._key_indexes=[0,0,0,0,0,0,0,0]
		self._scale=[True,False,True,False,True,True,False,True,False,True,False,True]#which notes to display in scale mode.
		self._key_indexes[0] = 36 #C1 Note
		
		self._sequencer_clip = None
		self._clip_notes = []
		self._force_update = True
		self._display_bank = False
		self._display_bank_time = time.time()

		#quantization
		self._quantization = 1/4.0

		
		#loop 
		self._loop_length = None
		self._loop_start = None
		self._loop_end = None
		
		#fold
		self._is_fold = False
		self._is_scale_fold = False

		#buttons shifted
		self._translate_button_shifted = False
		self._select_button_shifted = False
		self._mute_button_shifted = False
		self._solo_button_shifted = False
		self._record_button_shifted = False
		self._play_button_shifted = False
		self._stop_button_shifted = False
		self._is_lane_muted = [False for i in range(128)]
		self._is_solo_lane = [False for i in range(128)]
		self._solo_lanes_count = 0



		self.set_seq_buttons(seq_buttons)
		self.set_pads(pads)
		self.set_translate_button(translate_button)
		self.set_select_button(select_button)
		self.set_mute_button(mute_button)
		self.set_solo_button(solo_button)
		self.set_record_button(transport_buttons[0])
		self.set_play_button(transport_buttons[2])
		self.set_stop_button(transport_buttons[1])
		self.set_forward_button(forward_button)
		self.set_rewind_button(rewind_button)
		self.set_pattern_leds(pattern_leds)

		self._compute_key_indexes(True)
		self.update()


	_active_instances = []
	
	
	def unlink(self):
		if self in StepSequencerComponent._active_instances:
			StepSequencerComponent._active_instances.remove(self)
	
	def link_with_step_offset(self, step_offset):
		assert (step_offset >= 0)
		StepSequencerComponent._active_instances.append(self)
		self._step_offset = step_offset


	def disconnect(self):
		self._parent = None
		self._seq_buttons = None
		self._pads = None
		self._translate_button = None
		self._sequencer_clip = None


	def update(self):
		if self._is_active:
			track = self.song().view.selected_track
			self.on_clip_slot_changed()
			self._update_translate_button()
			self._update_select_button()
			self._update_mute_button()
			self._update_solo_button()
			self._update_record_button()
			self._update_play_button()
			self._update_stop_button()
			self._update_pattern_leds()
			self._on_loop_changed()
			self._compute_key_indexes()
			self._update_seq_buttons()
			self._update_pads()
			self._update_pattern_leds()
			self._on_playing_status_changed()
			if self._sequencer_clip !=None and self._sequencer_clip.is_midi_clip:
				if ((not self.application().view.is_view_visible('Detail')) or (not self.application().view.is_view_visible('Detail/Clip'))):
					self.application().view.show_view('Detail')
					self.application().view.show_view('Detail/Clip')

	def on_enabled_changed(self):
		if self.is_enabled():
			self.enable_pads(True)
			self.enable_seq_buttons(True)
		else:
			self.enable_pads(False)
			self.enable_seq_buttons(False)
		self.update()

	def on_selected_track_changed(self):
		all_tracks = ((self.song().tracks + self.song().return_tracks))
		self._selected_track = self.song().view.selected_track
		self._selected_track_index = list(all_tracks).index(self._selected_track)
		self.update()

	def on_track_list_changed(self):
		self.update()

	def on_selected_scene_changed(self):
		self.update()

	def on_scene_list_changed(self):
		self.update()



	def on_clip_slot_changed(self):
		#select drumrack device
		if self.song().view.selected_track != None:
			track = self.song().view.selected_track
			if(track.devices != None and len(track.devices)>0):
				device = track.devices[0];
				if(device.can_have_drum_pads and device.has_drum_pads):
					self._drum_group_device  = device
					#self._parent._parent.log_message(str(len(self._drum_group_device.drum_pads)))
					#for index in range(len(self._drum_group_device.drum_pads)):
					#	if(self._drum_group_device.drum_pads[index].chains):
					#		self._parent._parent.log_message(str(index))
				else:
					self._drum_group_device  = None
			else:
				self._drum_group_device  = None
		else:
			self._drum_group_device  = None
			#select clip
		if self.song().view.highlighted_clip_slot != None:
			
			clip_slot = self.song().view.highlighted_clip_slot
			if clip_slot.has_clip: # and clip_slot.clip.is_midi_clip:
				if self._sequencer_clip != clip_slot.clip:
					#remove listeners
					if self._sequencer_clip != None:
						if self._sequencer_clip.is_midi_clip:
							self._parent._parent.log_message(dir(self._sequencer_clip.is_midi_clip))
							if self._sequencer_clip.notes_has_listener(self._on_notes_changed):
								self._sequencer_clip.remove_notes_listener(self._on_notes_changed)
						if self._sequencer_clip.playing_status_has_listener(self._on_playing_status_changed):
							self._sequencer_clip.remove_playing_status_listener(self._on_playing_status_changed) 
						if self._sequencer_clip.loop_start_has_listener(self._on_loop_changed):
							self._sequencer_clip.remove_loop_start_listener(self._on_loop_changed) 
						if self._sequencer_clip.loop_end_has_listener(self._on_loop_changed):
							self._sequencer_clip.remove_loop_end_listener(self._on_loop_changed)							   
					#update reference
					
					self._sequencer_clip = clip_slot.clip
					self._loop_start = clip_slot.clip.loop_start
					self._loop_end = clip_slot.clip.loop_end
					self._loop_length = self._loop_end - self._loop_start  
					self._bank_index = 0
					self._update_notes()
					self._update_play_button()
					self._on_loop_changed()
					
					#add listeners
					if self._sequencer_clip.is_midi_clip:
						if self._sequencer_clip.notes_has_listener(self._on_notes_changed):
							self._sequencer_clip.remove_notes_listener(self._on_notes_changed)
						self._sequencer_clip.add_notes_listener(self._on_notes_changed)		  
					if self._sequencer_clip.playing_status_has_listener(self._on_playing_status_changed):
						self._sequencer_clip.remove_playing_status_listener(self._on_playing_status_changed) 
					self._sequencer_clip.add_playing_status_listener(self._on_playing_status_changed)
					if self._sequencer_clip.loop_start_has_listener(self._on_loop_changed):
						self._sequencer_clip.remove_loop_start_listener(self._on_loop_changed)
					self._sequencer_clip.add_loop_start_listener(self._on_loop_changed)
					if self._sequencer_clip.loop_end_has_listener(self._on_loop_changed):
						self._sequencer_clip.remove_loop_end_listener(self._on_loop_changed)							   
					self._sequencer_clip.add_loop_end_listener(self._on_loop_changed)
			else:
				self._sequencer_clip=None
		else:
			self._sequencer_clip=None
					

	def _on_loop_changed(self): #loop start/end listener
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None:
				self._loop_length = self._sequencer_clip.loop_end - self._sequencer_clip.loop_start
				self._loop_start = self._sequencer_clip.loop_start
				self._loop_end = self._sequencer_clip.loop_end
				self._show_msg_callback(str(self._loop_length))



#NOTES CHANGES
	def _on_notes_changed(self): #notes changed listener
		if self.is_enabled() and self._is_active:
			self._update_notes()
			#self._parent._parent.schedule_message(1, self._update_notes)
			#Live bug: delay is required to avoid blocking mouse drag operations in MIDI clip view


	def _update_notes(self):
		"""LiveAPI clip.get_selected_notes returns a tuple of tuples where each inner tuple represents a note.
		The inner tuple contains pitch, time, duration, velocity, and mute state.
		e.g.: (46, 0.25, 0.25, 127, False)"""
		#if self.is_enabled() and self._is_active:
		if self._sequencer_clip!= None and self._sequencer_clip.is_midi_clip:
			self._sequencer_clip.select_all_notes()
			note_cache = self._sequencer_clip.get_selected_notes()
			self._sequencer_clip.deselect_all_notes()
			if self._clip_notes != note_cache:
				self._clip_notes = note_cache
				self._compute_key_indexes()
				self._update_seq_buttons()
				self._update_pads()

#PLAY POSITION

	def _on_playing_status_changed(self): #playing status changed listener
		if self._is_active:#self.is_enabled() and self._is_active:
			if self._sequencer_clip != None:
				if self._sequencer_clip.is_playing:
					if self._sequencer_clip.playing_position_has_listener(self._on_playing_position_changed):
						self._sequencer_clip.remove_playing_position_listener(self._on_playing_position_changed)
					self._sequencer_clip.add_playing_position_listener(self._on_playing_position_changed)
				else:
					if self._sequencer_clip.playing_position_has_listener(self._on_playing_position_changed):
						self._sequencer_clip.remove_playing_position_listener(self._on_playing_position_changed)
			self._update_play_button()

	def _on_playing_position_changed(self): #playing position changed listener
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None:
				"""LiveAPI clip.playing_position: Constant access to the current playing position of the clip.
				The returned value is the position in beats for midi and warped audio clips,
				or in seconds for unwarped audio clips. Stopped clips will return 0."""
				position = self._sequencer_clip.playing_position #position in beats (1/4 notes in 4/4 time)
				bank = int(position / self._quantization / self._width) # 0.25 for 16th notes;  0.5 for 8th notes
				self._update_seq_buttons()
				self._update_pads()

# MATRIX
	def _update_seq_buttons(self): #step grid LEDs are updated here
		if self.is_enabled() and self._is_active and self._seq_buttons != None:
			for x in range(self._width):
				self._grid_back_buffer[x] = 0

			#update back buffer
			if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
				if self._sequencer_clip.is_midi_clip:
					play_position = self._sequencer_clip.playing_position #position in beats (1/4 notes in 4/4 time)
					play_x_position = int(play_position / self._quantization) #position in beats (1/4 notes in 4/4 time)
					 
					#CLIP NOTES
					for note in self._clip_notes:
						note_key = note[0]
						note_position = note[1] #position in beats; range is 0.x to 15.x for 4 measures in 4/4 time (equivalent to 1/4 notes)
						note_grid_x_position = int(note_position / self._quantization) #stepped postion at quantize resolution
						note_muted = note[4]
						if note_key == self._key_indexes[self._selected_pad] and note_position >= self._bank_index * self._width * self._quantization and note_position <= (self._bank_index+1) * self._width * self._quantization:
							note_grid_x_position -= self._bank_index * self._width
							if note_muted:
								self._grid_back_buffer[note_grid_x_position] = 0
							else:
								self._grid_back_buffer[note_grid_x_position] = 127

					# METRONOME : add play positition in amber	
					if(True):
						if self._sequencer_clip.is_playing  and play_position >= self._bank_index * self._width * self._quantization and play_position <= (self._bank_index+1) * self._width * self._quantization:
							play_x_position -= self._bank_index * self._width
							if self._grid_back_buffer[play_x_position] == 127:
								self._grid_back_buffer[play_x_position] = 0
							else:
								self._grid_back_buffer[play_x_position] = 127
							#self._parent._parent.log_message(play_position2)
							#self._parent._parent.log_message(play_x_position2)
					for x in range(self._width):
						if(self._grid_back_buffer[x]!=self._grid_buffer[x] or self._force_update):
							self._grid_buffer[x] = self._grid_back_buffer[x]
							self._seq_buttons[x].send_value(self._grid_buffer[x])
							#self._parent._parent.log_message(str(x)+" => "+str(self._grid_back_buffer[x]))

	def _seq_buttons_value(self, value, sender): #matrix buttons listener
		if self.is_enabled() and self._is_active:
			if value != 0:
				#self._parent._parent.log_message(str(x)+"."+str(y)+"."+str(value)+" "+"scheduled")
				#self._parent._parent.schedule_message(1, self._matrix_value_message,[value,x,y,is_momentary])
				self._seq_buttons_value_message(value,sender)
				
	def _seq_buttons_value_message(self, value, sender): #value, x, y, is_momentary): #matrix buttons listener
		x = list(self._seq_buttons).index(sender)
		#self._parent._parent.log_message("got: x:"+ str(x)+" y:"+str(y))
		#self._parent._parent.log_message(str(x)+"."+str(value)+" "+ "processing"+"."+str(self.is_enabled())+str(self._is_active))
	
		
		"""(pitch, time, duration, velocity, mute state)
		e.g.: (46, 0.25, 0.25, 127, False)"""
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None and self._sequencer_clip.is_midi_clip:
				#self._parent._parent.log_message(self._sequencer_clip)
				if value != 0:
					#TODO:add quantization and offset
					pitch = self._key_indexes[self._selected_pad]
					time = (x + (self._bank_index * self._width))* self._quantization#convert position to time in beats
					#self._parent._parent.log_message(time)

					if self._sequencer_clip!= None and self._sequencer_clip.is_midi_clip:
							self._sequencer_clip.select_all_notes()
							note_cache = self._sequencer_clip.get_selected_notes()
							if self._clip_notes != note_cache:
								self._clip_notes = note_cache

					note_cache = list(self._clip_notes)
					for note in note_cache:
						if time == note[1] and pitch == note[0]:
							#self._parent._parent.log_message(note)
							note_cache.remove(note)
							break
					else:
						note_cache.append([pitch, time, 0.25, 127, False])
					#self._parent._parent.log_message("One remplace ")
					self._sequencer_clip.select_all_notes()
					self._sequencer_clip.replace_selected_notes(tuple(note_cache))


	def set_seq_buttons(self, buttons):
		if (buttons != self._seq_buttons):
			if self._seq_buttons != None:
				for index in range(len(self._seq_buttons)):
					self._seq_buttons[index].remove_value_listener(self._seq_buttons_value)
			self._seq_buttons = buttons
			if self._seq_buttons != None:
				for index in range(len(buttons)):
					if (self._seq_buttons[index] != None):
						self._seq_buttons[index].add_value_listener(self._seq_buttons_value, True)
				self._width = len(buttons)
			self.update()

	def set_pads(self, buttons):
		if (buttons != self._pads):
			if self._pads != None:
				for index in range(len(self._pads)):
					self._pads[index].remove_value_listener(self._pads_value)
			self._pads = buttons
			if self._pads != None:
				for index in range(len(buttons)):
					if (self._pads[index] != None):
						self._pads[index].add_value_listener(self._pads_value, True)
				self._height = len(buttons)
			self.update()

	def enable_seq_buttons(self, as_enabled):
		if self._seq_buttons != None:
			if as_enabled:
				for button in self._seq_buttons:
					button.add_value_listener(self._seq_buttons_value, True)
			else:
				for button in self._seq_buttons:
					button.remove_value_listener(self._seq_buttons_value)

	def enable_pads(self, as_enabled):
		if self._seq_buttons != None:
			if as_enabled:
				for button in self._pads:
					button.add_value_listener(self._pads_value, True)
			else:
				for button in self._pads:
					button.remove_value_listener(self._pads_value)

	def _pads_value(self, value, sender): #matrix buttons listener
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None and self._sequencer_clip.is_midi_clip:
				if value != 0:
					x = list(self._pads).index(sender)
					if self._select_button_shifted:
							self._selected_pad = x
							self.update()
					elif self._mute_button_shifted:
						pitch_to_mute = self._key_indexes[x]
						self._is_lane_muted[pitch_to_mute] = not self._is_lane_muted[pitch_to_mute]
						self._sequencer_clip.select_all_notes()
						self._update_mute_value()
					elif self._solo_button_shifted:
						pitch_to_solo = self._key_indexes[x]
						if self._is_solo_lane[pitch_to_solo]:
							self._is_solo_lane[pitch_to_solo] = False
							self._solo_lanes_count -= 1
						else:
							self._is_solo_lane[pitch_to_solo] = True
							self._solo_lanes_count += 1
						self._update_solo_value()


	def _update_pads(self): #step grid LEDs are updated here
		if self.is_enabled() and self._is_active and self._pads != None:
				if self._select_button_shifted:
					self.enable_pads(True)
					for x in range(self._height):
						self._pads[x].send_value(127*(x==self._selected_pad))
				elif self._mute_button_shifted:
					self.enable_pads(True)
					for x in range(self._height):
						self._pads[x].send_value(127*self._is_lane_muted[self._key_indexes[x]])
				elif self._solo_button_shifted:
					self.enable_pads(True)
					for x in range(self._height):
						self._pads[x].send_value(127*self._is_solo_lane[self._key_indexes[x]])
				else:
					self.enable_pads(False)
					for x in range(self._height):
						self._pads[x].send_value(0)

	def set_translate_button(self, button):
		if (button != self._translate_button):
			if (self._translate_button != None):
				self._translate_button.remove_value_listener(self._translation_value)
			self._translate_button = button
			if (self._translate_button != None):
				self._translate_button.add_value_listener(self._translation_value)
			##self._rebuild_callback()
			self.update()

	def _translation_value(self, value):
		if self.is_enabled() and self._is_active:
			if (value != 0):
				if not self._translate_button_shifted:
					self._translate_button_shifted = True
					self._key_indexes[0] += 8
				else:
					self._translate_button_shifted = False
					self._key_indexes[0] -= 8

				self._compute_key_indexes(False,True,False)
				for index in range(len(self._pads)):
					self._pads[index].set_identifier(self._key_indexes[index])
				self._update_seq_buttons()
				self._update_pads()
				self._update_translate_button()

	def _update_translate_button(self):
		if self.is_enabled() and self._is_active:
			self._translate_button.set_light(self._translate_button_shifted)

	def set_select_button(self, button):
		if (button != self._select_button):
			if (self._select_button != None):
				self._select_button.remove_value_listener(self._select_button_value)
			self._select_button = button
			if (self._select_button != None):
				self._select_button.add_value_listener(self._select_button_value)
			##self._rebuild_callback()
			self.update()

	def _select_button_value(self, value):
		if self.is_enabled() and self._is_active:
			if self._select_button_shifted:
				self._select_button_shifted = False
			else:
				self._select_button_shifted = True
			self._update_pads()
			self._update_select_button()

	def _update_select_button(self):
		if self.is_enabled() and self._is_active:
			self._select_button.set_light(self._select_button_shifted)
			
	def set_record_button(self, button):
		if (button != self._record_button):
			if (self._record_button != None):
				self._record_button.remove_value_listener(self._record_button_value)
			self._record_button = button
			if (self._record_button != None):
				self._record_button.add_value_listener(self._record_button_value)
			##self._rebuild_callback()
			self.update()

	def _record_button_value(self, value):
		if self.is_enabled() and self._is_active:
			if self._record_button_shifted:
				self._record_button_shifted = False
			else:
				self._record_button_shifted = True
				clip_slot = self.song().view.highlighted_clip_slot
				if clip_slot.has_clip:
					clip_slot.delete_clip()
				else:
					clip_slot.create_clip(4)


			self.update()
			self._update_record_button()

	def _update_record_button(self):
		if self.is_enabled() and self._is_active:
			clip_slot = self.song().view.highlighted_clip_slot
			self._record_button.set_light(clip_slot.has_clip)
						
	def set_play_button(self, button):
		if (button != self._play_button):
			if (self._play_button != None):
				self._play_button.remove_value_listener(self._play_button_value)
			self._play_button = button
			if (self._play_button != None):
				self._play_button.add_value_listener(self._play_button_value)
			##self._rebuild_callback()
			self.update()

	def _play_button_value(self, value):
		if self.is_enabled() and self._is_active:
			if self._play_button_shifted:
				self._play_button_shifted = False
			else:
				self._play_button_shifted = True
				clip_slot = self.song().view.highlighted_clip_slot
				clip_slot.fire()
			self.update()

	def _update_play_button(self):
		if self.is_enabled() and self._is_active:
			clip_slot = self.song().view.highlighted_clip_slot
			self._play_button.set_light(clip_slot.is_playing)

	def set_stop_button(self, button):
		if (button != self._stop_button):
			if (self._stop_button != None):
				self._stop_button.remove_value_listener(self._stop_button_value)
			self._stop_button = button
			if (self._stop_button != None):
				self._stop_button.add_value_listener(self._stop_button_value)
			##self._rebuild_callback()
			self.update()

	def _stop_button_value(self, value):
		if self.is_enabled() and self._is_active:
			if self._stop_button_shifted:
				self._stop_button_shifted = False
			else:
				self._stop_button_shifted = True
				clip_slot = self.song().view.highlighted_clip_slot
				clip_slot.stop()
			self.update()
			self._update_stop_button()

	def _update_stop_button(self):
		if self.is_enabled() and self._is_active:
			clip_slot = self.song().view.highlighted_clip_slot
			self._stop_button.set_light(self._stop_button_shifted)

	def set_forward_button(self, button):
		if (button != self._forward_button):
			if (self._forward_button != None):
				self._forward_button.remove_value_listener(self._forward_button_value)
			self._forward_button = button
			if (self._forward_button != None):
				self._forward_button.add_value_listener(self._forward_button_value)
			##self._rebuild_callback()
			self.update()

	def _forward_button_value(self, value):
		if self.is_enabled() and self._is_active and value != 0:
			if self._select_button_shifted:
				if self._loop_length < 4*self._width*self._quantization:
					self._loop_end += self._width * self._quantization
					self._sequencer_clip.loop_end = self._loop_end
			elif (self._bank_index+1)*self._width*self._quantization < self._loop_end:
				self._bank_index += 1
			self.update()

	def set_rewind_button(self, button):
		if (button != self._rewind_button):
			if (self._rewind_button != None):
				self._rewind_button.remove_value_listener(self._rewind_button_value)
			self._rewind_button = button
			if (self._rewind_button != None):
				self._rewind_button.add_value_listener(self._rewind_button_value)
			##self._rebuild_callback()
			self.update()

	def _rewind_button_value(self, value):
		if self.is_enabled() and self._is_active and value != 0:
			if self._select_button_shifted:
				if self._loop_length > self._width*self._quantization:
					self._loop_end -= self._width * self._quantization
					self._sequencer_clip.loop_end = self._loop_end
			elif self._bank_index >= 1:
				self._bank_index -= 1
			self.update()

	def set_pattern_leds(self, leds):
		if (leds != self._pattern_leds):
			self._pattern_leds = leds
			self.update()

	def _update_pattern_leds(self):
		for index in range(len(self._pattern_leds)):
			self._pattern_leds[index].send_value(127*(index==self._bank_index)	, True)

	def set_mute_button(self, button):
		if (button != self._mute_button):
			if (self._mute_button != None):
				self._mute_button.remove_value_listener(self._mute_button_value)
			self._mute_button = button
			if (self._mute_button != None):
				self._mute_button.add_value_listener(self._mute_button_value)
			##self._rebuild_callback()
			self.update()

	def _mute_button_value(self, value):
		if self.is_enabled() and self._is_active:
			if (value != 0):
				if self._mute_button_shifted:
					self._mute_button_shifted = False
					self._unmute_all()
				else:
					self._mute_button_shifted = True
					self._solo_button_shifted = False
					self._update_mute_value()

				self._update_pads()
				self._update_mute_button()
				self._update_solo_button()

	def _unmute_all(self):
		if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
			self._sequencer_clip.select_all_notes()
			note_cache = self._sequencer_clip.get_selected_notes()
			if self._clip_notes != note_cache:
				self._clip_notes = note_cache
			note_cache = list(self._clip_notes)
			notes_changed = 0
			for note in self._clip_notes:
				notes_changed = notes_changed + 1
				note_to_mute = note
				note_cache.remove(note)
				note_cache.append([note_to_mute[0], note_to_mute[1], note_to_mute[2], note_to_mute[3], False])
			if notes_changed>0:
				self._sequencer_clip.select_all_notes()
				self._sequencer_clip.replace_selected_notes(tuple(note_cache))
				self.update()

	def _update_mute_value(self):
		if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
			self._sequencer_clip.select_all_notes()
			note_cache = self._sequencer_clip.get_selected_notes()
			if self._clip_notes != note_cache:
				self._clip_notes = note_cache
			note_cache = list(self._clip_notes)
			notes_changed = 0
			for note in self._clip_notes:
				notes_changed = notes_changed + 1
				note_to_mute = note
				note_cache.remove(note)
				note_cache.append([note_to_mute[0], note_to_mute[1], note_to_mute[2], note_to_mute[3], self._is_lane_muted[note_to_mute[0]]])
			if notes_changed>0:
				self._sequencer_clip.select_all_notes()
				self._sequencer_clip.replace_selected_notes(tuple(note_cache))
				self.update()

	def _update_mute_button(self):
		if self.is_enabled() and self._is_active:
			self._mute_button.set_light(self._mute_button_shifted)

	def set_solo_button(self, button):
		if (button != self._solo_button):
			if (self._solo_button != None):
				self._solo_button.remove_value_listener(self._solo_button_value)
			self._solo_button = button
			if (self._solo_button != None):
				self._solo_button.add_value_listener(self._solo_button_value)
			##self._rebuild_callback()
			self.update()

	def _solo_button_value(self, value):
		if self.is_enabled() and self._is_active:
			if (value != 0):
				if self._solo_button_shifted:
					self._solo_button_shifted = False
					self._unmute_all()
				else:
					self._solo_button_shifted = True
					self._mute_button_shifted = False
					self._update_solo_value()
				self._update_pads()
				self._update_solo_button()
				self._update_mute_button()

	def _update_solo_button(self):
		if self.is_enabled() and self._is_active:
			self._solo_button.set_light(self._solo_button_shifted)

	def _update_solo_value(self):
		if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
			self._sequencer_clip.select_all_notes()
			note_cache = self._sequencer_clip.get_selected_notes()
			if self._clip_notes != note_cache:
				self._clip_notes = note_cache
			note_cache = list(self._clip_notes)
			notes_changed = 0
			if self._solo_lanes_count == 0:
				for note in self._clip_notes:
					notes_changed = notes_changed + 1
					note_to_mute = note
					note_cache.remove(note)
					note_cache.append([note_to_mute[0], note_to_mute[1], note_to_mute[2], note_to_mute[3], False])
			else:
				for note in self._clip_notes:
					notes_changed = notes_changed + 1
					note_to_mute = note
					note_cache.remove(note)
					note_cache.append([note_to_mute[0], note_to_mute[1], note_to_mute[2], note_to_mute[3], not self._is_solo_lane[note[0]]])
			if notes_changed>0:
				self._sequencer_clip.select_all_notes()
				self._sequencer_clip.replace_selected_notes(tuple(note_cache))
				self.update()

	def _compute_key_indexes(self,force=False,up=True,down=True):
				
		if (self._is_fold or self._is_scale_fold) and not self._scale_fold_shift:
			if force:
				#when switching to fold mode 
				key_index=self._key_indexes[0] #use previous base key
				new_key_index = key_index #set default value if not match found
				#find base note
				inc=0
				found_base_note=False
				while not found_base_note and (key_index+inc<=127 or key_index-inc>=0):
					if key_index+inc<=127 and up:
						#look upwards
						if self._is_fold and self._is_used(key_index+inc) or self._is_scale_fold and self._scale[(key_index+inc)%12]:
							new_key_index=key_index+inc
							found_base_note=True
							#self._parent._parent.log_message("found base note: +"+str(inc))
					if key_index-inc>=0 and down:
						#look downwards
						if self._is_fold and self._is_used(key_index-inc) or self._is_scale_fold and self._scale[(key_index-inc)%12]:
							new_key_index=key_index-inc
							found_base_note=True
							#self._parent._parent.log_message("found base note: -"+str(inc))
					inc=inc+1
					
				self._key_indexes[0]=new_key_index #set found value
				#fill in the 7 other lanes with notes
				for i in range(self._height-1):
					key_index=self._key_indexes[i+1 -1] +1 #set base for search
					new_key_index=key_index # set an initial value if no match found
					found_other_note=False
					inc=0
					while not found_other_note and (key_index+inc<127):
						if self._is_fold and self._is_used(key_index+inc) or self._is_scale_fold and self._scale[(key_index+inc)%12]:
							new_key_index=key_index+inc
							found_other_note=True
							found_base_note=True
							#self._parent._parent.log_message("found note"+str(i+1)+": +"+str(inc))
						if not found_base_note:
							found_other_note=True
							new_key_index=key_index+inc
							#self._parent._parent.log_message("found note"+str(i+1)+": +"+str(inc))
						inc=inc+1
					self._key_indexes[i+1]=new_key_index #set found value
					
		elif (self._drum_group_device!=None):
			i = 0
			for index in range(len(self._drum_group_device.drum_pads)):
				if(index>=self._key_indexes[0]):
					if(self._drum_group_device.drum_pads[index].chains):
						if(i<len(self._key_indexes)):
							#self._parent._parent.log_message(str(index))
							self._key_indexes[i] = index
						i = i + 1
						#fill in empty slots
			for j in range(i,i<len(self._key_indexes)):
				self._key_indexes[i]=-1

		else:
			#when switching to unfold mode
			new_key_index=self._key_indexes[0]
			for i in range(self._height): # set the 8 lanes incrementally
				self._key_indexes[i]=new_key_index+i
		
		#self._parent._parent.log_message("keys : ")
		#for i in range(8):
		#	self._parent._parent.log_message(str(i)+" : "+str(self._key_indexes[i]))
		

	def _is_used(self,key):
		if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
			if self._sequencer_clip.is_midi_clip:
				if self._drum_group_device!=None:
					#return False if drum slot is empty
					if self._drum_group_device.drum_pads[key].chains==False:
						return False
				for note in self._clip_notes:
					if note[0]==key: #key: 0-127 MIDI note #
						return(True)
			else:
				return(False)
		return(False)
		

