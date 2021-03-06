#
#   utils.py
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
import gui, board, pieces
import load_save
import comments
import psn
import gamelist

game_ref = None
gui_ref = None
pieces_ref = None
board_ref = None
usib_ref = None
usiw_ref = None
tc_ref = None
comments_ref = None
psn_ref = None
gamelist_ref = None


def get_gui_ref():
    global gui_ref    
    if gui_ref is None:       
        gui_ref = gui.Gui()
    return gui_ref


def get_pieces_ref():
    global pieces_ref    
    if pieces_ref is None:       
        pieces_ref = pieces.Pieces()
    return pieces_ref


def get_board_ref():
    global board_ref    
    if board_ref is None:       
        board_ref = board.Board()
    return board_ref


def set_game_ref(game):
    global game_ref
    game_ref = game


def get_game_ref():
    if game_ref is None:
        raise RuntimeError, 'game_ref not set'
    return game_ref


def get_comments_ref():
    global comments_ref    
    if comments_ref is None:       
        comments_ref = comments.Comments()
    return comments_ref


def set_tc_ref(tc):
    global tc_ref
    tc_ref = tc


def get_tc_ref():
    if tc_ref is None:
        raise RuntimeError, 'tc_ref not set'
    return tc_ref


def get_psn_ref():   
    global psn_ref    
    if psn_ref is None:       
        psn_ref = psn.Psn()
    return psn_ref


def get_gamelist_ref():
    global gamelist_ref    
    if gamelist_ref is None:       
        gamelist_ref = gamelist.Gamelist()
    return gamelist_ref
    

def set_usi_refs(usi_b, usi_w):   
    global usib_ref, usiw_ref
    usib_ref = usi_b   
    usiw_ref = usi_w


def get_usi_refs():
    return usib_ref, usiw_ref


# Copy the board position to the clipboard in std SFEN format     
def copy_SFEN_to_clipboard(action):   
    sfen = board_ref.get_sfen()
    copy_text_to_clipboard(sfen) 


# paste a position from the clipboard
def paste_clipboard_to_SFEN(action):    
    sfen = get_text_from_clipboard()
    if sfen is None:
       get_gui_ref().info_box("Error: invalid sfen")       
       return
    if not validate_sfen(sfen):
        get_gui_ref().info_box("Error: invalid sfen")
        return
    load_save_ref = load_save.get_ref()
    load_save_ref.init_game(sfen) 


# lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1
def validate_sfen(sfen):    
    sfenlst = sfen.split()
    num_words = len(sfenlst) 
    if num_words != 3 and num_words !=4:    
        return False

    if num_words == 3:
        board_state, side_to_move, pieces_in_hand = sfenlst
        move_count = '1'
    else:
        board_state, side_to_move, pieces_in_hand, move_count = sfenlst

    # board_state
    ranks = board_state.split('/')
    if len(ranks) != 9:
        print "board state does not have 9 ranks"
        return False

    # side_to_move
    if side_to_move != 'w' and side_to_move != 'b':
        print "invalid side to move"
        return False

    # pieces in hand

    
    # Move Count
    try:
        mc = int(move_count)
    except ValueError:
        print "invalid move count"
        return False    

    return True


def copy_game_to_clipboard(action):
    load_save_ref = load_save.get_ref()   
    gamestr = load_save_ref.get_game()
    copy_text_to_clipboard(gamestr)


def paste_game_from_clipboard(action):
    gamestr = get_text_from_clipboard()
    if gamestr is None:
       print "Error invalid game data"
       return    
    ref = get_psn_ref()
    ref.load_game_psn_from_str(gamestr)


def copy_text_to_clipboard(text):    
    clipboard = gtk.clipboard_get()       # get the clipboard    
    clipboard.set_text(text)              # put the FEN data on the clipboard    
    clipboard.store()                     # make our data available to other applications


def get_text_from_clipboard():    
    clipboard = gtk.clipboard_get()       # get the clipboard     
    text = clipboard.wait_for_text()      # read the text from the clipboard
    return text



