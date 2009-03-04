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

import md5
import time
import urllib
import urllib2
import string
import dbClass
from logger import Logger

class Scrobbler:
    
    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.client = 'tst'
        self.version = '1.0'
        self.url = "http://post.audioscrobbler.com:80"
        self.deletionIds = []
        self.scrobbleCount = 0
        self.log = Logger(name='scrobbling', stream_log_level=2)
        
    def setScrobbleTime(self, time):
        self.scrobbleTime = int(time * 3600)
        
    def _setScrobbleTime(self):
        #depreciated
        """A manual way for setting the time to start scrobbling"""
        print 'Please set the time that the scrobbling was started in hours \
eg. Enter 8.5 if you started listening to the songs 8 and a half hours ago'
        while True:
            s = raw_input('>>> ') 
            try:
                s = int(float(s) * 3600)
                break
            except:
                print 'You didn\'t enter a valid hour value.\n'
        self.log.logger.info('User started listening to current scrobbles %d seconds ago' % s)
        return s
    
    def handshake(self):
        self.timestamp = self.createTimestamp()
        self.authenticationCode = self.createAuthenticationCode()
        self.url += r"/?" +self.encodeUrl()
        try:
            conn = urllib2.urlopen(self.url)
            self.serverResponse = conn.readline().strip()
        except urllib2.URLError:
            return 'NO INTERNET', "Couldn't find Last.fm server"
        if self.serverResponse == 'OK':
            msg = 'User authenticated.'
            self.sessionID = conn.readline()[:-1]
            self.nowPlayingUrl = conn.readline().strip #not used at this time
            self.submissionUrl = conn.readline()[:-1]
        elif self.serverResponse == 'BADAUTH':
            msg = 'Username or password incorrect, please reset'
        elif self.serverResponse == 'BANNED':
            msg = 'This scrobbling client has been banned from submission,\
                  please notify the developer'
        elif self.serverResponse == 'BADTIME':
            msg = 'Timestamp is incorrect, please check your clock settings'
        elif self.serverResponse.startswith('FAILED'):
            msg = 'Connection to server failed:', string.split(response, ' ')[1:]
        return self.serverResponse, msg
        
    def submitTracks(self, c):
        """Takes c, a cursor object with scrobble data and tries to submit it to last.fm"""

        pastTime = int(time.time() - self.scrobbleTime)
        while True:
            cache = c.fetchmany(50)
            if len(cache) == 0:
                break
            else:
                self.scrobbleCount += len(cache)
                #s=<sessionID>  The Session ID returned by the handshake. Required.
                #a[0]=<artist>  The artist name. Required.
                #t[0]=<track>   The track title. Required.
                #i[0]=<time>    The time the track started playing, UNIX timestamp.
                #o[0]=<source>  Put P for this value
                #r[0]=<rating>  Blank or dont use(for now)
                #l[0]=<secs>    The length of the track in seconds. 
                #b[0]=<album>   The album title, or an empty string if not known.
                #n[0]=<tracknumber>The position of the track on the album, or empty.
                #m[0]=music brainz identifier, leave blank
                fullList = [[], [], [], [], [], [], []]
                size = len(cache)
                for track in cache:
                    for index in range(0, len(fullList)):
                        song_data_item = track[index]
                        try:
                            #this is to avoid a unicode to ascii error,
                            #which occours when we try to urlencode accented characters
                            #(umlauts etc.)
                            song_data_item = song_data_item.encode('UTF-8')
                        except AttributeError:
                            #cannot encode integers
                            pass
                        
                        fullList[index].append(song_data_item)
                #remove row ID's which will track which items in scrobble
                #list require deletions
                self.delIds = fullList.pop(0)
                #append extra data to fullList, time, source, musicbrainz tags
                while len(fullList) < 9:
                    fullList.append([])
                for extra in range(0, len(cache)):
                    #append time, use l to work out
                    length = fullList[2][extra]
                    pastTime += int(length)
                    fullList[6].append(pastTime)
                    #append source (always P)
                    fullList[7].append(u"P")
                    #empty strings for music brain tag
                    fullList[8].append(u"")
                    
                postValues = { "s" : self.sessionID }
                for i in range(0, size):
                    dic = self.getDicValue(i)
                    for j in range (0, len(dic)): #haha!
                        postValues[dic[j]] = fullList[j][i]
                postValues = urllib.urlencode(postValues)
                if not self._sendPost(postValues):
                    self.log.logger.critical('Error posting to last.fm')
                    return False
        #if all songs are scrobbled with ok response: 
        return True   
    def getDicValue(self, i):
        """Returns a list of dictionary keys for a specified index"""
        values = "atlbnriom"
        list = []
        for v in values:
            list.append("%s[%d]" % (v, i))
        return list
        
    def _sendPost(self, postValues):
        req = urllib2.Request(url=self.submissionUrl, data=postValues)
        try:
            url_handle = urllib2.urlopen(req)
            response = url_handle.readline().strip()
        except urllib2.URLError:
            response = 'Connection Refused, please try again'
        
        if response == 'OK':
            self.log.logger.info('Scrobbled %d songs' % self.scrobbleCount)
            self.deletionIds.extend(self.delIds)    
            return True
        elif response == 'BADSESSION':
            self.log.logger.critical('Bad session')
            pass
            #handshake again dont delete cache
            return False
        elif response.startswith('FAILED'):
            self.log.logger.critical('Scrobbling Failure:', response)
            return False
        elif response.__contains__('Connection refused'):
            self.log.logger.critical(response)
            return False
   
    def encodeUrl(self):
        u = urllib.urlencode({
            "hs":"true",
            "p":"1.2",
            "c":self.client,
            "v":self.version,
            "u":self.user,
            "t":self.timestamp,
            "a":self.authenticationCode})
        return u
    
    def createAuthenticationCode(self):
        code = md5.new(self.password + self.timestamp).hexdigest()
        return code
    
    def createTimestamp(self):
        stamp = str(int(time.time()))
        return stamp


