import yaml
from userinput import *
import socket
import subprocess
import glob
import os
import time
import sys
import logging
from time import sleep

# first try qmp from system, otherwise the bundled one
try:
    import qmp
except:
    import bundles.qmp as qmp

__all__ = ['VirtPlayerQemu', 'VirtPlayerError']

class IVirtPlayer(object):
    '''(NULL)'''
    def __init__(self) :
        self.playerConfig = None # dict
        pass
    def play (self) :
        # returns 
        pass
    def stop (self) :
        # returns 
        pass
    def quit (self) :
        # returns 
        pass
    def isAlive (self) :
        # returns 
        pass
    def takeScreenshot (self, outputdir) :
        # returns 
        pass
    def sendUserInput (self, input) :
        # returns 
        pass
    def isIdle (self) :
        # returns 
        pass


class VirtPlayerQemu(IVirtPlayer):

    def __init__(self, playerConf=None, engineConf=None, sessionInfo=None):

        self.playerConfig = playerConf
        self.engineConfig = engineConf
        self.sessionInfo = sessionInfo
        self.qemuobj = None
        self.qemuproc = None

    def play(self, iso, oshdimg):
        #TODO:
        # check if vm is enabled
        try:
            self._startVirt(iso, oshdimg)
            time.sleep( 4 )
            greetings = self.qemuobj.connect()
            #workarround: using subprocess requires qemu being frozen during 
            #start -S so a following continue command is required, otherwise no 
            #furhter qmp commads are possible
            self.qemuobj.cmd('cont',{})
        except qmp.QMPConnectError:
            # raised also when kvm_module is not loaded
            raise VirtPlayerError(self.sessionInfo,
                                             'Didn\'t get QMP greeting message')

        except qmp.QMPCapabilitiesError:
            raise VirtPlayerError(self.sessionInfo,
                                             'Could not negotiate capabilities')
        except socket.error:
            raise VirtPlayerError(self.sessionInfo, 'Socket error on play')
#        except Exception as e:
#            raise VirtPlayerError(self.sessionInfo, 'Unknown error on play', e )

    def stop (self) :
        try:
            cmd = 'stop'
            params = {}
            ret = self.qemuobj.cmd( cmd, params )
#         except socket.error, err:
#             raise VirtPlayerError(self.sessionInfo, 'Socket error on stop')
        except Exception as e:
            raise VirtPlayerError(self.sessionInfo, 'Unknown error on stop', e)

        except:
            pass

    def quit(self):

        # machine is poweroff
        if not self.isAlive():
            return
        try:
            cmd = 'quit'
            params = {}
            ret = self.qemuobj.cmd( cmd, params )
