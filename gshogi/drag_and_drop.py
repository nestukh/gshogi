#
#   drag_and_drop.py
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

import utils
from constants import *

class Drag_And_Drop:

    drag_and_drop_ref = None

    def __init__(self):
        self.verbose = False
        self.board = utils.get_board_ref()
        self.game = utils.get_game_ref()


    def set_verbose(self, verbose):
        self.verbose = verbose


    """
    def draw(self, cr, width, height):
        # Fill the background with gray
        cr.set_source_rgb(0.5, 0.5, 0.5)
        cr.rectangle(0, 0, width, height)
        cr.fill()
    """    
    

    #
    # user has begun to drag a piece
    #
    def drag_begin(self, widget, drag_context, data):

        """
        #cr = self.gui.window.window.cairo_create()
        self.gui.af.window.set_opacity(0)
        cr = self.gui.af.window.cairo_create()

        cr.rectangle(400, 400, 600, 600)

        #cr.rectangle(event.area.x, event.area.y,
        #        event.area.width, event.area.height)
        cr.clip()

        #self.draw(cr, *self.gui.window.window.get_size())
        self.draw(cr, *self.gui.af.window.get_size())
        """
   
        self.dnd_data_received = False        

        # get x,y co-ords of source square
        x, y = data

        if self.verbose:
            print "in drag begin"       
            print "data=",data
            print "widget_name=",widget.get_name()
            print "source sq=", x, y

        stm = self.game.get_side_to_move()

        #print "proto=",drag_context.protocol
        # drag source is a capture square not a board square
        if widget.get_name() == "bcap_eb" or widget.get_name() == "wcap_eb":
            self.src_x = x
            self.src_y = y   
            self.piece = self.board.get_cap_piece(y, stm)
            
            self.src = self.piece + '*'
            
            pb = self.board.get_cap_pixbuf(y, stm)          

            hot_x = pb.get_width() / 2
            hot_y = pb.get_height() / 2       
            drag_context.set_icon_pixbuf(pb, hot_x, hot_y)        

            # save the pixbuf for use in the drop (receivecallback) routines
            self.dnd_pixbuf = pb

            # clear the square where the piece is being moved from
            self.board.set_cap_as_unoccupied(y, self.piece, stm)            
            self.board.refresh_screen()
        else:                    

            # convert the x, y co-ords into the shogi representation (e.g. 8, 6 is 1g)
            sq = self.board.get_square_posn(x, y)        
           
            self.src = sq
            if self.verbose: print "source square: (x, y) = (", x, ",",  y, ") ", sq
            self.src_x = x
            self.src_y = y            
        
            # set the icon for the drag and drop to the piece that is being dragged
            self.piece = self.board.get_piece(x, y)
            pb = self.board.get_piece_pixbuf(x, y)

            hot_x = pb.get_width() / 2
            hot_y = pb.get_height() / 2       
            drag_context.set_icon_pixbuf(self.board.get_piece_pixbuf(x, y), hot_x, hot_y)        

            # save the pixbuf for use in the drop (receivecallback) routines
            self.dnd_pixbuf = pb

            # clear the square where the piece is being moved from
            self.board.set_square_as_unoccupied(x, y)


    def sendCallback(self, widget, context, selection, targetType, eventTime):
        if targetType == TARGET_TYPE_TEXT:           
            sel = "gShogi"
            selection.set(selection.target, 8, sel)        


    def receiveCallback(self, widget, context, x, y, selection, targetType,
                        time, data):
        if self.verbose:
            print "in receive callback"
            print "x=", x
            print "y=", y        
            print "selection.data=",selection.data
            print "targetType=", targetType
            print "time=", time
            print "data=",data        

        self.dnd_data_received = True

        # get x,y co-ords of dest square
        x, y = data

        # convert the x, y co-ords into the shogi representation (e.g. 8, 6 is 1g)
        sq = self.board.get_square_posn(x, y)
             
        # set destination square            
        dst = sq
        if self.verbose: print "dst =",dst        

        move = self.game.get_move(self.piece, self.src, dst, self.src_x, self.src_y, x, y)
        if self.verbose:        
            print "move=",move
            print

        # if drag and drop failed then reinstate the piece where it
        # was dragged from
        if move is None:
            self.board.update()
            return
         
        # show the dropped piece on the board
        self.board.set_image(x, y, self.dnd_pixbuf)        

        # display the move                
        gobject.idle_add(self.game.human_move, move)


    # if drag and drop failed then reinstate the piece where it
    # was dragged from
    def drag_end(self, widget, drag_context):
        # if receiveCallback function not entered then restore board
        # to before the drag started
        if not self.dnd_data_received:
            self.board.update()
            return


def get_ref():
    if Drag_And_Drop.drag_and_drop_ref is None:
        Drag_And_Drop.drag_and_drop_ref = Drag_And_Drop()
    return Drag_And_Drop.drag_and_drop_ref



