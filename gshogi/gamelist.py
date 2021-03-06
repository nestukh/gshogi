#
#   gamelist.py
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
import os

import utils

class Gamelist:

    def __init__(self):

        self.game = utils.get_game_ref()
        glade_dir = self.game.get_glade_dir()
        self.glade_file = os.path.join(glade_dir, "gamelist.glade")        
        
        # create gamelist window
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.glade_file)
        self.builder.connect_signals(self)

        self.window = self.builder.get_object('gamelist_window')
        self.treeview = self.builder.get_object('gamelist_treeview')
        self.liststore = self.builder.get_object('liststore1')

        cell0 = gtk.CellRendererText()       
        #cell0.set_property('cell-background', gtk.gdk.color_parse("#F8F8FF"))
        tvcolumn0 = gtk.TreeViewColumn()       
        self.treeview.append_column(tvcolumn0)         
        tvcolumn0.pack_start(cell0, True)
        tvcolumn0.set_min_width(50)        
        tvcolumn0.set_attributes(cell0, text=0)     

        self.tree_selection = self.treeview.get_selection()

        self.window.hide()


    # user has closed the window
    # just hide it
    def delete_event(self, widget, event):                     
        self.window.hide()
        return True  # do not propagate to other handlers 


    # called from gui.py when doing view gamelist
    def show_gamelist_window_cb(self, action):
        self.show_gamelist_window()


    # called from psn.py when opening multi-game file
    # and from show_gamelist_window_cb above        
    def show_gamelist_window(self):        
        # 'present' will show the window if it is hidden
        # if not hidden it will raise it to the top
        self.window.present()           
        return 

    def set_game_list(self, glist):
        # update liststore
        self.liststore.clear()
        gameno = 0 
        for hdrs in glist:           
            gameno += 1
            h = str(gameno) + '. '
            hdrno = 1 
            for hdr in hdrs:
                hdr = hdr.strip()
                hdr = hdr.lstrip('[')
                hdr = hdr.rstrip(']') 
                if hdrno == 1:
                    h = h + hdr 
                else:
                    h = h + ', ' + hdr 
                hdrno += 1            
            lst = [ h ]
            self.liststore.append(lst)


    def loadgame_button_clicked_cb(self, button):           
        (treemodel, treeiter) = self.tree_selection.get_selected() 
        if treeiter is not None:                
            game_str = treemodel.get_value(treeiter, 0)
            gameno = ''
            i = 0
            while game_str[i] != '.':
                gameno += game_str[i]
                i += 1
            try: 
                gameno = int(gameno)
            except ValueError, ve:
                return
            psn_ref = utils.get_psn_ref() 
            psn_ref.load_game_from_multigame_file(gameno)
            
           

