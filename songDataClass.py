import string
import re

class songData:
    def __init__(self):
        self.songData = []
        self.max = 7 #count of all possible song data
        self.requiredData = ['Track ID', 'Title', 'Artist', 'Album', 'Track number', 
                             'Duration', 'Use Count']
        self.filetypeReached = False
        
    def _isData(self, data):
        """Returns true if the data submitted is data we want"""
        for item in self.requiredData:
            if data.__contains__(item):
                return True
        if data.__contains__('Filetype:'):
            self.filetypeReached = True
            print self.filetypeReached
                #self.checkFiletype(data)
        return False
        
    def _isUsecount(self, data):
        if data.__contains__('Use count'):
            return True
        return False
        
    def _cleanData(self, data):
        """Strips unneeded info"""
        cleanedData = string.split(data, ': ')
        return cleanedData[1][:-1]
    
    def _getKey(self, data):
        """returns the key (eg. Album) for a string"""
        key = string.split(data, ':')[0][:-1]
        return key
        
    def newData(self, newData):
        """Needs to find out what data it is and assign 
        it to the correct variable"""
        if self.filetypeReached == True:
            print 'is true'
            #check if this line is usecount if not we need to append
            if self._isUsecount(newData):
                self.songData.append(self._cleanData(newData))
            else:
                self.songData.append('0 times')
            self.exportData()
            self.resetValues()
            #run newData again, because we have a new track
            self.newData(newData)
                
        elif self._isData(newData):
            clean = self._cleanData(newData)
            self.songData.append(clean)
        else:
            pass
            
    def checkFiletype(self, filetype):
        """if this is called we are at the end of the song. 
        check that its a valid type mp3, check if use count exists and if not append"""
        print 'calling checkFiletype'
        if self.checkIfFull():
            #use count exists
            print 'all accounted for'
            print self.songData
        elif self.checkSongDataCount() == 6:
            self.songData.append(0)
            print 'use count missing'
            print self.songData

        #resetdata for next song
        self.resetValues()
        
        
    def checkIfFull(self):
        """Returns true if all songdata is available. Note that Use Count wont exist
        if the song has never been played"""
        if len(self.songData) == self.max:
            return True
        else:
            return False
        
    def checkSongDataCount(self):
        return len(self.songData)
    
    def resetValues(self):
        self.songData = []
        self.filetypeReached = False
        
    def exportData(self):
        """Sends song data to database"""
        #trim seconds and usecount before export
        self._trimExportData()
        print self.songData
        
    def _trimExportData(self):
        self.songData[0] = int(self.songData[0])
        self.songData[4] = int(self.songData[4])
        self.songData[5] = int(string.split(self.songData[5], ' ')[0]) / 1000
        self.songData[6] = int(string.split(self.songData[6], ' ')[0])
        
def run():
    trackListing = file('./mtp-tracklisting', 'r')
    sd = songData()
    for line in trackListing.readlines():
        sd.newData(line)

if __name__ == "__main__":
    run()