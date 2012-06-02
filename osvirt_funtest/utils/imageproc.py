import hashlib
import cv
import sys
import os
import subprocess

def calculateSimilarity(srcImage, destImage, grayScale=True):
    """ Returns the similarity level of images: 
        1.0 means equal images
        0.0 menas absolutely different images

        loading, computing and comparing two images of 2.4 Mb
        by similarity will get 0.02 seconds
    """
    try:
        if grayScale:
            colormode = cv.CV_LOAD_IMAGE_GRAYSCALE
        else:
            colormode = cv.CV_LOAD_IMAGE_COLOR
        img1 = cv.LoadImageM(srcImage, colormode)
        img2 = cv.LoadImageM(destImage, colormode)
        #different sizes are considered as different images 
        if img1.rows != img2.rows or img1.cols != img2.cols:
            return 0.0
        if grayScale:
            # use some threshold ?
            # cv.Threshold(img, img, 245, 255, cv.CV_THRESH_BINARY)
            l = cv.CreateMat(img1.rows, img1.cols, cv.CV_8UC1)
            cv.Xor(img1, img2, l)
            diffs = cv.CountNonZero(l)
        else:
            # A possibile way is reading pixel by pixel src and dest image 
            # and account equal pixels and divide it by the total of pixels 
            diffs = 0
            for row in range(img1.rows):
                for col in range(img1.cols):
                    # (r, g, b) = img1[row, col]
                    rgb1 = img1[row, col]
                    rgb2 = img2[row, col]
                    if rgb1 != rgb2:
                        diffs = diffs + 1
        imgsize = img1.rows * img1.cols
        return (imgsize - diffs) / float(imgsize)
    except IOError:
        print srcImage, destImage
        raise InvalidImageError

def rawCompare(scrImg=None, destImg=None, similarityThreshold=0.95):

    sim = calculateSimilarity(scrImg, destImg)
    return (sim, sim >= similarityThreshold)

def calculateHash(srcImage, size=-1):
    """ loading, computing and comparing two images of 2.4 Mb
        by hash will get 0.02 seconds """
    try:
        with open(srcImage) as fimg:
            _hash = str( hashlib.md5( fimg.read(size) ).hexdigest() )
        return _hash
    except IOError:
        raise InvalidImageError

def generateOgv(srcDir, out):

    # ffmpeg -r 10 -i 'screen-%04d.ppm' out.ogv
    try:
        screenspath = os.path.join(srcDir,"'screen-%04d.ppm'")
        cmdline = '{cmd} {params} {inpt} {out}'.format(cmd='ffmpeg',
                            params='-r 3 -i', inpt=screenspath, out=out)
        pobj = subprocess.Popen(cmdline, shell=True)
        pobj.wait()
        if pobj.returncode != 0:
            raise Exception
    except:
        raise

class InvalidImageError(Exception):
    pass

