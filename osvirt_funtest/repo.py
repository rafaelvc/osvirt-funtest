from test import TestCase, Screen, TestResult
from userinput import *
import utils.imageproc as imageproc
import yaml
import os
import uuid
import glob
import shutil
from time import localtime, strftime

__all__ = ['TestCaseRepoManager', 'ScreenRepoManager', 'TestResultRepoManager',
                                       'IsoRepoManager', 'OsHdImageRepoManager']

class IRepoManager :

    def __init__(self) :
        self.repoAddress = None # string
        pass
    def removeItem (self, ) :
        # returns 
        pass
    def addItem (self, ) :
        # returns 
        pass
    def loadItem (self, itemId) :
        # returns IRepoItem
        pass

# class IRepoItem:
#     def __init__(self) :
#         self.itemId = None # string
#         pass

class RepoManager :

    def __init__(self):
        self.repoAddress = None # string
        pass

    @staticmethod
    def listItens(repo):

        if not os.path.exists(repo):
            raise RepoNotFound
        return [ os.path.basename(file)
                 for file in glob.glob( os.path.join( repo, '*.*' )) ]

    @staticmethod
    def removeItem(repo, item):

        itemPath = os.path.join( repo, item )
        if not os.path.exist(itemPath):
            raise ItemNotFound
        os.remove( itemPath )

    @staticmethod
    def update(src, dest):

        try:
            allfiles = glob.glob(os.path.join(src,'*.*'))
            for file in allfiles:
                shutil.copy2(file, dest) # cp -p
        except Exception as e:
            pass

class TestCaseRepoManager(RepoManager, IRepoManager):

    def __init__(self) :
        pass

    @staticmethod
    def addItem(testCase, repo):

        tcaseYaml = {}
        tcaseFile = os.path.join(repo, testCase.uniqName + ".yml")
        if os.path.exists(tcaseFile):
            raise TestCaseFound
        tcaseYaml['uniqname'] = testCase.uniqName
        tcaseYaml['description'] = testCase.description
        screenList = []
        for id_,screen in testCase.dictOfScreens.items():
            screenDict = {}
            screenDict['id'] = id_
            screenDict['name'] = screen.uniqName
            screenDict['hash'] = screen.hashValue
            screenDict['timeout'] = screen.timeout
            screenDict['timestamp'] = screen.timestamp
            if screen.listOfUserInputs is not None:
                inputs = []
                for inp in screen.listOfUserInputs:
                    if inp.__class__.__name__ == 'Keyboard':
                        inputs.append({'keyboard':str(inp.key),'timestamp':inp.timestamp})
                    elif inp.__class__.__name__ == 'Keystream':
                        inputs.append({'keystream':str(inp.keystreamToStr()),'timestamp':inp.timestamp})
                    elif inp.__class__.__name__ == 'Mouse':
                        pass
                screenDict['userinput'] = inputs
            screenList.append(screenDict)
        tcaseYaml['screens'] = screenList
        with open(tcaseFile, 'w') as foutput:
            foutput.write(yaml.dump(tcaseYaml, default_flow_style=False, indent=4))

    @staticmethod
    def loadItem(nameItem, repo):

        tcaseFile = os.path.join(repo, nameItem + ".yml")
        if not os.path.exists(tcaseFile):
            raise TestCaseNotFound
        with open(tcaseFile) as yfstream:
            yamlobj = yaml.load(yfstream)
            testCase = TestCase(name=yamlobj['uniqname'],
                                desc=yamlobj['description'])
            for screenInfo in yamlobj['screens']:
                inputList = []
                if screenInfo.has_key('userinput'):
                    userInput = screenInfo['userinput']
                    for inp in userInput:
                        if inp.has_key('timestamp'):
                            timestamp = inp['timestamp']
                        else:
                            timestamp = 0.0
                        # TODO: better handling for input types
                        if inp.has_key('keyboard'):
                            inputObj = Keyboard( key=inp['keyboard'], timestamp=timestamp )
                        elif inp.has_key('keystream'):
                            inputObj = Keystream( keystream=inp['keystream'], timestamp=timestamp )
                        elif inp.has_key('mouse'):
                            inputObj = Mouse( inp['mouse'], timestamp=timestamp )
                        else:
                            raise UnknownInput
                        inputList.append( inputObj )
                sim = None
                if screenInfo.has_key('similarity'):
                    sim = float(screenInfo['similarity'])
                screenObj = Screen(id_=screenInfo['id'], name=screenInfo['name'], inputs=inputList,
                        hash_=screenInfo['hash'],timeout=screenInfo['timeout'], similarity=sim,
                        timestamp=screenInfo['timestamp'])
                testCase.dictOfScreens[screenInfo['id']] = screenObj
        return testCase


