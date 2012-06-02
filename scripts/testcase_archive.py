#!/usr/bin/python

import tarfile
import yaml
import sys
import os
import shutil

TESTCASEREPO='/home/cabral/osvirt-funtest/repos/testcase/'
SCREENREPO='/home/cabral/osvirt-funtest/repos/screen/'


#TODO parse osimage_autotest cfg and get from repo
def getfromrepo(testcase):
    # testcase list
    #./osimage_autotest info -t
    return open(os.path.join(TESTCASEREPO,testcase+'.yml'))

def getinfo(tarinfo):
    print tarinfo.__dict__
    return tarinfo

def usage():
    print './testcase_archive <testcase>'
    sys.exit(1)

if __name__ == "__main__":

    if len(sys.argv) != 2:
        usage()
    testcase = sys.argv[1]

    tcasefile = testcase+'.yml'
    testcase_fname = os.path.join(TESTCASEREPO,tcasefile)
    os.mkdir(testcase)
    shutil.copy(testcase_fname, testcase)

    tcase_fp = open(testcase_fname)
    tcaseyml = yaml.load(tcase_fp)
    testcase_archive = testcase + '.tar.bz2'
    resulttar = tarfile.open(testcase_archive,'w:bz2')

    # add test case
    resulttar.add(os.path.join(testcase,tcasefile))

    # add test case screens
    for screen in tcaseyml['screens']:
        file = screen['hash'] + '.ppm'
        screenpath = os.path.join(SCREENREPO, file)
        shutil.copy(screenpath, testcase)
#       python 2.7
#       resulttar.add(screenpath, recursive=False, filter=getinfo)
        resulttar.add(os.path.join(testcase,file))

    resulttar.close()
    tcase_fp.close()
    shutil.rmtree(testcase)




