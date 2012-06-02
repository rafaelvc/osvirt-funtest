import os
import sys
import uuid
import utils.imageproc as imageproc

if sys.version_info > (2, 7):
    from collections import OrderedDict
else:
    from ordereddict import OrderedDict

from time import strftime
from datetime import datetime

class TestCase():

    def __init__(self, name, desc):
        self.uniqName = name
        self.description = desc
        self.dictOfScreens = OrderedDict()

class TestResult():

    RESULT_OK,RESULT_FAILED,RESULT_UNKNOWN = 'OK','FAILED','UNKNOWN'
    DATE_FORMAT = '%a, %d %b %Y %H:%M:%S'

    def __init__(self, testCaseName, iso, osHdImage, dtExecStart=None,
                 dtExecEnd=None, failedScreen=None, expectedScreen=None,
                                                        status=RESULT_UNKNOWN):
        self.testCaseName = testCaseName
        self.iso = iso
        self.osHdImage = osHdImage
        self.failedScreen = failedScreen
        self.expectedScreen = expectedScreen
        if dtExecStart is not None and dtExecEnd is not None:
            dtdelta = (datetime(*dtExecEnd[:6]) - datetime(*dtExecStart[:6]))
            self.totalTime = dtdelta.seconds
            self.dateOfExecStart = strftime(TestResult.DATE_FORMAT, dtExecStart )
            self.dateOfExecEnd =  strftime(TestResult.DATE_FORMAT, dtExecEnd )
        else:
            self.totalTime = 0
            self.dateOfExecStart = None
            self.dateOfExecEnd = None
        self.status = status

class Screen():

    def __init__(self, id_=None, name=None, inputs=None, hash_=None, timeout=60, timestamp=0.0,
                 path=None, similarity=None, subRelativePos=None,
                                             subWidth=None, subHeight=None):
        self.uniqName = name
        self.listOfUserInputs = inputs
        self.hashValue = hash_
        self.timeout = timeout
        self.timestamp = float(timestamp)
        self.rawContent = None
        self.similarity = similarity
        self.path = path
        self.subRelativePos = None
        # Relative positivions: botton,top,left,right,center
        # Combinations are allowed, eg.: bottom-left,top-right,center-left
        self.subWitdth = None
        self.subHeight = None
        if id_ is None:
            self.screenId = uuid.uuid4().get_hex()[:6]
        else:
            self.screenId = id_

    def getHash(self):

        if self.hashValue is None:
            self.hashValue = imageproc.calculateHash( self.path )[:5]
        return self.hashValue

    def setPath(self, dir, oldfilename, newfilename=None):

        if newfilename is None:
            newfilename = self.screenId + '.ppm'
        self.path = os.path.join(dir, newfilename)
        os.rename(os.path.join(dir, oldfilename), self.path)


class OperationSystemImage():

    def __init__(self, arch, imgFile, dtLastChange):

        self.arch = arch
        self.imageFile = imgFile
        self.dateLastChange = dtLastChange

class Iso():

    def __init__(self) :
        pass


