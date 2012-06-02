from optparse import OptionParser, OptionGroup
import sys

AVAILABLE = ['info', 'record', 'test']

class ICommand :

    def __init__(self) :
        self.options = None # 

    def parseOptions (self):
        raise NotImplementedError

    def run (self, testEngine):
        raise NotImplementedError

class Command:

    def __init__(self, cmdType, cmdOptions):

        usage = "Usage: %prog {cmdType} [options] arg1 arg2".format(
                                                        cmdType=cmdType.lower())
        self.parser = OptionParser(usage=usage)
        self.optionsRaw = cmdOptions
        self.optionsParsed = None
        self.commandType = cmdType

    def parseOptions(self):
        raise NotImplementedError

    def run (self, testEngine):
        raise NotImplementedError

    def _checkOptions(self, absolutelyRequires=None, partiallyRequires=None,
                            dependencyAbsRequires=None):

        if absolutelyRequires is not None:
            for opt in absolutelyRequires:
                value = self.optionsParsed.__dict__[opt.replace('-','_')]
                if (isinstance(value, bool) and not value) or value is None:
                    raise RequiredOption(
                           'Required options %s' % ' '.join(absolutelyRequires))

        if partiallyRequires is not None:
            for opt in partiallyRequires:
                value = self.optionsParsed.__dict__[opt.replace('-','_')]
                if (isinstance(value, bool) and value) or value is not None:
                    return
            raise RequiredOption('One of the options is required: %s' %' '.join(
                                                             partiallyRequires))
        if dependencyAbsRequires is not None:
            for opt,deps in absolutelyRequires:
                value = self.optionsParsed.__dict__[opt.replace('-','_')]
                if (isinstance(value, bool) and value) or value is not None:
                    for op in deps:
                        value = self.optionsParsed.__dict__[op.replace('-','_')]
                        if (isinstance(value, bool) and not value) or (
                         value is None):
                            raise RequiredOption(
                             'Using %s requires options %s'%(opt,' '.join(deps)))

class CommandInfo(Command, ICommand):

    def __init__(self, cmdType, cmdOptions):
        Command.__init__(self, cmdType, cmdOptions)

    def parseOptions(self):

        self.parser.add_option('-i','--show-isos', action='store_true',
                                 default=False, help="""Show available isos.""")
        self.parser.add_option('-t','--show-test-cases', action='store_true',
                           default=False, help="""Show available test cases.""")
        self.parser.add_option('-s','--show-oshd-images', action='store_true',
              default=False, help="""Show available operating system images.""")
        group = OptionGroup(self.parser, 'Test cases execution information' )
        group.add_option('-r','--show-results', action='store_true',
         default=False, help="""Show information about previous test case\
          execution.""")
        group.add_option('-I', '--filterby-iso', action='store',
                               dest='isoFilter', help="""Filter by iso file.""")
        group.add_option('-T', '--filterby-test-case', action='store',
                            dest='tcaseFilter', help="""Filter by test case.""")
        group.add_option('-S', '--filterby-oshd-image', action='store',
             dest='oshdimgFilter', help="""Filter by operating system image.""")
        try:
            self.parser.add_option_group(group)
            (self.optionsParsed, self.args) = (
                                        self.parser.parse_args(self.optionsRaw))
            self._checkOptions(partiallyRequires=['show-isos', 'show-test-cases'
                                          , 'show-oshd-images','show-results'])
        except RequiredOption as e:
            sys.stdout.write('Error on command %s:\n%s\n' % (self.commandType,
                                                             e.args[0]))
            sys.exit(1)

    def run (self, testEngine):

        if self.optionsParsed.show_isos:
            testEngine.showAvailableIsos()
        if self.optionsParsed.show_test_cases:
            testEngine.showAvailableTestCases()
        if self.optionsParsed.show_oshd_images:
            testEngine.showAvailableOsHdImages()

        if self.optionsParsed.show_results:
#            testEngine.showAvailableTestResults(self.optionsParsed.isoFilter,
#               self.optionsParsed.tcaseFilter, self.optionsParsed.oshdimgFilter)
            testEngine.showAvailableTestResults()

class CommandRecord(Command, ICommand):

    def __init__(self, cmdType, cmdOptions):
        Command.__init__(self, cmdType, cmdOptions)

    def parseOptions (self) :
        self.parser.add_option('-t','--test-case', action='store', type='string'
        , help="""Test case name which is the yml file name that test case info\
         will be recorded.""")
        self.parser.add_option('-i','--iso', action='store', type='string',
                   help="""Start a test case record session for a given iso.""")
        self.parser.add_option('-s','--oshd-image', action='store',type='string'
         ,help="""Operation system hd image which will be used by the record\
          session, see info --oshd-images.""")
        self.parser.add_option('-r','--store-oshd-image', action='store_true',
         default=False, help="""Move oshd-image to the operating system image\
          repository in the end of the record session.""")
        self.parser.add_option('-d','--desc-oshdimage', action='store',
         type='string', help="""Short description of the operating system \
          image placed in the image file name.""")
        try:
            (self.optionsParsed, self.args) = self.parser.parse_args(
                                                                self.optionsRaw)
            self._checkOptions(absolutelyRequires=['test-case'],
                               partiallyRequires=['iso','oshd-image'],
                               dependencyAbsRequires=[('store-oshdimage',
                                                      ['desc-oshdimage'])])


        except RequiredOption as e:
            sys.stdout.write('Error on command %s:\n%s\n' % (self.commandType,
                                                             e.args[0]))
            sys.exit(1)


    def run(self, testEngine):

#        testEngine.recordTest(self.optionsParsed.test_case,
#                          self.optionsParsed.iso, self.optionsParsed.oshd_image)
        testEngine.recordTest()


class CommandTest(Command, ICommand):

    def __init__(self, cmdType, cmdOptions):
        Command.__init__(self, cmdType, cmdOptions)

    def parseOptions (self):

        self.parser.add_option('-t','--test-case', action='store', type='string'
           , help="""Execute the specified test case, see info --test-cases.""")
        self.parser.add_option('-i','--iso', action='store', type='string',
          help="Iso which will be used by the test case, see info --show-isos.")
        self.parser.add_option('-s','--oshd-image', action='store',
          type='string', help="""Operation system hd image which will be used\
           by the test case, see info --oshd-images.""")
        self.parser.add_option('-r','--store-oshd-image', action='store_true',
          default=False, help="""Move oshd-image with testing changes to the\
           operating system image repository in the end of the test session.""")
        self.parser.add_option('-d','--desc-oshdimage', action='store',
         type='string', help="""Short description of the operating system \
          image placed in the image file name.""")
        try:
            (self.optionsParsed, self.args) = self.parser.parse_args(
                                                                self.optionsRaw)
            self._checkOptions(absolutelyRequires=['test-case'],
                               partiallyRequires=['iso','oshd-image'],
                               dependencyAbsRequires=[('store-oshdimage',
                                                      ['desc-oshdimage'])])

        except RequiredOption as e:
            sys.stdout.write('Error on command %s:\n%s\n' % (self.commandType,
                                                                     e.args[0]))
            sys.exit(1)

    def run (self, testEngine):

#        testEngine.executeTest(self.optionsParsed.test_case,
#                          self.optionsParsed.iso, self.optionsParsed.oshd_image)
        testEngine.executeTest()

class RequiredOption(Exception):
    pass

class UnknownCommand(Exception):
    pass
