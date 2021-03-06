#
#   engine_output.py - Display USI Engine Output Window
#
#   This file is part of gshogi   
#
#   gshogi is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   gshogi is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with gshogi.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import gobject
import os
import pango

import utils
from constants import *

class Engine_Output:

    engine_output_ref = None

    def __init__(self):        
        self.game = utils.get_game_ref()
        glade_dir = self.game.get_glade_dir()
        self.glade_file = os.path.join(glade_dir, "engine_output.glade")       
        Engine_Output.engine_output_ref = self       
       
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.glade_file)
        self.builder.connect_signals(self)

        self.window = self.builder.get_object('engine_output_window')
        self.tv = [gtk.TextView(), gtk.TextView()]
        self.tv[0] = self.builder.get_object('engine_output_textview1')
        self.tv[1] = self.builder.get_object('engine_output_textview2')
        self.tv[0].set_editable(False)
        self.tv[1].set_editable(False)

        tabs =  pango.TabArray(4, True)
        tabs.set_tab(0, pango.TAB_LEFT, 40)
        tabs.set_tab(1, pango.TAB_LEFT, 160)
        tabs.set_tab(2, pango.TAB_LEFT, 230)
        tabs.set_tab(3, pango.TAB_LEFT, 280)

        self.tv[0].set_tabs(tabs)
        self.tv[1].set_tabs(tabs)

        self.tb = [gtk.TextBuffer(), gtk.TextBuffer()] 
        self.tb[0] = self.tv[0].get_buffer()
        self.tb[1] = self.tv[1].get_buffer() 
        #self.tb[0].set_text('')
        #self.tb[1].set_text('')               

        self.nps_lbl = [gtk.Label(), gtk.Label()]
        self.nps_lbl[0] = self.builder.get_object('engine_output_nodes_lbl1')
        self.nps_lbl[1] = self.builder.get_object('engine_output_nodes_lbl2')
        
        self.engine_name_lbl = [gtk.Label(), gtk.Label()]
        self.engine_name_lbl[0] = self.builder.get_object('engine_output_engine_name_lbl1')
        self.engine_name_lbl[1] = self.builder.get_object('engine_output_engine_name_lbl2')
       
        self.ponder_move_lbl = [gtk.Label(), gtk.Label()]
        self.ponder_move_lbl[0] = self.builder.get_object('engine_output_ponder_move_lbl1')
        self.ponder_move_lbl[1] = self.builder.get_object('engine_output_ponder_move_lbl2')       

        self.currmove_lbl = [gtk.Label(), gtk.Label()]
        self.currmove_lbl[0] = self.builder.get_object('engine_output_currmove_lbl1')
        self.currmove_lbl[1] = self.builder.get_object('engine_output_currmove_lbl2')
 
        #self.window.show_all() 


    # user has closed the window
    # just hide it
    def delete_event(self, widget, event):        
        self.window.hide()
        return True  # do not propagate to other handlers        


    def format_time(self, ztime):
        if ztime == '':
            return ztime        
        try:
            ms = int(ztime)
        except:
            return ztime
        secs = ms / 1000        
        mins = 0
        if secs > 60:
            mins = secs / 60
            secs = secs - mins * 60
        smins = str(mins)
        if mins < 10:
            smins = '0' + smins
        ssecs = str(secs)
        if secs < 10:
            ssecs = '0' + ssecs
        return smins + ':' + ssecs
        

    def add_to_log(self, side, engine_name, msg):
        # Write to either the black or white split pane
        if side == 'b':
            idx = 1   # bottom pane for black
        else:
            idx = 0   # top pane for white

        msg = msg + '\n'

        ztime = ''
        nodes = ''
        depth = ''
        nps = ''
        pv = ''
        currmove = ''
        score = ''   
        msg_lst = msg.split()
        for i in range(0, len(msg_lst)):                
            if msg_lst[i] == 'time':
                ztime = msg_lst[i + 1]
            elif msg_lst[i] == 'nodes':
                nodes = msg_lst[i + 1]
            elif msg_lst[i] == 'depth':
                depth = msg_lst[i + 1]
            elif msg_lst[i] == 'nps':
                nps = msg_lst[i + 1]
            elif msg_lst[i] == 'currmove':
                currmove = msg_lst[i + 1]
            elif msg_lst[i] == 'score':                
                score = msg_lst[i + 1]
                if score == 'cp':
                    score = msg_lst[i + 2]
                elif score == 'mate':
                    score = score + ' ' + msg_lst[i + 2]         
            elif msg_lst[i] == 'pv':
                pv_lst = msg_lst[i + 1:]
                for p in pv_lst:
                    pv = pv + p + '  '

        ztime = self.format_time(ztime)        
        zmsg = depth + '\t' + nodes + '\t' + ztime + '\t' + score + '\t' + pv + '\n'         
        
        # insert at start of buffer
        start_iter = self.tb[idx].get_start_iter()            
            
  
        if ztime != '' or nodes != '' or depth != '' or pv != '':
            self.tb[idx].insert(start_iter, zmsg)

        self.nps_lbl[idx].set_text('NPS: ' + nps)
        """
        if nps != '':
            self.nps_lbl[idx].set_text('NPS: ' + nps)
        else:
            try:                    
                nps_num = int(nodes) * 1000 / int(ztime)             
                nps = str(nps_num)
                self.nps_lbl[idx].set_text('NPS: ' + nps)
            except:
                pass            
        """
        

        #self.nps_lbl[idx].set_text('NPS: 1200')

        if side == 'b':
            s = 'Black: '
        else:
            s = 'White: '
        self.engine_name_lbl[idx].set_text(s + engine_name)

        if currmove != '':
            self.currmove_lbl[idx].set_text('Current Move: ' + currmove)


    def clear(self, side, engine_name):
        # Write to either the black or white split pane
        if side == 'b':
            idx = 1   # bottom pane for black
        else:
            idx = 0   # top pane for white
        
        self.tb[idx].set_text('')      

        if side == 'b':
            s = 'Black: '
        else:
            s = 'White: '
        self.engine_name_lbl[idx].set_text(s + engine_name)        


    def set_ponder_move(self, pondermove, side):        
        if side == 'b':
            self.ponder_move_lbl[1].set_text('Ponder: ' + pondermove)
        else: 
            self.ponder_move_lbl[0].set_text('Ponder: ' + pondermove)        


    def show_engine_output_window(self, b):
        self.window.present()


def get_ref():
    if Engine_Output.engine_output_ref is None:
        Engine_Output.engine_output_ref = Engine_Output()
    return Engine_Output.engine_output_ref



