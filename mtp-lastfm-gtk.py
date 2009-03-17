#!/usr/bin/env python

# Copyright 2009 Daniel Woodhouse
#
#This file is part of mtp-lastfm.
#
#mtp-lastfm is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#mtp-lastfm is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with mtp-lastfm.  If not, see http://www.gnu.org/licenses/

import os
import sys
import re
import md5
import gtk
import pygtk
import gtk.glade
pygtk.require("2.0")

import dbClass
from songdata import SongData
import scrobbler
import songview
import webservices

__author__ = ("Daniel Woodhouse",)
__version__ = "0.6"
__test_mode__ = False #disables the authentication and scrobbling section for offline work
__std_err_log__ = False #Log stderr messages to ~/.mtp-lastfm/error.log


def get_path():
    if "dev" in __version__:
        print 'Development version'
    return os.path.dirname(__file__)

class MTPLastfmGTK:
    def __init__(self):
        
        self.HOME_DIR = os.path.join(os.environ['HOME'], ".mtp-lastfm") + os.sep
        self.MAIN_PATH = get_path()
        
        self.MAIN_GLADE = os.path.join(self.MAIN_PATH, "glade", "gui.glade")
        self.CACHE_GLADE = os.path.join(self.MAIN_PATH, "glade", "cache.glade")
        self.BANNED_GLADE = os.path.join(self.MAIN_PATH, "glade", "ban.glade")
        self.LOVED_GLADE = os.path.join(self.MAIN_PATH, "glade", "loved.glade")
        self.LOG_GLADE = os.path.join(self.MAIN_PATH, "glade", "log.glade")
        
        try:
            os.mkdir(self.HOME_DIR)
        except OSError:
            pass
        
        if __std_err_log__:
            sys.stderr = open(os.path.join(self.HOME_DIR, "error.log"), 'a')
        
        self.tree = gtk.glade.XML(self.MAIN_GLADE)
        event_handlers = {
            "on_main_window_destroy" : gtk.main_quit,
            "on_login_window_destroy" : gtk.main_quit,
            "on_login_clicked" : self.on_login_clicked,
            "on_logout_clicked" : self.on_logout_clicked,
            "on_username_entry_focus_out_event" : self.on_username_entry_focus_out_event,
            "on_password_entry_key_press_event" : self.on_password_entry_key_press_event,
            "on_check_device_clicked" : self.on_check_device_clicked,
            "on_scrobble_clicked" : self.on_scrobble_clicked,
            "on_scrobble_time_entered_clicked" : self.on_scrobble_time_entered_clicked,
            "on_options_clicked" : self.on_options_clicked,
            "on_apply_options_clicked" : self.on_apply_options_clicked,
            "on_cancel_options_clicked" : self.on_cancel_options_clicked,
            "on_cache_clicked" : self.on_cache_clicked,
            "on_banned_tracks_clicked" : self.on_banned_tracks_clicked,
            "on_loved_tracks_clicked" : self.on_loved_tracks_clicked,
            "on_about_clicked" : self.on_about_clicked,
        }
        self.tree.signal_autoconnect(event_handlers)
        
        self.main_window = self.tree.get_widget("main_window")
        self.options_window = self.tree.get_widget("options_window")
        self.login_window = self.tree.get_widget("login_window")
        
        about_dialog = self.tree.get_widget("about_dialog")
        about_dialog.set_version(__version__)
        about_dialog.set_authors(__author__)

        self.usersDB = dbClass.lastfmDb_Users(self.HOME_DIR)
        current_user = self.usersDB.get_users()
        self.show_login_window()
        if current_user is not None:
            self.username = current_user[0]
            self.password = current_user[1]
            if self.authenticate_user():
                self.setup_user_session()
            else:
                self.tree.get_widget("login_error").set_text(self.authentication_error)
    
    def links(dialog, link, user_data):
        print link, user_data
      
    def show_main_window(self):
        self.login_window.hide()
        self.write_info("User authenticated.", clear_buffer=True)
        self.main_window.show()
        while gtk.events_pending():
            gtk.main_iteration(False)
        
    def show_options_window(self):
        self.options_window.show()
        
    def show_login_window(self):
        self.main_window.hide()
        self.login_auto_completer()
        self.login_window.show()
        
    
    # This section deals with the MAIN WINDOW
        
    def on_logout_clicked(self, widget):
        self.tree.get_widget("username_entry").set_text("")
        self.tree.get_widget("password_entry").set_text("")
        self.tree.get_widget("login_error").set_text("")
        self.show_login_window()
    
    def on_check_device_clicked(self, widget):
        self.write_info("Connecting to MTP device...")
        if not __test_mode__:
            os.system("mtp-tracks > " + self.HOME_DIR + "mtp-dump_" + self.username)
        f = file(self.HOME_DIR + "mtp-dump_" + self.username, 'r').readlines()
        if len(f) < 3:
            self.write_info("MTP Device not found, please connect")
        else:
            self.write_info("Done.", new_line=" ")
            self.write_info("It is now safe to remove your MTP device\nCross checking song data with local database...")
            self.song_db.pending_scrobble_list = None
            song_obj = SongData(self.song_db, self.HOME_DIR, self)
            for line in f:
                song_obj.check_new_data(line)
            self.song_db.pending_scrobble_list = None
            if song_obj.song_count % 100 != 0:
                self.write_info("%d tracks checked" % song_obj.song_count)
            self.write_info("Complete.")
            if song_obj.error_count > 0:
                self.write_info("%d items were not added to your song database." % song_obj.error_count)
                
                buffer = self.tree.get_widget("info").get_buffer()
                iter = buffer.get_end_iter()
                anchor = buffer.create_child_anchor(iter)
                button = gtk.Button(label=None, stock="gtk-info")
                button.show()
                self.tree.get_widget("info").add_child_at_anchor(button, anchor)
                button.connect("clicked", self.show_error_details, "songdata")
            self.song_db.update_scrobble_count()
            self.set_button_count()
    
    def show_error_details(self, widget, data):
        if data is "songdata":
            tree = gtk.glade.XML(self.LOG_GLADE)
            f = open(self.HOME_DIR + "db.log", "r").read()
            self.write_info(new_info=f, text_widget=tree.get_widget("text_view"),
                            clear_buffer=True)
            tree.get_widget("window").show()
    
    def set_button_count(self):
        """Checks if we should set a value for a button or disable it"""
        buttons = {
            "loved_tracks" :
                [len(self.song_db.return_pending_love().fetchall()),
                "loved_label"],
            
            "banned_tracks" :
                [len(self.song_db.return_tracks("B").fetchall()),
                "banned_label"],
                
            "cache" :
                [self.song_db.scrobble_counter,
                "cache_label"]}
        
        for key, value in buttons.items():
            if value[0] is 0:
                sensitivity = False
                text = ""
            else:
                sensitivity = True
                text = "(" + str(value[0]) + ")"
            
            self.tree.get_widget(value[1]).set_text(text)
            self.tree.get_widget(key).set_sensitive(sensitivity)
   
    def authenticate_user(self):
        """This authenticates the user with last.fm ie. The Handshake"""
        #disable all buttons etc
        self.tree.get_widget("login_window").set_sensitive(False)
        self.tree.get_widget("username_entry").set_text(self.username)
        self.tree.get_widget("password_entry").set_text(self.password)
        self.tree.get_widget("login_error").set_text("Authenticating...")
        while gtk.events_pending():
            gtk.main_iteration(False)
        self.scrobbler = scrobbler.Scrobbler(self)
        if __test_mode__:
            server_response = "OK"
        else:
            server_response, msg = self.scrobbler.handshake()
        self.tree.get_widget("login_window").set_sensitive(True)
        if server_response == "OK":
            self.session_key = self.usersDB.get_session_key(self.username)
            return True
        else:
            self.authentication_error = msg
            return False
            
    
    def on_scrobble_clicked(self, widget):
        """Scrobbles tracks to last.fm"""
        #show scrobble dialog, if user has indicated in preferences
        if self.options.return_option("use_default_time") == True:
            scr_time = self.options.return_option("scrobble_time")
            self.continue_scrobbling = True
        else:
            self.continue_scrobbling = True
            self.show_scrobble_dialog()
        if self.continue_scrobbling is True:
            scr_time = self.tree.get_widget("scrobble_time_manual").get_value()
            self.scrobble(scr_time)
            self.love_tracks()
                
    def scrobble(self, scr_time):
        self.scrobbler.set_scrobble_time(scr_time)
        scrobble_list = self.song_db.return_scrobble_list(self.options.return_scrobble_ordering())
        if self.scrobbler.submit_tracks(scrobble_list):
                self.song_db.delete_scrobbles('all')
        else:
            self.song_db.delete_scrobbles(self.scrobbler.deletion_ids)                
        self.write_info("Scrobbled " + str(self.scrobbler.scrobble_count) +" Tracks")
        
    def love_tracks(self):
        """This should be called after scrobbling in order to love pending tracks
        I'm not sure if this is the best place for it since it may be time consuming
        if there is a whole lotta love... den den da da da da den"""
        if not self.session_key:
            return False
        love_cache = self.song_db.return_love_cache()
        webservice = webservices.LastfmWebService()
        loved = []
        if love_cache is not None:
            self.write_info("Sending love...")
            for item in love_cache:
                if webservice.love_track(item[1], item[2], self.session_key):
                    self.write_info(item[1] + " - " + item[2])
                    loved.append(item[0])
            self.song_db.mark_as_love_sent(loved)
            self.write_info("Done.")
        self.set_button_count()
    
    
    def show_scrobble_dialog(self):
        self.tree.get_widget("scrobble_time_manual").set_value(self.options.return_option("scrobble_time"))
        response = self.tree.get_widget("scrobble_dialog").run()
        while gtk.events_pending():
            gtk.main_iteration(False)
        if response == gtk.RESPONSE_DELETE_EVENT or response == gtk.RESPONSE_CANCEL:
            self.tree.get_widget("scrobble_dialog").hide()
            self.continue_scrobbling = False
    
    def on_scrobble_time_entered_clicked(self, widget):
        self.tree.get_widget("scrobble_dialog").hide()
        
   
    def on_cache_clicked(self, widget):
        cache_window = songview.CacheWindow(self.CACHE_GLADE, self.song_db, self)
    
    def on_banned_tracks_clicked(self, widget):
        banned_window = songview.BannedWindow(self.BANNED_GLADE, self.song_db, self)
        
    def on_loved_tracks_clicked(self, widget):
        loved_window = songview.LovedWindow(self.LOVED_GLADE, self.song_db, self)

    def write_info(self, new_info, text_widget="Default",
                   new_line='\n', clear_buffer=False):
        """Writes data to the main window to let the user know what is going on"""
        if text_widget is "Default":
            text_widget = self.tree.get_widget("info")
        buffer = text_widget.get_buffer()
        if clear_buffer is True:
            buffer.set_text(new_info)
        else:
            start, end = buffer.get_bounds()
            info = buffer.get_text(start, end)
            if info is None:
                buffer.set_text(new_info)
            else:
                buffer.set_text(info + new_line + new_info)
        while gtk.events_pending():
            gtk.main_iteration(False)




    #menu options
    def on_options_clicked(self, widget):
        for o in self.options.options_list:
            try:
                self.tree.get_widget(o).set_active(self.options.return_option(o))
            except AttributeError:
                self.tree.get_widget(o).set_value(self.options.return_option(o))
        self.options_window.show()
    
    
    #This section deals with the LOGIN WINDOW
    def on_username_entry_focus_out_event(self, widget, key):
        entry = self.tree.get_widget("username_entry").get_text()
        user = self.usersDB.user_exists(entry)
        if user is not False:
            self.tree.get_widget("password_entry").set_text(user[1])
        
    def on_login_clicked(self, widget):
        self.username = self.tree.get_widget("username_entry").get_text()
        self.password = self.tree.get_widget("password_entry").get_text()
        remember_password = self.tree.get_widget("remember_password").get_active()
        
        if self.username == '' or self.password == '':
            login_error = self.tree.get_widget("login_error")
            login_error.set_text("Error: Please enter a username and password")
        else:
            if not re.findall(r"^([a-fA-F\d]{32})$", self.password):
                self.password = md5.new(self.password).hexdigest()
            if self.authenticate_user():
                if remember_password is True:
                    self.usersDB.update_user(self.username, self.password)
                else:
                    self.usersDB.remove_user(self.username)
                self.setup_user_session()
            else:
                self.show_login_window()
                self.tree.get_widget("login_error").set_text(self.authentication_error)
    
    def setup_user_session(self):
        self.tree.get_widget("user").set_text(self.username)
        self.options = Options(self.username, self.usersDB)
        if not os.path.exists(self.HOME_DIR + self.username + 'DB'):
            self.write_info("User db doesn't exist, creating.")
            create_new = True
        else:
            create_new = False
        self.song_db = dbClass.lastfmDb(self.HOME_DIR + self.username + "DB", create_new)
        self.set_button_count()
        self.show_main_window()
        if self.options.return_option("startup_check") == True:
            self.on_check_device_clicked("x")
        if self.options.return_option("auto_scrobble") == True:
            self.on_scrobble_clicked("x")
        
        
    def on_username_entry_insert_text(self, widget):
        """Check the user database on keypress to see if we have a match"""
        entry = self.tree.get_widget("username_entry").get_text()
        users = self.usersDB.get_users_like(entry)
        if len(users) is 1:
            self.tree.get_widget("username_entry").set_text(users[0][0])
            #we need to select the text after the cursor so the user can continue
            #writing without mistakes
    
    def on_password_entry_key_press_event(self, widget, key):
        if key.keyval == 65293:
            self.on_login_clicked(widget)
            
    def login_auto_completer(self):
        self.completion = gtk.EntryCompletion()
        self.completion.set_inline_completion(True)
        self.completion.set_popup_completion(False)
        self.tree.get_widget("username_entry").set_completion(self.completion)
        liststore = gtk.ListStore(str)
        self.completion.set_model(liststore)
        pixbufcell = gtk.CellRendererPixbuf()
        self.completion.pack_start(pixbufcell)
        self.completion.add_attribute(pixbufcell, 'pixbuf', 3)
        self.completion.set_text_column(0)
        users = self.usersDB.get_users(all=True)
        for user in users:
            liststore.append([user[0]])
    
    #this section deals with the OPTIONS WINDOW
    def on_cancel_options_clicked(self, widget):
        self.options_window.hide()
        
    
    def on_apply_options_clicked(self, widget):
        random = self.tree.get_widget("random").get_active()
        alpha = self.tree.get_widget("alphabetical").get_active()
        startup_check = self.tree.get_widget("startup_check").get_active()
        auto_scrobble = self.tree.get_widget("auto_scrobble").get_active()
        scrobble_time = self.tree.get_widget("scrobble_time").get_value()
        use_default_time = self.tree.get_widget("use_default_time").get_active()
        self.options.update_options(random, alpha,
                                    startup_check, auto_scrobble,
                                    scrobble_time, use_default_time)
        self.options_window.hide()
        
    
    #About Window
    def on_about_clicked(self, widget):
        response = self.tree.get_widget("about_dialog").run()
        if response == gtk.RESPONSE_DELETE_EVENT or response == gtk.RESPONSE_CANCEL:
            self.tree.get_widget("about_dialog").hide()
        
class Options:
    def __init__(self, username, db):
        self.options_list = ("random", "alphabetical", "startup_check",
                        "auto_scrobble", "scrobble_time", "use_default_time")
        self.db = db
        self.username = username
        self.reset_default()
        self.reset_options()
    
    def update_options(self, *args):
        self.db.update_options(self.username, *args)
        self.reset_options()
    
    def reset_options(self):
        options = self.db.retrieve_options(self.username)
        if options is None:
            self.username = "default"
            options = self.db.retrieve_options(self.username)
        self.dic_options = self.create_option_dic(options)
        
    def return_scrobble_ordering(self):
        if self.return_option("random") == True:
            return "RANDOM()"
        else:
            return "songs.artist"
    
    
    def reset_default(self):
        self.db.reset_default_user()
        
    def create_option_dic(self, options):
        dic = {}
        for o in range(0, len(self.options_list)):
            dic[self.options_list[o]] = options[o]
        return dic
    
    def return_option(self, option_name):
        return self.dic_options[option_name]
        
        
if __name__ == "__main__":
    mtp = MTPLastfmGTK()
    gtk.main()


