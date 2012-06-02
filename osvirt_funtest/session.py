class Sesssion(object):

    def __init__():

        self.session_id = id
        self.session_path = path

    def _createTestSession(self, iso=None, oshdimg=None):


        self.sessionId = uuid.uuid4().get_hex()
        self.sessionPath = os.path.abspath( os.path.join( self.engineConfig['var-dir'],
                                            self.sessionId + '-session'))
        self.virtPlayer = self._virtPlayerFactory()
        try:
            os.mkdir( self.sessionPath )
            self.sessionScreenPath = os.path.join(self.sessionPath,'screen-tmp')
            os.mkdir( self.sessionScreenPath )
            base_dir = os.path.abspath(os.curdir)
            os.chdir( self.sessionPath )
            isoPath = None
            if iso is not None:
                if not os.path.isabs(self.engineConfig['iso-repo']):
                    isoPath = base_dir
                isoPath = os.path.join(isoPath, self.engineConfig['iso-repo'], iso)
                if not os.path.exists(isoPath):
                    raise IsoNotFound
                os.symlink( isoPath, iso)
                isoPath = os.path.join( self.sessionPath, iso )
            oshdimgPath = None
            if oshdimg is not None:
                if not os.path.isabs(self.engineConfig['oshdimage-repo']):
                    oshdimgPath = base_dir
                oshdimgPath = os.path.join(oshdimgPath, self.engineConfig['oshdimage-repo'], oshdimg)
                if not os.path.exists(oshdimgPath):
                    raise OsHdImageNotFound
                os.symlink( oshdimgPath, oshdimg )
                oshdimgPath = os.path.join( self.sessionPath, oshdimg )
            else:
                oshdimgPath = os.path.join(self.sessionPath, self._generateHdName(iso))
                self.virtPlayer.createHdImage( oshdimgPath )
            os.chdir( base_dir )
            print base_dir
            self.virtPlayer.play(isoPath, oshdimgPath)
            self.osHdImage = oshdimgPath
        except OSError:
            pass
        except virt.VirtPlayerError as e:
            sys.stdout.write('Session info: %s\n%s' %(e[0]['sessionId'], e[1]))
            sys.exit(1)




