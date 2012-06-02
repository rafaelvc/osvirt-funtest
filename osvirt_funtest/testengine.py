import sys
import os
import uuid
import yaml
import shutil
import logging
from time import localtime, strftime, sleep, time
from ConfigParser import SafeConfigParser
from threading import Thread
from Queue import Queue, Empty
# import pdb

from test import TestCase, TestResult, Screen
import utils.imageproc as imageproc
from repo import *
import virt

INSTALL_DIR='/home/rafael/osimage-autotest'

class TestEngine(object):

    def __init__(self, cmdOpts) :

        self.engineConfig = {}
        self.virtPlayerConfig = {}
        self._loadConfig()
        self.commandOptions = cmdOpts
        self.sessionId = None
        self.sessionPath = None
        self.sessionScreenPath = None
        self.testCase = None
        self.iso = None
        self.osHdImage = None
        self._screencont = 0

        self.shootThread = None

        # It's thread-safe
        self.screenQueue = Queue()

        for repo in ('iso','testcase','testresult','screen','oshdimage'):
            self.engineConfig[repo+'-repo'] = os.path.join(INSTALL_DIR,
                                                self.engineConfig[repo+'-repo'])
        self.engineConfig['var-dir'] = os.path.join(INSTALL_DIR,
                                                   self.engineConfig['var-dir'])

