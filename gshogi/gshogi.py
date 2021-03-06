#
#   gshogi 0.4.5  August 2012
#
#   Copyright (C) 2010-2012 John Cheetham    
#   
#   web   : http://www.johncheetham.com/projects/gshogi
#   email : developer@johncheetham.com
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

import pygtk
pygtk.require('2.0')
import gtk

import thread, traceback
import sys
import os
import gobject
import pickle
import time

import engine
import utils
import gui, usi, engine_manager, time_control, set_board_colours
import move_list
import engine_output
from constants import *

class Game:    

    def __init__(self):

        self.verbose = False
        self.verbose_usi = False
        for arg in sys.argv:
            if arg == '-v' or arg == '--verbose':
                self.verbose = True
            if arg == '-vusi':
                self.verbose_usi = True

        self.ask_before_promoting = False
        self.gameover = False       
        self.time_limit = '00:10'
        self.stopped = True
        self.quitting = False        
        self.src = ''
        self.src_x = ''
        self.src_y = ''
        self.startpos = 'startpos'
        self.start_stm = BLACK        

        self.search_depth = 39
        self.thinking = False
        self.cmove = 'none'
        self.movelist = []
        self.redolist = []        
        self.player = ["Human", "gshogi"]
        self.pondermove = [None, None]

       # set paths to images. opening book etc        
        self.set_data_paths() 
        opening_book_path = os.path.join(self.prefix, "data/opening.bbk")              
        engine.init(opening_book_path, self.verbose)

        self.glade_dir = os.path.join(self.prefix, 'glade')             
        
        utils.set_game_ref(self)            

        # usiw is the instance that plays white (gote)
        # usib is the instance that plays black (sente)
        self.usib = usi.Usi(self.verbose, self.verbose_usi, 'b')
        self.usiw = usi.Usi(self.verbose, self.verbose_usi, 'w')
        utils.set_usi_refs(self.usib, self.usiw)  

        # instantiate board, gui, classes 
        self.tc = time_control.Time_Control(self.verbose) 
        utils.set_tc_ref(self.tc)
        self.engine_manager = engine_manager.Engine_Manager(self.verbose)        
        self.board = utils.get_board_ref()
        self.pieces = utils.get_pieces_ref()
        
        self.gui = utils.get_gui_ref() 
        self.board.set_refs(self, self.gui)
        self.gui.set_refs(self, self.board, self.engine_manager, self.tc)
        self.gui.build_gui()
        self.board.build_board()
        self.engine_manager.set_refs(self, self.gui, self.usib, self.usiw)
        self.usib.set_refs(self, self.engine_manager, self.gui, self.tc)
        self.usiw.set_refs(self, self.engine_manager, self.gui, self.tc)
        self.tc.set_refs(self, self.gui)               
        self.set_board_colours = set_board_colours.get_ref()
        self.engine_output = engine_output.get_ref()                     

        # set level        
        command = 'level 0 ' + self.time_limit                  
        engine.command(command)   
        # turn off beeps
        if not BEEP:
            engine.command('beep')

        # restore users settings to values from previous game
        self.restore_settings()

        self.usib.set_engine(self.player[BLACK], None)
        self.usiw.set_engine(self.player[WHITE], None)        
        self.gui.update_toolbar(self.player)
               
        self.move_list = move_list.get_ref()

        self.tc.reset_clock()
        
        self.gui.enable_go_button()            
        self.gui.disable_stop_button()

        self.stm = self.get_side_to_move()
        
        self.timer_active = False       


    def set_data_paths(self):
        
        # Find the absolute path that this python program is running in 
        progpath = os.path.abspath(os.path.dirname(__file__))        

        # work out if we are running from an installed version
        # or from the source directory
        if progpath.startswith(sys.prefix):
            # we are installed
            self.prefix = os.path.join (sys.prefix, "share/gshogi")
            
            if os.path.isdir(self.prefix):
                if self.verbose: print "images/data path=", self.prefix
            else:
                if self.verbose: print "setting images/data path"

                for dir in ("share", "games", "share/games",
                    "local/share", "local/games", "local/share/games"):
                    self.prefix = os.path.join (sys.prefix, dir, "gshogi")
                    if os.path.isdir(self.prefix):
                        if self.verbose: print "found images/data path=", self.prefix                        
                        break
                else:
                    raise Exception("can't find data directory")
       
        else:
            # we are NOT installed
            # get data files (images, opening book, endgame databases) from same directory as this program 
            self.prefix = os.path.abspath(os.path.dirname(__file__))
            self.prefix = os.path.dirname(self.prefix)            
            if self.verbose: print "using images/data path=", self.prefix 


        # set up gshogi directory under home directory
        self.gshogipath = os.path.expanduser("~") + "/.gshogi"        
        if not os.path.exists(self.gshogipath):
            try:
                os.makedirs(self.gshogipath)
            except OSError, exc:                
                raise


    #
    # Process Human move
    #
    def square_clicked(self, widget, event, data):               
        # if in edit board mode then call routine in gui.py to show the edit
        # popup menu
        if self.gui.get_edit_mode():
            (x, y) = data
            self.gui.show_edit_popup(event, x, y)
            return

        if self.gameover or self.thinking or self.stopped:        
            return            

        self.stm = self.get_side_to_move()
        if self.player[self.stm]  != "Human":
            return        
        self.gui.set_side_to_move(self.stm)

        # get x,y co-ords of square clicked on (0, 0 is top left)            
        (x, y) = data        

        # convert the x, y co-ords into the shogi representation (e.g. 8, 6 is 1g)
        sq = self.board.get_square_posn(x, y)        
        
        # if the square clicked on is a valid source square
        # then set this square as the source square
        if self.board.valid_source_square(x, y, self.stm):             
            self.src = sq
            if self.verbose: print "source square: (x, y) = (", x, ",",  y, ") ", sq
            self.src_x = x
            self.src_y = y
            self.piece = self.board.get_piece(x, y)
            #self.hilite_move(sq)
            self.gui.hilite_squares( [(x, y)] )
            return
          
        # must have a valid source square before checking dest square        
        if self.src == '':
            return
             
        # Not a valid source square, assume destination square            
        dst = sq
        
        move = self.get_move(self.piece, self.src, dst, self.src_x, self.src_y, x, y)
        if move is None:
            return
         
        # display the move
        self.human_move(move)


    # format human move            
    def get_move(self, piece, src, dst, src_x, src_y, dst_x, dst_y):
        if self.verbose:
            print "in get move"
            print "src=",src
            print "dst=",dst
            print "src_x=",src_x
            print "src_y=",src_y
            print "dst_x=",dst_x
            print "dst_y=",dst_y
       
        move = self.src + dst
        # check for promotion
        if self.promotion_zone(src, dst, self.stm):
            promote = self.board.promote(piece, src_x, src_y, dst_x, dst_y, self.stm)
            if (promote == 2):
                # must promote
                move = move + "+"
            elif (promote == 1):
                # promotion is optional
                #
                # But always prompt before promoting a silver since it
                # can be valuable to have an unpromoted silver on the
                # opposite side of the board.
                if self.ask_before_promoting or piece == " s" or piece == " S":
                    response = self.gui.promote_popup()
                    if (response == gtk.RESPONSE_CANCEL):
                        return None
                    if (response == gtk.RESPONSE_YES):                            
                        move = move + "+"
                else:                        
                    move = move + "+"           

        if self.verbose: print "move=",move        

        engine.setplayer(self.stm)
        validmove = engine.hmove(move)
        if (not validmove):
            # illegal move                               
            self.gui.set_status_bar_msg("Illegal Move")
            return None
        return move                         


    def human_move(self, move):        
        self.movelist.append(move)
        self.redolist = []        
        #self.board.save_board(len(self.movelist))

        # highlight the move by changing square colours
        self.hilite_move(move)       
        
        self.board.update()
        # update move list in move list window
        self.move_list.update()

        if self.verbose: engine.command('bd')
        self.src = ''

        self.gameover, msg = self.check_for_gameover() 
        if (self.gameover):
            self.stop()               
            self.gui.set_status_bar_msg(msg)                
            self.thinking = False  
            return                   
                
        #self.gui.set_status_bar_msg('Thinking ...')  
        #if self.verbose: print "--------------------------------------------------------------------------------"
        #print "whites move"
        self.stm = self.get_side_to_move()
        self.gui.set_side_to_move(self.stm)
        if self.verbose:
            print "#"
            print "# " + self.get_side_to_move_string(self.stm) + " to move"
            print "#"                
        self.gui.set_status_bar_msg(" ")                
                
        self.src = ''

        # update time for last move
        self.tc.update_clock()

        self.gui.apply_drag_and_drop_settings(self.player[self.stm], self.stm)   

        if self.player[self.stm] == "Human":                     

            # set clock ready for move to come   
            self.tc.start_clock(self.stm)            

            if not self.timer_active:
                gobject.timeout_add(1000, self.tc.show_time)            

            return
            
        self.thinking = True
        # disable some functionality while the computer is thinking
        #self.gui.disable_menu_items()   

        # It's the computers turn to move
        # kick off a separate thread for computers move so that gui is still useable                                      
        self.ct= thread.start_new_thread( self.computer_move, () )
                                        
        return
        

    def stop_clicked(self, widget):
        self.stop()


    def stop(self):
        self.stopped = True        
        self.gui.enable_menu_items()
        self.gui.enable_go_button()
        self.gui.disable_stop_button()
        self.gui.unset_all_drag_and_drop_squares()

        # update time
        self.tc.stop_clock()                    

        # stop engines        
        self.usib.stop_engine()
        self.usiw.stop_engine()
        engine.movenow()
        self.gui.set_status_bar_msg("stopped")        


    def go_clicked(self, widget):        
            
        # update time control prior to move
        self.tc.update_gui_time_control(self.stm)             
            
        # side to move
        self.stm = self.get_side_to_move() 

        # start a timer to display the time left while the player is thinking
        self.tc.start_clock(self.stm)           
        
        if not self.timer_active:       
            gobject.timeout_add(1000, self.tc.show_time)

        self.gui.disable_menu_items()
        self.gui.disable_go_button()
        self.gui.enable_stop_button()        
        
        self.stopped = False

        if self.verbose:
            print "#"
            print "# " + self.get_side_to_move_string(self.stm) + " to move"
            print "#"        

        self.gui.apply_drag_and_drop_settings(self.player[self.stm], self.stm)

        #self.board.reduce_board_history(self.movelist)
        self.engine_output.clear('w', ' ')
        self.engine_output.clear('b', ' ')

        if self.player[self.stm] == "Human":            
            self.gui.set_status_bar_msg("ready")             
            return

        self.gui.set_status_bar_msg('Thinking ...')
        # It's the computers turn to move
        # kick off a separate thread for computers move so that gui is still useable                                                    
        self.ct= thread.start_new_thread( self.computer_move, () )


    def cap_square_clicked(self, widget, event, data):       

        # if in edit board mode then call routines in board.py to change the piece count
        # in the komadai
        if self.gui.get_edit_mode():           
            x, y, colour = data            
            if event.button == 1:                           # left click - decrement count for the piece clicked on
                self.board.decrement_cap_piece(y, colour)
            elif event.button == 3:                         # right click - increment count for the piece clicked on
                self.board.increment_cap_piece(y, colour)
            return

        if self.gameover or self.thinking:        
            return            
        
        x, y, colour = data

        # If user clicked in the black capture area and it's white to move or vice versa
        # then ignore
        stm = self.get_side_to_move()
        if stm != colour:
            return

        self.src_x = x
        self.src_y = y                
        self.piece = self.board.get_cap_piece(y, stm)        

        if (self.piece != '0'):
            self.src = self.piece + '*'
        else:
            self.src = ''
        #print "self.src=",self.src


    def get_prefix(self):
        return self.prefix


    def get_glade_dir(self):
        return self.glade_dir


    def computer_move(self):        
        try:           
            self.thinking = True                
                       
            while  True:
                self.thinking = True                                
                self.stm = self.get_side_to_move()                                

                # update time for last move
                gtk.gdk.threads_enter()
                #self.tc.update_clock()                
                self.gui.set_side_to_move(self.stm)
                # set clock ready for move to come                
                #self.tc.start_clock(self.stm)
                gtk.gdk.threads_leave()

                if self.verbose:
                    print "#"
                    print "# " + self.get_side_to_move_string(self.stm) + " to move"
                    print "#"                

                if self.player[self.stm] == "Human":
                    gtk.gdk.threads_enter()
                    self.gui.apply_drag_and_drop_settings(self.player[self.stm], self.stm)
                    gtk.gdk.threads_leave()
                    self.thinking = False
                    self.tc.start_clock(self.stm)                              
                    return
                
                t_start = time.time()
                if self.player[self.stm] != 'gshogi':                            
                    if self.stm == BLACK:
                        self.usi = self.usib
                        #usi_opponent = self.usiw
                        #opponent_stm = WHITE 
                    else:
                        self.usi = self.usiw
                        #usi_opponent = self.usib
                        #opponent_stm = BLACK
                    
                    ponder_enabled = self.engine_manager.get_ponder()

                    if not ponder_enabled:
                        # get engines move
                        self.cmove, self.pondermove[self.stm] = self.usi.cmove(self.movelist, self.stm)
                    else:
                        # pondering
                        ponderhit = False                    
                        if self.pondermove[self.stm] is not None and len(self.movelist) > 0:
                            if self.movelist[-1] == self.pondermove[self.stm]:
                                ponderhit = True

                        if ponderhit:
                            self.cmove, self.pondermove[self.stm] = self.usi.send_ponderhit(self.stm)  # ponderhit, wait for return of bestmove and pondermove
                        else:                           
                            if self.pondermove[self.stm] is not None:
                                bm, pm = self.usi.stop_ponder()  # stop ponder, wait for return of bestmove and pondermove from ponder                                      
                            # get engines move
                            self.cmove, self.pondermove[self.stm] = self.usi.cmove(self.movelist, self.stm)
                        
                        # start pondering                    
                        if self.pondermove[self.stm] is not None:
                            self.usi.start_ponder(self.pondermove[self.stm], self.movelist, self.cmove)  # send position and ponder command, return immediately                   

                    if self.stopped or self.cmove is None:                        
                        self.thinking = False                        
                        return                    

                    if self.verbose: print "computer move is",self.cmove
                    # check if player resigned
                    if self.cmove == 'resign':
                        if self.verbose: print "computer resigned"                        
                        self.gameover = True
                        self.thinking = False
                        colour = self.get_side_to_move_string(self.stm)                        
                        msg = "game over - " + colour + " resigned"
                        gtk.gdk.threads_enter()
                        self.stop()
                        self.gui.set_status_bar_msg(msg)                        
                        gtk.gdk.threads_leave()                        
                        self.thinking = False 
                        return
                    
                    #engine.setplayer(WHITE)
                    engine.setplayer(self.stm)            
                    validmove = engine.hmove(self.cmove)             
                    if (not validmove):
                        gtk.gdk.threads_enter()
                        self.stop()
                        self.gui.set_status_bar_msg(self.cmove + " - computer made illegal Move!")                        
                        gtk.gdk.threads_leave()
                        self.gameover = True                        
                        self.thinking = False                 
                        return                    
                    if self.verbose: engine.command('bd')                                                         
                else:

                    if self.verbose: print "using gshogi builtin engine"
                    #
                    # We are using the builtin gshogi engine (not a USI engine)
                    #

                    if self.player[self.stm ^ 1] == "Human":
                        gtk.gdk.threads_enter()                    
                        self.gui.set_status_bar_msg('Thinking ...')
                        gtk.gdk.threads_leave() 

                    # set the computer to black or white                                       
                    engine.setplayer(self.stm ^ 1)                    
                    
                    # start the clock
                    #print "starting clock from gshogi.py"
                    gtk.gdk.threads_enter()                 
                    self.tc.start_clock(self.stm)
                    gtk.gdk.threads_leave()                    

                    # set time limit/level for move in gshogi engine
                    self.tc.set_gshogi_time_limit(self.stm)                   

                    # call the gshogi engine to do the move      
                    self.cmove = engine.cmove()                   

                    # update time for last move
                    gtk.gdk.threads_enter()
                    #print "updating clock from gshogi.py"                    
                    self.tc.update_clock()                
                    self.gui.set_side_to_move(self.stm)        
                    gtk.gdk.threads_leave()                                                                             

                    if self.quitting:
                        return                  

                    if self.stopped:                        
                        self.thinking = False
                        gtk.gdk.threads_enter()
                        self.gui.set_status_bar_msg("stopped")                        
                        gtk.gdk.threads_leave()
                        engine.command('undo')                        
                        return                                                    
                           
                if self.cmove != '':
                    self.movelist.append(self.cmove)
                    self.redolist = []
                    # highlight the move by changing square colours
                    gtk.gdk.threads_enter()
                    self.hilite_move(self.cmove)
                    gtk.gdk.threads_leave() 
                else:
                    # empty move is returned by gshogi engine when it is in checkmate
                    if self.verbose: print "empty move returned by engine"
                
                # if the engine moved very fast then wait a bit
                # before displaying the move. The time to wait
                # is in MIN_MOVETIME in constants.py
                t_end = time.time()
                move_t = t_end - t_start
                if move_t < MIN_MOVETIME:
                    diff = MIN_MOVETIME - move_t
                    time.sleep(diff)

                # if program is exitting then quit this thread asap
                if self.quitting:
                    return                

                #self.board.save_board(len(self.movelist))
                # show computer move              
                gtk.gdk.threads_enter()
                self.board.update()
                self.move_list.update()
                gtk.gdk.threads_leave()    
    

                #if self.player[self.stm] != 'gshogi' and self.engine_manager.get_ponder():                    
                #    self.usi.send_ponder()
                #    #self.ctp= thread.start_new_thread( self.usi.send_ponder, () )                   

                if self.verbose: engine.command('bd')
       
                if self.verbose: print "move=",self.cmove
                msg = self.cmove                

                self.gameover, gmsg = self.check_for_gameover()
                if (self.gameover):            
                    if (msg == ''):
                        msg = gmsg 
                    else:
                        msg = self.get_side_to_move_string(self.stm) + ": " + msg
                        msg = msg + ". " + gmsg                                   
                    self.thinking = False
                    self.stm = self.get_side_to_move()
                    gtk.gdk.threads_enter()
                    self.stop()                
                    self.gui.set_side_to_move(self.stm)                    
                    self.gui.set_status_bar_msg(msg)                    
                    gtk.gdk.threads_leave()                 
                    return    

                msg = self.get_side_to_move_string(self.stm) + ": " + msg
                gtk.gdk.threads_enter()
                self.gui.set_status_bar_msg(msg)
                gtk.gdk.threads_leave()                

            self.thinking = False 
        except:            
            traceback.print_exc()
            return   


    # highlight the move by changing square colours
    def hilite_move(self, move):
        # if move is a drop then just highlight the dest square
        if move[1] == '*':
            dst = self.board.get_gs_square_posn(move[2:4])
            self.gui.hilite_squares( [dst] )
        else:
            # not a drop so highlight source and dest squares   
            src = self.board.get_gs_square_posn(move[0:2])
            dst = self.board.get_gs_square_posn(move[2:4])         
            self.gui.hilite_squares( [src, dst] )


    def check_for_gameover(self):
        gameover = False
        msg = ''
        winner = engine.getwinner()                
        if (winner):
            gameover = True            
            winner -= 1
            if (winner == BLACK):
                msg = "game over - black wins"
            elif (winner == WHITE):
                msg = "game over - white wins"
            elif (winner == NEUTRAL):
                msg = "game over - match drawn"
            else:
                print "invalid value returned from engine getwinner function"
        return gameover, msg      


    def set_promotion_mode(self, mode):
        self.ask_before_promoting = mode               


    def promotion_zone(self, src, dst, stm):        
        srclet = src[1:2]                        
        dstlet = dst[1:2]

        # can't promote dropped pieces
        if srclet == '*':
            return False                

        if stm == BLACK:
            if (srclet < 'd' and srclet != '*') or dstlet < 'd':
                return True
            else:
                return False
        else:
            if (srclet > 'f' and srclet != '*') or dstlet > 'f':
                return True
            else:
                return False


    #
    # Callback Functions
    #
    
    def quit_game(self, b):
        self.quit()        
        return False

    
    # This callback quits the program
    def delete_event(self, widget, event, data=None):
        self.quit()        
        return False


    def quit(self): 
        self.stopped = True
        self.quitting = True
        engine.movenow()
        self.save_settings()         
        self.usib.stop_engine() 
        self.usiw.stop_engine()      
        gtk.main_quit()
        return False


    def quitting(self):
        return self.quitting


    #
    # called from menu by new game and new handicap game   
    #
    def new_game_cb(self, action):
        menu_name = action.get_name()
        self.new_game(menu_name)

  
    # called from new_game_cb in this module and from load_game_psn_from_str
    # in psn.py 
    def new_game(self, menu_name):
        
        self.gameover = False
        engine.command('new')                

        if menu_name == 'NewGame':
            # Normal Game (No handicap)
            self.startpos = 'startpos'
            self.start_stm = BLACK
        else:
            # Handicap Game
            self.start_stm = WHITE
            if menu_name == 'LanceHandicap':           
                sfen = 'lnsgkgsn1/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                  
            elif menu_name == 'BishopHandicap':            
                sfen = 'lnsgkgsnl/1r7/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                  
            elif menu_name == 'RookHandicap':           
                sfen = 'lnsgkgsnl/7b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                   
            elif menu_name == 'RookandLanceHandicap':            
                sfen = 'lnsgkgsn1/7b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                  
            elif menu_name == 'TwoPieceHandicap':            
                sfen = 'lnsgkgsnl/9/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                  
            elif menu_name == 'FourPieceHandicap':            
                sfen = '1nsgkgsn1/9/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                  
            elif menu_name == 'SixPieceHandicap':            
                sfen = '2sgkgs2/9/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                 
            elif menu_name == 'EightPieceHandicap':            
                sfen = '3gkg3/9/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'                 
            elif menu_name == 'TenPieceHandicap':           
                sfen = '4k4/9/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL w - 1'               
            else:
                self.gui.info_box('Error. Invalid menu name:' + menu_name)               
                return
            
            engine.setfen(sfen)
            self.startpos = sfen 
 
        self.board.update()
        # update move list in move list window
        self.move_list.update()
        if not BEEP:
            engine.command('beep')        

        self.usib.set_newgame()
        self.usiw.set_newgame()        
        self.movelist = []
        self.redolist = [] 
        self.gui.set_status_bar_msg('') 
        self.stm = self.get_side_to_move()
        self.gui.set_side_to_move(self.stm)
        self.gui.unhilite_squares()        
                               
        self.tc.reset_clock()


    #
    # save users settings at program termination
    #    
    def save_settings(self):         
        
        # get settings
        s = Settings()
        s.name = NAME
        s.version = VERSION
        s.engine_list = self.engine_manager.get_engine_list()        
        s.pieceset = self.pieces.get_pieceset()
        s.custom_pieceset_path = self.pieces.get_custom_pieceset_path() 
        s.player_white = self.player[WHITE]
        s.player_black = self.player[BLACK]
        s.clock_settings = self.tc.get_clock_settings()
        #s.dnd = self.gui.get_dnd()
        s.colour_settings = self.set_board_colours.get_settings()
        s.hash_value = self.engine_manager.get_hash_value()        
        s.ponder = self.engine_manager.get_ponder()
        s.show_coords = self.gui.get_show_coords()
        s.highlight_moves = self.gui.get_highlight_moves()

        # pickle and save settings
        try:                        
            settings_file = os.path.join (self.gshogipath, "settings")            
            f = open(settings_file, 'w')            
            pickle.dump(s, f)            
            f.close()        
        except AttributeError, ae:
            print "attribute error:",ae
        except pickle.PickleError, pe:
            print "PickleError:", pe
        except pickle.PicklingError, pe2:
            print "PicklingError:", pe2
        except Exception, exc:
            print "cannot save settings:", exc         


    #
    # restore users settings at program start-up
    #    
    def restore_settings(self):       
        x = ''               
        try:            
            settings_file = os.path.join (self.gshogipath, "settings")            
            f = open(settings_file, 'rb')            
            x = pickle.load(f)           
            f.close()        
        except EOFError, eofe:
            print "eof error:",eofe        
        except pickle.PickleError, pe:
            print "pickle error:", pe
        except IOError, ioe:
            pass    # Normally this error means it is the 1st run and the settings file does not exist        
        except Exception, exc:
            print "Cannot restore settings:", exc             
        
        if x:
            # engine list
            try:                
                self.engine_manager.set_engine_list(x.engine_list)                
            except Exception, e:                        
                if self.verbose: print e, ". engine list not restored"

            # pieceset 'eastern', 'western' or 'custom'
            try:                
                self.pieces.set_pieceset(x.pieceset) 
            except Exception, e:                        
                if self.verbose: print e, ". pieceset setting not restored" 

            # custom pieceset path
            try:
               self.pieces.set_custom_pieceset_path(x.custom_pieceset_path)
            except Exception, e:                        
                if self.verbose: print e, ". custom pieceset path setting not restored" 

            # set the engine or human for each player
            try:
                self.player[WHITE] = x.player_white
                self.player[BLACK] = x.player_black
            except Exception, e:                        
                if self.verbose: print e, ". player setting not restored" 

            # time controls
            try:
                cs = x.clock_settings                
                self.tc.restore_clock_settings(cs)          
            except Exception, e:                        
                if self.verbose: print e, ". time controls not restored" 

            # using Drag and Drop enabled
            #try:
            #    if x.dnd == True:
            #        self.gui.set_dnd()
            #except Exception, e:                        
            #    if self.verbose: print e, ". DND setting not restored" 

           # colour settings
            try:               
                cs = x.colour_settings
                #
                # if settings file is from old version then need to add border colour and grid colour
                # this code will only run once
                # 
                if x.version == '0.4.3':
                    print "converting old colour scheme to new version"                    
                    lst = list(cs)                    
                    lst.insert(7, lst[2])      # border colour - set same as square colour
                    lst.insert(8, '#000000')   # grid colour - set to black               
                    cs = tuple(lst)
                    print "colour scheme tuple is:",cs

                self.set_board_colours.restore_colour_settings(cs)          
            except Exception, e:                        
                if self.verbose: print e, ". colour settings not restored" 

            # hash value
            try:               
                hash_value = x.hash_value                         
                self.engine_manager.set_hash_value(hash_value)                
            except Exception, e:                        
                if self.verbose: print e, ". hash value not restored" 
    
            # ponder (true/false)
            try:
                ponder = x.ponder
                self.engine_manager.set_ponder(ponder)
            except Exception, e:                        
                if self.verbose: print e, ". ponder not restored" 

            # show coordinates (true/false)
            try:
                show_coords = x.show_coords
                self.gui.set_show_coords(show_coords)
            except Exception, e:                        
                if self.verbose: print e, ". show_coords not restored" 

            # highlight moves (true/false)
            try:
                highlight_moves = x.highlight_moves
                self.gui.set_highlight_moves(highlight_moves)
            except Exception, e:                        
                if self.verbose: print e, ". highlight_moves not restored" 


    def goto_move(self, move_idx):
        try:
            self.usib.stop_engine()
            self.usiw.stop_engine()     
        except:
            pass           
        self.gameover = False
        #print "move is",move
        #print "movelist len is",len(self.movelist)
        if move_idx < len(self.movelist):
            while move_idx < len(self.movelist):
                self.undo_move()
        else:
            while move_idx > len(self.movelist):
                self.redo_move()
        
        self.stm = self.get_side_to_move()
        self.gui.set_side_to_move(self.stm)

        self.board.update() 
        #self.gui.set_status_bar_msg(" ")
        move = None
        try:
            move = self.movelist[len(self.movelist) - 1]  
            #print "move ",move
        except IndexError:
            pass
        
        if move is not None:        
            self.gui.set_status_bar_msg(move)
            # highlight the move by changing square colours
            self.hilite_move(move)  
        else:
            self.gui.set_status_bar_msg(" ")
            self.gui.unhilite_squares()     


    #
    # called from gui.py when undo button click on toolbar (passed widget is gtk.ToolButton object)
    # and when undo move is selected from menu (or ctrl-u is pressed) (passed widget is gtk.Action object) 
    #
    def undo_single_move(self, b):        
        engine.command('undo')
        move = None 
        try:            
            move = self.movelist.pop()                        
            self.redolist.append(move)           
            self.stm = self.get_side_to_move()
            self.gui.set_side_to_move(self.stm)            
        except IndexError:
            pass
        
        try:
            self.usib.stop_engine()
            self.usiw.stop_engine()     
        except:
            pass           
        self.gameover = False
        self.board.update()
        # set move list window to last move               
        self.move_list.set_move(len(self.movelist))
        if move is not None:        
            self.gui.set_status_bar_msg('(' + move + ')')
            # highlight the move by changing square colours
            self.hilite_move(move)
        else:  
            self.gui.unhilite_squares()


    # undo a move without updating the gui
    def undo_move(self):        
        engine.command('undo')
        move = None 
        try:            
            move = self.movelist.pop()                        
            self.redolist.append(move)                     
        except IndexError:
            pass      
        

    def undo_all(self, toolbutton):      
        try:
            self.usib.stop_engine()
            self.usiw.stop_engine()     
        except:
            pass           
        self.gameover = False
        while len(self.movelist) != 0:
            self.undo_move()
      
        self.stm = self.get_side_to_move()
        self.gui.set_side_to_move(self.stm)

        self.board.update()
        # set move list window to initial position
        self.move_list.set_move(0)
        self.gui.set_status_bar_msg(" ")
        self.gui.unhilite_squares()       


    #
    # called from gui.py when redo button click on toolbar (passed widget is gtk.ToolButton object)
    # and when redo move is selected from menu (or ctrl-r is pressed) (passed widget is gtk.Action object) 
    #
    def redo_single_move(self, widget):               
        move = None        
        try:
            move = self.redolist.pop()

            # get side to move before appending to movelist            
            self.stm = self.get_side_to_move()
            self.movelist.append(move)

            # do the move in gshogi engine
            engine.setplayer(self.stm)            
            engine.hmove(move)            

            # side to move changes to opponent
            self.stm = self.get_side_to_move()
            self.gui.set_side_to_move(self.stm)            
        except IndexError:
            pass
        
        try:
            self.usib.stop_engine()
            self.usiw.stop_engine()     
        except:
            pass        
        self.board.update()
        # set move list window to last move               
        self.move_list.set_move(len(self.movelist))        
        if move is not None:        
            self.gui.set_status_bar_msg(move)
            # highlight the move by changing square colours
            self.hilite_move(move) 


    # redo a move without updating the gui
    def redo_move(self):
        move = None        
        try:
            move = self.redolist.pop()

            # get side to move before appending to movelist            
            self.stm = self.get_side_to_move()
            self.movelist.append(move)

            # do the move in gshogi engine
            engine.setplayer(self.stm)            
            engine.hmove(move)                      
        except IndexError:
            pass


    def redo_all(self, toolbutton):        
        #try:
        #    self.usib.stop_engine()
        #    self.usiw.stop_engine()     
        #except:
        #    pass    
        while len(self.redolist) != 0:
            self.redo_move()        
        self.stm = self.get_side_to_move()
        self.gui.set_side_to_move(self.stm)  
        self.board.update()
        # set move list window to last move               
        self.move_list.set_move(len(self.movelist))
        
        move = None
        try:
            move = self.movelist[len(self.movelist) - 1]  
            #print "move ",move
        except IndexError:
            pass
        
        if move is not None:        
            self.gui.set_status_bar_msg(move)
            # highlight the move by changing square colours
            self.hilite_move(move)  
 

    def set_movelist(self, movelist):
        self.movelist = movelist


    def set_redolist(self, redolist):
        self.redolist = redolist


    def set_startpos(self, startpos):
        self.startpos = startpos


    def set_side_to_move(self, stm):
        self.stm = stm


    def get_stm(self):
        return self.stm


    def get_move_count(self):
        return len(self.movelist) + 1

         
    def get_side_to_move(self):

        # get side to move for the first move of the game
        # This is black in a normal game and white in a handicap game
        start_stm = self.get_stm_from_sfen(self.startpos)
                  
        if len(self.movelist) % 2 == 0:            
            return start_stm
        else:           
            return start_stm ^ 1
                

    def get_side_to_move_string(self, stm):          
        if stm == BLACK:            
            return "black"
        else:
            return "white"


    def get_stm_from_sfen(self, sfen):        
        if sfen == 'startpos':
            # normal game
            stm = BLACK
        else:
            sp = sfen.split()            
            try:
                if sp[1] == 'w':
                    stm = WHITE                
                else: 
                    stm = BLACK
            except:
                    stm = BLACK        
        return stm


    def get_player(self, side):
        return self.player[side]


    def move_now(self, b):
        if self.player[self.stm]  == "Human":
            return

        if not self.thinking:
            return

        # builtin gshogi engine
        if self.player[self.stm]  == "gshogi":
            engine.movenow()
            return
        
        # USI engine
        try:
            if self.stm == BLACK:                
                self.usib.command('stop\n')        
            else:                
                self.usiw.command('stop\n')            
        except:
            pass


    def get_movelist(self):
        return self.movelist


    def get_redolist(self):
        return self.redolist


    def get_verbose(self):
        return self.verbose


    def get_verbose_usi(self):
        return self.verbose_usi


    def set_players(self, b):
        dialog = gtk.Dialog("Players", None, 0, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK)) 
        dialog.set_title('Set Players')
    
        elist = self.engine_manager.get_engine_list()       
        
        # White Player 
        fr = gtk.Frame("White")
        dialog.vbox.pack_start(fr, True, True, 15)
        #dialog.vbox.set_spacing(20)
        vb = gtk.VBox(False, 0)
        fr.add(vb)
               
        comboboxw = gtk.combo_box_new_text()        
        comboboxw.append_text("Human")
        
        if self.player[WHITE] == "Human":
            comboboxw.set_active(0)

        i = 1
        for (engine_name, path) in elist:            
            comboboxw.append_text(engine_name)
            
            if engine_name == self.player[WHITE]:
                comboboxw.set_active(i)
            i += 1        
        vb.pack_start(comboboxw, True, True, 15)       


        # Black Player 
        fr = gtk.Frame("Black")
        dialog.vbox.pack_start(fr, True, True, 15)
        vb = gtk.VBox(False, 0)
        fr.add(vb)
                       
        comboboxb = gtk.combo_box_new_text()
        comboboxb.append_text("Human")
        if self.player[BLACK] == "Human":
            comboboxb.set_active(0)

        i = 1
        for (engine_name, path) in elist:            
            comboboxb.append_text(engine_name)            
            if engine_name == self.player[BLACK]:
                comboboxb.set_active(i)                
            i += 1        
        vb.pack_start(comboboxb, True, True, 15)        
        
        dialog.show_all()        


        # If user hasn't clicked on OK then exit now
        if dialog.run() != gtk.RESPONSE_OK:
            dialog.destroy()
            return                
        
        
        self.player[BLACK] = comboboxb.get_active_text()
        self.player[WHITE] = comboboxw.get_active_text()

        self.usib.set_engine(self.player[BLACK], None)
        self.usiw.set_engine(self.player[WHITE], None)

        self.gui.update_toolbar(self.player)
        
        dialog.destroy()               


    """
    def set_level(self, b):        
        
        dialog = gtk.MessageDialog(
            None,  
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,  
            gtk.MESSAGE_QUESTION,  
            gtk.BUTTONS_OK_CANCEL,  
            None)
        dialog.set_title('Configure Engine')    
        markup = "<b>gShogi</b>"
        dialog.set_markup(markup)       

        adj = gtk.Adjustment(float(self.search_depth), float(0), float(39), 1, 5, 0)               
        spinner = gtk.SpinButton(adj, 1.0, 0)        
        al = gtk.Alignment(xalign=1.0, yalign=0.0, xscale=0.0, yscale=0.0)
        al.add(spinner)
        al.show()
        spinner.show()        

        tbl = gtk.Table(1, 2, True)
        tbl.attach(gtk.Label("Search Depth:"), 0, 1, 0, 1)
        tbl.attach(al, 1, 2, 0, 1)       

        #some secondary text        
        markup = 'Configure Options'        
       
        dialog.format_secondary_markup(markup)      
        
        dialog.vbox.add(tbl)       

        dialog.show_all()        

        # If user hasn't clicked on OK then exit now
        if dialog.run() != gtk.RESPONSE_OK:
            dialog.destroy()
            return

        # user clicked OK so update with the values entered        
        depth = adj.get_value()        
        dialog.destroy()               
        
        # set search depth if valid
        try:
            idepth = int(depth)
            if (idepth >= 0 and idepth <= 39):
                self.search_depth = idepth
                engine.depth(self.search_depth)
        except ValueError:
                pass    


    def get_search_depth(self):
        return self.search_depth
    """
 
    def get_startpos(self):
        return self.startpos


    def get_stopped(self):
        return self.stopped


# class to save settings on program exit and restore on program start
class Settings:
    pass


def run():
    Game()        
    #gobject.threads_init()
    gtk.gdk.threads_init() 
    gtk.gdk.threads_enter()   
    gtk.main()
    gtk.gdk.threads_leave()
    return 0     

if __name__ == "__main__":        
    run()