class TestResultRepoManager(RepoManager, IRepoManager) :

    def __init__(self) :
        pass

    @staticmethod
    def addItem(testResult, sessionDir, repo) :

        def copyIfExists(file_, dir_):
            if os.path.exists(file_):
                shutil.copy(file_, dir_)

        resultInfo = { 'Test case name' : testResult.testCaseName,
              'Iso file'       : testResult.iso,
              'Image file'     : testResult.osHdImage,
              'Start date'     : testResult.dateOfExecStart,
              'Finish date'    : testResult.dateOfExecEnd,
              'Total time'     : testResult.totalTime,
              'Status'         : testResult.status }

        if testResult.status == TestResult.RESULT_FAILED:
            resultInfo['Expected screen'] = testResult.expectedScreen.hashValue
            if testResult.failedScreen is not None:
                resultInfo['Failed screen'] = testResult.failedScreen.hashValue

        # Temp solution for filesystem + yaml as database backend
        resultDir = os.path.join(repo, uuid.uuid4().get_hex()[:6])
        os.mkdir(resultDir)
        with open(os.path.join(resultDir, 'resultinfo.yml'),'w') as fresult:
            fresult.write(yaml.dump(resultInfo, default_flow_style=False,
                                                                      indent=4))
        imageproc.generateOgv(os.path.join(sessionDir,'screen-tmp'),
                                          os.path.join(resultDir,'session.ogv'))
        log = os.path.join(sessionDir, 'session.log')
        copyIfExists(log, resultDir)
        failScreen = os.path.join(sessionDir, 'failscreen.ppm')
        copyIfExists(failScreen, resultDir)
        virtPlayerlog = os.path.join(sessionDir, 'virtplayer.log')
        copyIfExists(virtPlayerlog, resultDir)

#        video = os.path.join(sessionDir, 'session.ogv')
#        copyIfExists(video, resultDir)

    @staticmethod
    def listItens(repo, filterByTestCase=None, filterByIso=None,
                                                        filterByOsHdImage=None):
        def result_format(resultId, result):
            return (resultId, ( result['Test case name'], result['Iso file'],
                     result['Image file'], result['Start date'],
                 result['Finish date'], result['Total time'], result['Status'] ))

        resultDirs = [dir for dir in os.listdir(repo) if os.path.isdir(
                                                        os.path.join(repo,dir))]
        results = []
        for resultDir in resultDirs:
            with open(os.path.join(repo,
                                   resultDir,'resultinfo.yml')) as fyamlresult:
                yamlobj = yaml.load(fyamlresult)
                results.append((resultDir, yamlobj))
        results = [ result_format(resultid,result) for resultid,result in results ]
        if filterByTestCase is not None:
            results = [ result_format(resultid, result) for resultid,result in results
                      if result['Test case name'] == filterByTestCase]
        if filterByIso is not None:
            results = [ result_format(resultid, result) for resultid,result in results
                      if result['Iso file'] == filterByIso]
        if filterByOsHdImage is not None:
            results = [ result_format(resultid, result) for resultid,result in results
                      if result['Image file'] == filterByOsHdImage]
        return results


class IsoRepoManager(RepoManager, IRepoManager):

    def __init__(self) :
        pass
    def addItem (self) :
        # returns 
        pass

class OsHdImageRepoManager(RepoManager, IRepoManager):

    def __init__(self):
        pass
    def addItem (self):
        # returns 
        pass

class ScreenRepoManager(RepoManager, IRepoManager):

    def __init__(self):
        pass
    def addItem (self):
        # returns 
        pass
    def loadItem (self):
        # returns 
        pass

    def createTmpDir(self, basedir):
        pass

class SessionManager(RepoManager, IRepoManager):

    def __init__(self) :
        pass

    @staticmethod
    def listItens(repo):

        def sessionInfo_format(sessionId, sessionInfo, playerInfo):
            return (sessionId, ( sessionInfo['TestCase'], sessionInfo['Iso'],
             sessionInfo['OsHdImage'], sessionInfo['Stage'], 
             sessionInfo['Progress'], sessionInfo['Last Update'], playerInfo['vncport']))

        if not os.path.exists(repo):
            raise RepoNotFound

        itwalk = os.walk(repo)
        rootdir,sessions,files = itwalk.next()
        sessionsInfo = []
        for session in sessions:
            runtimepath = os.path.join(repo, session, 'runtimeinfo.yml')
            if not os.path.exists(runtimepath):
                continue
            with open(runtimepath) as rtfp:
                yamlsession = yaml.load(rtfp)
                playerinfo = os.path.join(repo, session, 'playerinfo.yml')
                with open(playerinfo) as rtpfp:
                    yamlplayer = yaml.load(rtpfp)
                    sessionsInfo.append((session[:6], yamlsession, yamlplayer))

        sessionsInfo = [ sessionInfo_format(sessionId, sessionInfo, yamlplayer)
                                   for sessionId,sessionInfo,yamlplayer in sessionsInfo ]
        return sessionsInfo


    def addItem (self) :
        # returns 
        pass