#    @testing_session
    def executeTest(self):

        testCaseName = self.commandOptions.test_case
        self.testCase = TestCaseRepoManager.loadItem(testCaseName,
                                             self.engineConfig['testcase-repo'])
        failedScreen = None
        expectedScreen = None
        self._screencont = 0
        result = True
        status = TestResult.RESULT_OK
        dtExecStart = localtime()
        self._createTestSession()
        for id,screen in self.testCase.dictOfScreens.items():
            self._updateTestSessionInfo(self.testCase, screen)
            result,lastScreen = self._waitScreen(screen, self.sessionScreenPath)
            if not result:
                failedScreen = lastScreen
                expectedScreen = screen
                if lastScreen is not None:
                    shutil.copy(failedScreen.path, os.path.join(self.sessionPath,
                                                             'failscreen.ppm') )
                status = TestResult.RESULT_FAILED
                break
            elif screen.listOfUserInputs:
                print  'sent', screen.hashValue, screen.listOfUserInputs
                firstinp = screen.listOfUserInputs[0]
                if firstinp.timestamp > 0.0:
                    firstinp.timestamp-screen.timestamp
                    sleep(firstinp.timestamp-screen.timestamp)
                    self.virtPlayer.sendUserInput( screen.listOfUserInputs )
            print screen.hashValue
        dtExecEnd = localtime()
        tcaseResult = TestResult( testCaseName, dtExecStart=dtExecStart,
                                  dtExecEnd=dtExecEnd,
                                  iso=os.path.basename(
                                                 self._noneToNullStr(self.iso)),
                                  osHdImage=os.path.basename(self.osHdImage),
                                  failedScreen=failedScreen,
                                  expectedScreen=expectedScreen, status=status)
        logging.info('Session finished.')
        TestResultRepoManager.addItem(tcaseResult, sessionDir=self.sessionPath,
                                        repo=self.engineConfig['testresult-repo'])
        self._finalizeTestSession()

 #   @testing_session
    def recordTest(self):
        """ Note: this function does not need to be a thread 
        consumer of screens, however whether some processing during
        the screens capture is required it is already prepared for such case"""
        testCaseName = self.commandOptions.test_case
        testCase = TestCase(name=testCaseName, desc=None)
        # A general timeout for the whole record session ?
        # recordtimeout = int(self.engineConfig['record-session-timeout'])
        inputEvents = []
        screens = []
        self._createTestSession()
        while True:
            try:
                #blocks until a screen or None is available
                currentscreen = self.screenQueue.get(block=True)
                if currentscreen is None:
                    break
                events = self.virtPlayer.getUserInputEvents()
                if events:
                    inputEvents += events
                screens.append( currentscreen )
                self._updateRecordSessionInfo( currentscreen )
            except Exception as e:
                print e
                break
        if not screens:
            raise RecordWithoutScreen
        self.removeBlackListedScreens( screens )
        logging.info('Dropping blacklisted screens complete.')
        self.removeSimilarScreens(testCase, screens)
        logging.info('Removing similar screens complete.')
        self.applyEventsForScreens(testCase, inputEvents)
        logging.info('Events on screens processing complete.')
        self.doTimeoutForScreens(testCase)
        logging.info('Timeout for screens processing complete.')
        TestCaseRepoManager.addItem(testCase,self.engineConfig['testcase-repo'])
        ScreenRepoManager.update(self.sessionScreenPath,
                                               self.engineConfig['screen-repo'])
        self._finalizeTestSession()
        return testCase

    def removeBlackListedScreens(self, screens):

        # TODO: read from a file at least
        # little screen appearing durint the boot unable to be 
        # detected on test and some black screens
        print screens
        blacklist = ['2c818','007d9','8e1be','b7229']
        for screen in screens:
            if screen.getHash() in blacklist:
                screens.remove(screen)

    def removeSimilarScreens(self, testcase, screens):

        if not screens:
            return
        nrscr = len(screens)
        screensrc = screens[0]
        testcase.dictOfScreens[screensrc.screenId] = screensrc
        if nrscr == 1:
            return
        ixdest = 1
        while ixdest < nrscr:
            screendest = screens[ixdest]
            if not self._compareScreen(screensrc, screendest)[1]:
                testcase.dictOfScreens[screendest.screenId] = screendest
                screensrc = screens[ixdest]
            ixdest += 1

    def doTimeoutForScreens(self, testcase, timeoutdelay=5):

        screens = testcase.dictOfScreens.items()
        firstscreen = screens[0][1]
        firstscreen.timeout = timeoutdelay
        start_t = firstscreen.timestamp
        for id_,screen in screens[1:]:
            screen.timeout = int((screen.timestamp - start_t) + timeoutdelay)

    def applyEventsForScreens(self, testcase, inputEvents):

        if not inputEvents:
            return
        screens = testcase.dictOfScreens.items()
        ix = 0
        for id_,screen in screens:
            if not inputEvents:
                break
            screen.listOfUserInputs = []
            try:
                id_,nextscreen = screens[ix+1]
            except IndexError:
                while inputEvents:
                    screen.listOfUserInputs.append(inputEvents[0])
                    inputEvents = inputEvents[1:]
                return
            for ev in inputEvents:
                if (ev.timestamp >= screen.timestamp and
                    ev.timestamp < nextscreen.timestamp):
                    screen.listOfUserInputs.append(ev)
                    inputEvents = inputEvents[1:]
                else:
                    break
            ix += 1

    def screenShootProducer(self, dir_, delay, timeout=3600):

        start_t = time()
        current_t = time()
        while (current_t - start_t) <= timeout:
            try:
                self.virtPlayer.takeScreenshot(dir_)
                currentscreen = self._getCurrentScreen(dir_, False)
                currentscreen.timestamp = current_t
                # TODO: figure out the screen timeout, should be the 
                # wasted time in the screen plus some delay - default = 60
                self.screenQueue.put(currentscreen)
            except virt.VirtPlayerShutdown:
                # works out screens production and makes consumer 
                # threads to unblock
                print 'Shutdown catched'
                self.screenQueue.put(None)
                break
            except Exception as e:
                break
            sleep(delay)
            current_t = time()
            # timestamp_sec = int(tm)
            # timestamp_microsec = int((tm-timestamp_sec)*1000000)
        logging.info('Shoot thread finished.')

    def _createTestSession(self):

        iso = self.commandOptions.iso
        oshdimg = self.commandOptions.oshd_image
        storehdimg = self.commandOptions.store_oshd_image
        specdesc = self.commandOptions.desc_oshdimage

        self.sessionId = uuid.uuid4().get_hex()
        self.sessionPath = os.path.join(self.engineConfig['var-dir'],
                                                    self.sessionId + '-session')
        try:
            self.virtPlayer = self._virtPlayerFactory()
            # Creates session dir and jump to it
            os.mkdir( self.sessionPath )
            self.sessionScreenPath = os.path.join(self.sessionPath,'screen-tmp')
            os.mkdir( self.sessionScreenPath )
            base_dir = os.path.abspath(os.curdir)
            os.chdir( self.sessionPath )
            logging.basicConfig(filename='session.log',level=logging.INFO, 
                                      format='INFO:%(asctime)-15s: %(message)s')
            logging.info('Session started.')

            # Prepare ISO
            isoPath = None
            if iso is not None:
                isoPath = os.path.join(self.engineConfig['iso-repo'], iso)
                if not os.path.exists(isoPath):
                    raise IsoNotFound
                os.symlink( isoPath, iso)
                isoPath = os.path.join( self.sessionPath, iso )
            self.iso = isoPath
            # Prepare os hd image 
            oshdimgName = self._generateHdName(specdesc, iso, oshdimg)
            if storehdimg and oshdimgName in OsHdImageRepoManager.listItens(
                                           self.engineConfig['oshdimage-repo']):
                    raise OsHdImageAlready('Try a new os hd image desc.')
            oshdimgPath = os.path.join(self.sessionPath, oshdimgName)
            if oshdimg is None:
                # Since there isn't hd provided we will create one 
                self.virtPlayer.createHdImage( oshdimgPath )
                logging.info('New hd image created: %s.', oshdimgName)
            else:
                # Copy renaming hd so it is able to go to repo if required
                srchdfile = os.path.join(self.engineConfig['oshdimage-repo'],
                                                                       oshdimg)
                desthdfile = oshdimgPath
                self.virtPlayer.createHdImageDisposable(srchdfile, desthdfile)
            os.chdir( base_dir )
            self.virtPlayer.play(isoPath, oshdimgPath)
            self.osHdImage = oshdimgPath

            #Start screenshot thread 
            self.shootThread = Thread(target=self.screenShootProducer,
                                            args=(self.sessionScreenPath,0.5))
            self.shootThread.start()
            logging.info('Shoot thread started.')

        except OSError:
            pass
        except virt.VirtPlayerError as e:
            sys.stdout.write('Session info: %s\n%s' %(e[0]['sessionId'], e[1]))
            sys.exit(1)

    def _finalizeTestSession(self):

        try:
            self.virtPlayer.quit()
            if self._hasOption('store_oshd_image'):
                # the new image is diffrent from existent ones,
                # see generateHdName
                shutil.move(self.osHdImage, self.engineConfig['oshdimage-repo'])
            shutil.rmtree( self.sessionPath )
        except:
            raise

    def _updateRecordSessionInfo(self, currentScreen):

        runTimeInfo = {'TestCase' : 'RECORD MODE',
                       'Stage': '%s-%s' % (currentScreen.hashValue,
                                                        currentScreen.uniqName),
                       'Progress': '0.0%',
                       'Last Update' : strftime('%a, %d %b %Y %H:%M:%S',
                                                                   localtime())}
        if self.iso is not None:
            runTimeInfo['Iso'] = os.path.basename(self._noneToNullStr(self.iso))
        else:
            runTimeInfo['Iso'] = ''
        if self.osHdImage is not None:
            runTimeInfo['OsHdImage'] = os.path.basename(self.osHdImage)
        else:
            runTimeInfo['OsHdImage'] = ''

        with open(os.path.join(self.sessionPath, 'runtimeinfo.yml'),'w') as fruntime:
            fruntime.write(yaml.dump(runTimeInfo))


    def _updateTestSessionInfo(self, testCase, currentScreen):

        total = float(len(testCase.dictOfScreens.keys()))
        screenNumber = testCase.dictOfScreens.keys().index(
                                                        currentScreen.screenId)
        runTimeInfo = {'TestCase' : self.testCase.uniqName,
                       'Iso': os.path.basename(self._noneToNullStr(self.iso)),
                       'OsHdImage': os.path.basename(self.osHdImage),
                       'Stage': '%s-%s' % (currentScreen.hashValue,
                                                        currentScreen.uniqName),
                       'Progress': '%.2f%%' % (((screenNumber + 1)/total)*100),
                       'Last Update' : strftime('%a, %d %b %Y %H:%M:%S',
                                                                   localtime())}
        with open(os.path.join(self.sessionPath, 'runtimeinfo.yml'),'w') as fruntime:
            fruntime.write(yaml.dump(runTimeInfo))

    def _generateHdName(self, specdesc=None, iso=None, oshdimage=None):
        """ Os hd image file name format: <DESC>_<SPEC-DESC>_<ARCH>.img 
            Iso file name format:  <DESC>.<ARCH>.iso """

        if oshdimage is not None:
            withoutext = os.path.splitext(oshdimage)[0]
            desc,oldspecdesc,arch = withoutext.split('_')
        elif iso is not None:
            withoutext = os.path.splitext(iso)[0]
            desc,arch = withoutext.split('.')
        else:
            raise Exception('Requires either iso or oshdimage parameters.')

        if specdesc is None:
            specdesc = ''
        else:
            specdesc = specdesc + '_'
        return desc + '_' + specdesc + arch + '.img'


    def showAvailableIsos (self):

        iso = None
        sys.stdout.write('Avilable isos:\n')
        for iso in IsoRepoManager.listItens(self.engineConfig['iso-repo']):
            sys.stdout.write('%s \n' % iso)
        if iso is None:
            sys.stdout.write('There are not isos in the repo: %s \n'
             % self.engineConfig['iso-repo'])

    def showAvailableTestCases(self):

        testCase = None
        sys.stdout.write('Avilable test cases:\n')
        for testCase in TestCaseRepoManager.listItens(
                                            self.engineConfig['testcase-repo']):
            sys.stdout.write('%s \n' % testCase)
        if testCase is None:
            sys.stdout.write('There are not test cases in the repo: %s \n' %
                                            self.engineConfig['testcase-repo'])

    def showAvailableOsHdImages(self):

        oshdImage = None
        sys.stdout.write('Available operation system images isos:\n')
        for osHdImage in OsHdImageRepoManager.listItens(
                                        self.engineConfig['oshdimage-repo']):
            sys.stdout.write('%s \n' % osHdImage)
        if osHdImage is None:
            sys.stdout.write('There are not hd images in the repo: %s \n' %
                                            self.engineConfig['oshdimage-repo'])

    def showAvailableTestResults(self, filterByIso=None, filterByTestCase=None,
                                                        filterByOsHdImage=None):

        testCase = None
        sys.stdout.write('Available test case results:\n')
        for resultId, resultInfo in (
         TestResultRepoManager.listItens(self.engineConfig['testresult-repo'],
                            filterByIso, filterByTestCase,filterByOsHdImage) ):
            testCase,iso,osHdImage,sdate,fdate,total,result = resulInfo
            sys.stdout.write("""Test case: %s\nIso: %s\nOs Image: %s\n\
Start date: %s\nFinish date: %s\nTotal time: %s secs\nResult: %s\n\n""" % (
             testCase, iso, osHdImage, sdate, fdate, total, result))
        if testCase is None:
            sys.stdout.write('There are not test results in the repo: %s\n'
             % self.engineConfig['testresult-repo'])

    def _virtPlayerFactory(self):

       # m = __import__( self.engineConfig['virt-module'] )
       m = virt
       sessionInfo = {'sessionId':self.sessionId,'sessionPath':self.sessionPath}
       # return getattr( m, self.engineConfig['virt-handler'] )
       # (self.virtPlayerConfig, self.engineConfig, sessionInfo)
       return getattr( m, self.virtPlayerConfig['virt-handler'] )(
                           self.virtPlayerConfig,self.engineConfig, sessionInfo)

    def _loadConfig (self):

        config = SafeConfigParser()
        # TODO: exception for lack of .cfg
        config.read(os.path.join(INSTALL_DIR,'osimage-autotest.cfg'))
        confitens = config.items('global')
        for param,value in confitens:
            self.engineConfig[param] = value
        confitens = config.items(self.engineConfig['virt'])
        for param,value in confitens:
            self.virtPlayerConfig[param] = value

    def _compareScreen(self, srcScreen, destScreen):
        """ srcScreen == destScreen is not equal to srcScreen == destScreen,
            because of the similarity threshold """
        if srcScreen.similarity is not None:
            sim = srcScreen.similarity
        else:
            sim = float(self.engineConfig['img-similarity-threshold'])
        # It is not required to compute hash, as seem in the imageproc
        # module hashing and similarity of two images has similar performance
        # if srcScreen.getHash() == destScreen.getHash():
        #     return (1.0, True)
        return imageproc.rawCompare(srcScreen.path, destScreen.path, sim)


    def _waitScreen (self, expectedscreen, lastsimlevel=None):

        if expectedscreen.path is None:
            expectedscreen.path = os.path.join(self.engineConfig['screen-repo'],
                                        str(expectedscreen.screenId)  + '.ppm')
        timeout = expectedscreen.timeout
        last_t = time()
        while timeout > 0:
            #blocks until a screen or None is available
            currentscreen = self.screenQueue.get(block=True)
            if currentscreen is None:
                break
            simlevel,ret = self._compareScreen(expectedscreen, currentscreen)
            if ret:
                logging.info('Detected screen: %s for %s',
                              currentscreen.hashValue, expectedscreen.hashValue)
                return (True, currentscreen)
            current_t = time()
            timeout -= (current_t - last_t)
            last_t = current_t
        return (False, currentscreen)

    def _getCurrentScreen(self, dir, doCount=False):

        filename = None
        if doCount:
            # for ogv generation
            filename = 'screen-{0:04}'.format(self._screencont)+'.ppm'
            self._screencont += 1
        screen = Screen()
        screen.setPath(dir, 'lastscreen.ppm', filename)
        return screen

    def _hasOption(self, opt):

        return (self.commandOptions.__dict__.has_key(opt)
                                        and self.commandOptions.__dict__[opt])

    def _noneToNullStr(self,str):

        if str is None:
            return ''
        return str


# class testing_session(object):
# 
#     def __init__(self, f):
#         self.testingfunc = f
# 
#     def __call__(self):
#         self._createTestSession(iso, oshdimg)
#         self.testingfunc()
#         self._finalizeTestSession()

