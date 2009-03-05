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

import string
import dbClass
import time
from logger import Logger
class songData:
    def __init__(self):
        self.songData = []
        self.max = 7 #count of all possible song data
        self.requiredData = ['Track ID', 'Title', 'Artist', 'Album', 'Track number', 
                             'Duration', 'Use Count']
        self.acceptedDataTypes = ('ISO MPEG-1 Audio Layer 3',)
        self.filetypeReached = False
        self.isSong = False
        self.readyForExport = False
        self.log = Logger(name='Not added to scrobbling db', stream_log=False)

        
    def resetValues(self):
        self.songData = []
        self.filetypeReached = False
        self.isSong = False
        self.readyForExport = False
        
    def _isSong(self, data):
        for item in self.acceptedDataTypes:
            if data.__contains__(item):
                self.isSong = True
        
    def _isData(self, data):
        """Returns true if the data submitted is data we want"""
        for item in self.requiredData:
            if data.__contains__(item):
                return True
        if data.__contains__('Filetype:'):
            self.filetypeReached = True
            self._isSong(data)
        return False
        
    def _isUsecount(self, data):
        if data.__contains__('Use count'):
            return True
        return False
        
    def _cleanData(self, data):
        """Strips unneeded info"""
        index = data.find(":")
        clean_data = data[index+2:-1]
        return clean_data
    
    def _getKey(self, data):
        """returns the key (eg. Album) for a string"""
        key = string.split(data, ':')[0][:-1]
        return key
        
    def newData(self, newData):
        """Needs to find out what data it is and assign 
        it to the correct variable"""
        if self.filetypeReached == True:
            #check if this line is usecount if not we need to append
            if self._isUsecount(newData):
                self.songData.append(self._cleanData(newData))
            else:
                self.songData.append('0 times')
            self.exportData()
            if self.readyForExport == False:
                self.newData(newData)
                
        elif self._isData(newData):
            clean = self._cleanData(newData)
            self.songData.append(clean)
        else:
            pass
            
        
    def checkIfFull(self):
        """Returns true if all songdata is available. Note that Use Count wont exist
        if the song has never been played"""
        if len(self.songData) == self.max:
            return True
        else:
            return False
        
    def checkSongDataCount(self):
        return len(self.songData)
        
    def exportData(self):
        """Sends song data to database"""
        #trim seconds and usecount before export
        if self.isSong == True and self.checkIfFull() and self.songData[5] > 30:
            self._trimExportData()
            self.userFriendlyNames()
            self.readyForExport = True
        else:
            data = '\n'.join(self.songData) 
            self.log.logger.warn(data)
            self.resetValues()
        
    
    def _trimExportData(self):
        self.songData[0] = int(self.songData[0])
        self.songData[4] = int(self.songData[4])
        self.songData[5] = int(string.split(self.songData[5], ' ')[0]) / 1000
        self.songData[6] = int(string.split(self.songData[6], ' ')[0])
        
    def userFriendlyNames(self):
        self.trackid = self.songData[0]
        self.title = self.songData[1]
        self.artist = self.songData[2]
        self.album = self.songData[3]
        self.tracknumber = self.songData[4]
        self.duration = self.songData[5]
        self.usecount = self.songData[6]