#         except socket.error:
#             raise VirtPlayerError(self.sessionInfo, 'Socket error on quit')
        except Exception as e:
            raise VirtPlayerError(self.sessionInfo, 'Unknown error on quit', e)

    def isAlive(self):
        # See POPEN doc
        # if self.qemuproc.poll() is None:
        #    return True
        # poll and returncode both seems to be working
        if self.qemuproc.returncode is None:
            return True
        return False

    def takeScreenshot(self, outputdir=None, fileName="lastscreen.ppm"):

        try:
            if outputdir is None:
                outputdir = os.path.abspath(os.curdir)
            cmd = 'screendump'
            pathimg = os.path.join(outputdir, fileName)
            params = {'filename':  pathimg}
            ret = self.qemuobj.cmd( cmd, params )
            if ret is None:
                raise QEMUDisconnected
        except socket.error:
            sys.stdout.write('Socket error on takeScreenshot')
            # probably the vm is in finishing process then 
            # wait a bit to test its survival
            time.sleep( 30 )
            print self.qemuproc.poll()
            print self.qemuproc.returncode
            if not self.isAlive():
                raise VirtPlayerShutdown
            raise
            # raise VirtPlayerError(self.sessionInfo, 'Socket error on takeScreenshot')
        except QEMUDisconnected:
                self.qemuobj.close()
                raise
        except:
            sys.stdout.write('Unknown error on takeScreenshot')
            raise
 #       except Exception as e:
 #           raise VirtPlayerError(self.sessionInfo, 'Unknown error on takeScreenshot', e)

    def _startVirt(self, iso=None, oshdimg=None):

        try:
            isoOptions = hdOptions = ''
            if iso is not None:
                isoOptions = self.playerConfig['iso-parameters'].format(
                                                                    isofile=iso)
            if oshdimg is not None:
                hdOptions = self.playerConfig['hd-parameters'].format(
                                                                 hdfile=oshdimg)
            #For each testsession instance a different qmp/vnc port must be used
            qmpport = self._getQMPPort()
            vncport = self._getVNCPort()
            parameters = self.playerConfig['parameters'].format(qmpport=qmpport,
                                                                vncport=vncport)
            cmdline = '%s %s %s %s' % (self.playerConfig['executable'],
                                       parameters, isoOptions, hdOptions)
            self._openVirtPlayerLog()
            self.qemuproc = subprocess.Popen(args=cmdline, shell=True,
                                           stdout=self.vplog, stderr=self.vplog)
            self.qemuobj = qmp.QEMUMonitorProtocol( (
                                 self.playerConfig['qmpserver'], int(qmpport)) )
            # TODO warn user about the vnc port if it is changed
            # Save playerinfo.yaml
            playerInfo = { 'qmpport': qmpport,
                           'vncport': vncport }
            with open(os.path.join(self.sessionInfo['sessionPath'],
                                   'playerinfo.yml'),'w') as fplay:
                fplay.write(yaml.dump(playerInfo))
        except OSError:
            raise VirtPlayerError(self.sessionInfo,
                                  'Qemu could not be started: %s' % cmdline)
       #  except Exception as e:
       #     raise VirtPlayerError(self.sessionInfo, 'Unknown error on startVirt', e)

    def sendUserInput(self, inputs):

        ix = 0
        for input_ in inputs:
            # vm is busy/idle so no input user shoud be sent 
            idletimeout = self.playerConfig['idle-timeout']
            while not self._detectIdle() and idletimeout > 0:
                time.sleep(1)
                idletimeout = idletimeout - 1
            if idletimeout == 0:
                raise IdleRequired
            if isinstance(input_, Keyboard):
                self._sendKey(input_)
                logging.info('key sent: %s', input_.key )
            elif isinstance(input_, Mouse):
                self._sendMouse(input_)
            elif isinstance(input_, Keystream):
                for inp in input_.keystream:
                    self._sendKey(inp)
                    logging.info('key sent: %s', inp.key )
            else:
                raise VirtPlayerError(self.sessionInfo,
                                  'Unknown input type on sendUserInput', input_)
            # User input is sent accoring to its occurence relative to
            # screen and also relative to each other timestamp
            try:
                evdelay = inputs[ix+1].timestamp - input_.timestamp
                # Bug in the QMP timestamp:
                # events are executed later get sooner timestamp
                if evdelay < 0.0:
                    evdelay=0.5
                    logging.info('Events with wrong timestamps: %.6f %.6f',
                                       inputs[ix+1].timestamp, input_.timestamp)
                sleep(evdelay)
            except IndexError:
                pass
            ix+=1


    def getUserInputEvents(self):

        events = self.qemuobj.get_events()
        if not events:
            return []

        inputEvents = []
        try:
            lastevtime = 0
            keystream = []
            shortcut = []
            print events
            for ix,ev in enumerate(events):
                if ev['event'] == 'VNC_KEYEVENT':
                    # Key pressed
                    if ev['data']['down']:
                        if events[ix+1]['data']['down'] or shortcut:
                            shortcut.append(ev['data']['key'])
                            print type(ev['timestamp']['seconds'])
                            sctimestamp = float(str(ev['timestamp']['seconds'])+'.'+str(ev['timestamp']['microseconds']))
                        else:
                            keytimestamp = float(str(ev['timestamp']['seconds'])+'.'+str(ev['timestamp']['microseconds']))
                            keyinput = Keyboard(ev['data']['key'], keytimestamp)
                            inputEvents.append( keyinput )

                    # Key released
                    else:
                        # Key combinations eg. CTRL+key
                        if shortcut:
                            scinput = Keyboard('-'.join(shortcut), sctimestamp)
                            inputEvents.append( scinput )
                            shortcut = []

# Keystream handling
#                if ev.has_key('event') and ev['event'] == 'VNC_KEYEVENT' and ev['data']['down']:
#
#                    # Key events with delay time lesser then 2 seconts are of 
#                    # keystream type
#                    if lastevtime == 0 or ((int(ev['timestamp']['seconds']) - lastevtime) <= 2):
#                        keystream.append(ev['data']['key'])
#                    else:
#                        if len(keystream) > 1:
#                            inputEvents.append( Keystream(keystream) )
#                        else:
#                            inputEvents.append( Keyboard(keystream[0]) )
#                        keystream = [ev['data']['key']]
#                    lastevtime = int(ev['timestamp']['seconds'])
#
#
#            print keystream
#            if keystream:
#                if len(keystream) > 1:
#                    inputEvents.append( Keystream(keystream) )
#                else:
#                    inputEvents.append( Keyboard(keystream[0]) )

        except Exception as e:
            print e


        self.qemuobj.clear_events()
        return inputEvents

    def _sendKey(self, key):

       try:
           cmd = 'sendkey'
           params = {'string':  key.key, 'hold_time': int(key.holdTime)}
           ret = self.qemuobj.cmd( cmd, params )
#         except socket.error:
#             raise VirtPlayerError(self.sessionInfo, 'Socket error on sendkey: %s' % key.key)
       except Exception as e:
           raise VirtPlayerError(self.sessionInfo,
                                 'Unknown error on sendkey: %s ' % key.key, e)

    def _sendMouse(self, Mouse):
        # returns 
        pass

    def _getPort(self, _type):

        port = self.playerConfig['default-' + _type ]
        sessionDirs = glob.glob(os.path.join(self.engineConfig['var-dir'],
                                             '*-session'))
        sessionDirs = filter(lambda str: not
         (os.path.basename(str).replace('-session','')
                                              == self.sessionInfo['sessionId'])
                            ,sessionDirs)
        if len(sessionDirs) > 0:
            usedPorts = []
            for session in sessionDirs:
                with open(os.path.join(session,'playerinfo.yml')) as fplayinfo:
                    yamlobj = yaml.load(fplayinfo)
                    usedPorts.append(int(yamlobj[_type]))
            if usedPorts:
                port = max(usedPorts) + 1
        return port


    def _getQMPPort(self):

        return self._getPort('qmpport')

    def _getVNCPort(self):

        return self._getPort('vncport')

    def createHdImage(self, hdfile):

        exec_ = self.playerConfig['qemu-img-executable']
        params = self.playerConfig['qemu-img-parameters'].format(hdfile=hdfile)
        cmdline = "%s %s" % (exec_, params)
        try:
            self._openVirtPlayerLog()
            pobj = subprocess.Popen(args=cmdline,shell=True,stdout=self.vplog,
                                                            stderr=self.vplog)
            pobj.wait()
            if pobj.returncode != 0:
                raise Exception
        except OSError:
            raise VirtPlayerError(self.sessionInfo,
             'Disk image creating command could not be executed: %s' % cmdline)
        except Exception as e:
            raise VirtPlayerError(self.sessionInfo,
                                  'Unknown error on createHdImage', e)

    def createHdImageDisposable(self, srchdfile, desthdfile):

        exec_ = self.playerConfig['qemu-img-executable']
        params = self.playerConfig['qemu-img-parameters-disposable'].format(
                                    srchdfile=srchdfile, desthdfile=desthdfile)
        cmdline = "%s %s" % (exec_, params)
        try:
            self._openVirtPlayerLog()
            pobj = subprocess.Popen(args=cmdline,shell=True,stdout=self.vplog,
                                                            stderr=self.vplog)
            pobj.wait()
            if pobj.returncode != 0:
                raise Exception
        except OSError:
            raise VirtPlayerError(self.sessionInfo,
             'Disk image disposable creating command could not be executed: %s'
                                                                      % cmdline)
        except Exception as e:
            raise e
            # raise VirtPlayerError(self.sessionInfo,
            #                    'Unknown error on createHdImageDisposable\n', e)

    def _detectIdle(self):
        return True

    def _openVirtPlayerLog(self):

        if not self.__dict__.has_key('vplog'):
            self.vplog = open(os.path.join(self.sessionInfo['sessionPath'],
                                                        'virtplayer.log'),'w')
    def __del__(self):

        # Not sure if it is explicitly required
        if self.__dict__.has_key('vplog') and self.vplog: self.vplog.close()

class VirtPlayerError(Exception):
    pass

class VirtPlayerShutdown(VirtPlayerError):
    pass

class QEMUDisconnected(VirtPlayerError):
    pass
