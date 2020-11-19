"""
 OMRChecker
 Designed and Developed by-
 Udayraj Deshmukh
 https://github.com/Udayraj123
"""

# Use all imports relative to root directory (https://chrisyeh96.github.io/2017/08/08/definitive-guide-python-imports.html#case-2-syspath-could-change)
import src.constants as constants
# TODO: pass config in runtime later
from src.config import configDefaults as config

from imutils import grab_contours
from random import randint
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import glob
import cv2
import sys
import os
import re
import numpy as np
import json
from operator import itemgetter
from dataclasses import dataclass

class ImageUtils:
    """Class to hold indicators of images and save images."""

    def __init__(self):
        """Constructor for class ImageUtils"""
        self.save_img_list = {}
        self.save_image_level = config.outputs.save_image_level

    def reset_save_img(self, key):
        self.save_img_list[key] = []

    @staticmethod
    def append_save_img(key, img):
        if self.save_image_level >= int(key):
            if key not in self.save_img_list:
                self.save_img_list[key] = []
            self.save_img_list[key].append(img.copy())

    @staticmethod
    def saveImg(path, final_marked):
        print("Saving Image to " + path)
        cv2.imwrite(path, final_marked)

    @staticmethod
    def saveOrShowStacks(self, key, name, savedir=None, pause=1):
        if self.save_image_level >= int(key) and self.save_img_list[key] != []:
            result = np.hstack(
                tuple(
                    [
                        self.resize_util_h(img, config.dimensions.display_height)
                        for img in self.save_img_list[key]
                    ]
                )
            )
            result = self.resize_util(
                result,
                min(
                    len(self.save_img_list[key]) * config.dimensions.display_width // 3,
                    int(config.dimensions.display_width * 2.5),
                ),
            )
            if type(savedir) != type(None):
                self.saveImg(
                    savedir + "stack/" + name + "_" + str(key) + "_stack.jpg", result
                )
            else:
                show(name + "_" + str(key), result, pause, 0)

    @staticmethod
    def resize_util(img, u_width, u_height=None):
        if u_height is None:
            h, w = img.shape[:2]
            u_height = int(h * u_width / w)
        return cv2.resize(img, (int(u_width), int(u_height)))

    @staticmethod
    def resize_util_h(img, u_height, u_width=None):
        if u_width is None:
            h, w = img.shape[:2]
            u_width = int(w * u_height / h)
        return cv2.resize(img, (int(u_width), int(u_height)))


@dataclass
class ImageMetrics:
    resetpos = [0, 0]
    # for positioning image windows
    window_x, window_y = 0, 0
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
    # TODO Fill these for stats
    badThresholds = []
    veryBadPoints = []

plt.rcParams['figure.figsize'] = (10.0, 8.0)

# Image-processing utils

def normalize_util(img, alpha=0, beta=255):
    return cv2.normalize(img, alpha, beta, norm_type=cv2.NORM_MINMAX)


def normalize_hist(img):
    hist, _ = np.histogram(img.flatten(), 256, [0, 256])
    cdf = hist.cumsum()
    cdf_m = np.ma.masked_equal(cdf, 0)
    cdf_m = (cdf_m - cdf_m.min()) * 255 / (cdf_m.max() - cdf_m.min())
    cdf = np.ma.filled(cdf_m, 0).astype('uint8')
    return cdf[img]


def putLabel(img, label, size):
    scale = img.shape[1] / config.dimensions.display_width
    bgVal = int(np.mean(img))
    pos = (int(scale * 80), int(scale * 30))
    clr = (255 - bgVal,) * 3
    img[(pos[1] - size * 30):(pos[1] + size * 2), :] = bgVal
    cv2.putText(img, label, pos, cv2.FONT_HERSHEY_SIMPLEX, size, clr, 3)


def drawTemplateLayout(
        img,
        template,
        shifted=True,
        draw_qvals=False,
        border=-1):
    img = ImageUtils.resize_util(img, template.dimensions[0], template.dimensions[1])
    final_align = img.copy()
    boxW, boxH = template.bubbleDimensions
    for QBlock in template.qBlocks:
        s, d = QBlock.orig, QBlock.dimensions
        shift = QBlock.shift
        if(shifted):
            cv2.rectangle(final_align,
                          (s[0]+shift,s[1]),
                          (s[0]+shift+d[0],s[1]+d[1]),
                          constants.CLR_BLACK,
                          3)
        else:
            cv2.rectangle(final_align,
                          (s[0], s[1]),
                          (s[0] + d[0], s[1] + d[1]),
                          constants.CLR_BLACK
                          ,3)
        for _, qBoxPts in QBlock.traverse_pts:
            for pt in qBoxPts:
                x, y = (pt.x + QBlock.shift, pt.y) if shifted else (pt.x, pt.y)
                cv2.rectangle(final_align,
                              (int(x + boxW / 10),
                               int(y + boxH / 10)),
                              (int(x + boxW - boxW / 10),
                                int(y + boxH - boxH / 10)),
                              constants.CLR_GRAY,
                              border)
                if(draw_qvals):
                    rect = [y, y + boxH, x, x + boxW]
                    cv2.putText(final_align,
                                '%d'% (cv2.mean(img[rect[0]:rect[1], rect[2]:rect[3]])[0]),
                                (rect[2] + 2, rect[0] + (boxH * 2) // 3),
                                cv2.FONT_HERSHEY_SIMPLEX, 
                                0.6, 
                                constants.CLR_BLACK,
                                2)
        if(shifted):
            cv2.putText(final_align,
                        's%s'% (shift), 
                        tuple(s - [template.dimensions[0] // 20, -d[1] // 2]),
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        constants.TEXT_SIZE, 
                        constants.CLR_BLACK, 
                        4)
    return final_align


def getPlotImg():
    # Implement better logic here
    plt.savefig('tmp.png')
    # img = cv2.imread('tmp.png',cv2.IMREAD_COLOR)
    img = cv2.imread('tmp.png', cv2.IMREAD_GRAYSCALE)
    os.remove("tmp.png")
    # plt.cla()
    # plt.clf()
    plt.close()
    return img


def dist(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


def get_reflection(pt, pt1, pt2):
    pt, pt1, pt2 = tuple(
        map(lambda x: np.array(x, dtype=float), [pt, pt1, pt2]))
    return (pt1 + pt2) - pt

# These are used inside multiple extensions
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")

    # the top-left point will have the smallest sum, whereas
    # the bottom-right point will have the largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    # return the ordered coordinates
    return rect


def four_point_transform(image, pts):
    # obtain a consistent order of the points and unpack them
    # individually
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # compute the width of the new image, which will be the
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))

    maxWidth = max(int(widthA), int(widthB))
    # maxWidth = max(int(np.linalg.norm(br-bl)), int(np.linalg.norm(tr-tl)))

    # compute the height of the new image, which will be the
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    # maxHeight = max(int(np.linalg.norm(tr-br)), int(np.linalg.norm(tl-br)))

    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    # compute the perspective transform matrix and then apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    # return the warped image
    return warped

def get_fourth_pt(three_pts):
    m = []
    for i in range(3):
        m.append(dist(three_pts[i], three_pts[(i + 1) % 3]))

    v = max(m)
    for i in range(3):
        if(m[i] != v and m[(i + 1) % 3] != v):
            refl = (i + 1) % 3
            break
    fourth_pt = get_reflection(
        three_pts[refl], three_pts[(refl + 1) % 3], three_pts[(refl + 2) % 3])
    return fourth_pt

def auto_canny(image, sigma=0.93):
    # compute the median of the single channel pixel intensities
    v = np.median(image)

    # apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edged = cv2.Canny(image, lower, upper)

    # return the edged image
    return edged

def adjust_gamma(image, gamma=1.0):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")

    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)


def getGlobalThreshold(
        QVals_orig,
        plotTitle=None,
        plotShow=True,
        sortInPlot=True,
        looseness=1):
    """
        Note: Cannot assume qStrip has only-gray or only-white bg (in which case there is only one jump).
              So there will be either 1 or 2 jumps.
        1 Jump :
                ......
                ||||||
                ||||||  <-- risky THR
                ||||||  <-- safe THR
            ....||||||
            ||||||||||

        2 Jumps :
                  ......
                  |||||| <-- wrong THR
              ....||||||
              |||||||||| <-- safe THR
            ..||||||||||
            ||||||||||||

        The abstract "First LARGE GAP" is perfect for this.
        Current code is considering ONLY TOP 2 jumps(>= MIN_GAP) to be big, gives the smaller one

    """
    # Sort the Q vals
    # Change var name of QVals
    QVals = sorted(QVals_orig)
    # Find the FIRST LARGE GAP and set it as threshold:
    ls = (looseness + 1) // 2
    l = len(QVals) - ls
    max1, thr1 = config.threshold_params.MIN_JUMP, 255
    for i in range(ls, l):
        jump = QVals[i + ls] - QVals[i - ls]
        if(jump > max1):
            max1 = jump
            thr1 = QVals[i - ls] + jump / 2

    # NOTE: thr2 is deprecated, thus is JUMP_DELTA
    # Make use of the fact that the JUMP_DELTA(Vertical gap ofc) between
    # values at detected jumps would be atleast 20
    max2, thr2 = config.threshold_params.MIN_JUMP, 255
    # Requires atleast 1 gray box to be present (Roll field will ensure this)
    for i in range(ls,l):
        jump = QVals[i+ls] - QVals[i-ls]
        newThr = QVals[i-ls] + jump/2
        if(jump > max2 and abs(thr1-newThr) > config.threshold_params.JUMP_DELTA):
            max2=jump
            thr2=newThr
    # globalTHR = min(thr1,thr2)
    globalTHR, j_low, j_high = thr1, thr1 - max1 // 2, thr1 + max1 // 2

    # # For normal images
    # thresholdRead =  116
    # if(thr1 > thr2 and thr2 > thresholdRead):
    #     print("Note: taking safer thr line.")
    #     globalTHR, j_low, j_high = thr2, thr2 - max2//2, thr2 + max2//2

    if plotTitle:
        _, ax = plt.subplots()
        ax.bar(range(len(QVals_orig)), QVals if sortInPlot else QVals_orig)
        ax.set_title(plotTitle)
        thrline = ax.axhline(globalTHR, color='green', ls='--', linewidth=5)
        thrline.set_label("Global Threshold")
        thrline = ax.axhline(thr2, color='red', ls=':', linewidth=3)
        thrline.set_label("THR2 Line")
        # thrline=ax.axhline(j_low,color='red',ls='-.', linewidth=3)
        # thrline=ax.axhline(j_high,color='red',ls='-.', linewidth=3)
        # thrline.set_label("Boundary Line")
        # ax.set_ylabel("Mean Intensity")
        ax.set_ylabel("Values")
        ax.set_xlabel("Position")
        ax.legend()
        if(plotShow):
            plt.title(plotTitle)
            plt.show()

    return globalTHR, j_low, j_high


def getLocalThreshold(
        qNo,
        QVals,
        globalTHR,
        noOutliers,
        plotTitle=None,
        plotShow=True):
    """
    TODO: Update this documentation too-
    //No more - Assumption : Colwise background color is uniformly gray or white, but not alternating. In this case there is atmost one jump.

    0 Jump :
                    <-- safe THR?
           .......
        ...|||||||
        ||||||||||  <-- safe THR?
    // How to decide given range is above or below gray?
        -> global QVals shall absolutely help here. Just run same function on total QVals instead of colwise _//
    How to decide it is this case of 0 jumps

    1 Jump :
            ......
            ||||||
            ||||||  <-- risky THR
            ||||||  <-- safe THR
        ....||||||
        ||||||||||

    """
    # Sort the Q vals
    QVals = sorted(QVals)

    # Small no of pts cases:
    # base case: 1 or 2 pts
    if(len(QVals) < 3):
        thr1 = globalTHR if np.max(
            QVals) - np.min(QVals) < config.threshold_params.MIN_GAP else np.mean(QVals)
    else:
        # qmin, qmax, qmean, qstd = round(np.min(QVals),2), round(np.max(QVals),2), round(np.mean(QVals),2), round(np.std(QVals),2)
        # GVals = [round(abs(q-qmean),2) for q in QVals]
        # gmean, gstd = round(np.mean(GVals),2), round(np.std(GVals),2)
        # # DISCRETION: Pretty critical factor in reading response
        # # Doesn't work well for small number of values.
        # DISCRETION = 2.7 # 2.59 was closest hit, 3.0 is too far
        # L2MaxGap = round(max([abs(g-gmean) for g in GVals]),2)
        # if(L2MaxGap > DISCRETION*gstd):
        #     noOutliers = False

        # # ^Stackoverflow method
        # print(qNo, noOutliers,"qstd",round(np.std(QVals),2), "gstd", gstd,"Gaps in gvals",sorted([round(abs(g-gmean),2) for g in GVals],reverse=True), '\t',round(DISCRETION*gstd,2), L2MaxGap)

        # else:
        # Find the LARGEST GAP and set it as threshold: //(FIRST LARGE GAP)
        l = len(QVals) - 1
        max1, thr1 = config.threshold_params.MIN_JUMP, 255
        for i in range(1, l):
            jump = QVals[i + 1] - QVals[i - 1]
            if(jump > max1):
                max1 = jump
                thr1 = QVals[i - 1] + jump / 2
        # print(qNo,QVals,max1)

        CONFIDENT_JUMP = config.threshold_params.MIN_JUMP + config.threshold_params.CONFIDENT_SURPLUS
        # If not confident, then only take help of globalTHR
        if(max1 < CONFIDENT_JUMP):
            if(noOutliers):
                # All Black or All White case
                thr1 = globalTHR
            else:
                # TODO: Low confidence parameters here
                pass

        # if(thr1 == 255):
        #     print("Warning: threshold is unexpectedly 255! (Outlier Delta issue?)",plotTitle)

    # Make a common plot function to show local and global thresholds
    if(plotShow and plotTitle is not None):
        _, ax = plt.subplots()
        ax.bar(range(len(QVals)), QVals)
        thrline = ax.axhline(thr1, color='green', ls=('-.'), linewidth=3)
        thrline.set_label("Local Threshold")
        thrline = ax.axhline(globalTHR, color='red', ls=':', linewidth=5)
        thrline.set_label("Global Threshold")
        ax.set_title(plotTitle)
        ax.set_ylabel("Bubble Mean Intensity")
        ax.set_xlabel("Bubble Number(sorted)")
        ax.legend()
        # TODO append QStrip to this plot-
        # appendSaveImg(6,getPlotImg())
        if(plotShow):
            plt.show()
    return thr1

# from matplotlib.ticker import MaxNLocator
# def plotArray(QVals, plotTitle, sort = False, plot=True ):
#     f, ax = plt.subplots()
#     if(sort):
#         QVals = sorted(QVals)
#     ax.bar(range(len(QVals)),QVals)
#     ax.set_title(plotTitle)
#     ax.set_ylabel("Values")
#     ax.set_xlabel("Position")
#     ax.xaxis.set_major_locator(MaxNLocator(integer=True))
#     if(plot):
#         plt.show()
#     # else: they will call this
#     #     appendSaveImg(appendImgLvl,getPlotImg())


# Non image-processing utils


def setup_dirs(paths):
    print('\nChecking Directories...')
    for _dir in [paths.SAVE_MARKED_DIR]:
        if(not os.path.exists(_dir)):
            print('Created : ' + _dir)
            os.makedirs(_dir)
            os.mkdir(_dir + '/stack')
            os.mkdir(_dir + '/_MULTI_')
            os.mkdir(_dir + '/_MULTI_' + '/stack')
            # os.mkdir(_dir+sl+'/_BADSCAN_')
            # os.mkdir(_dir+sl+'/_BADSCAN_'+'/stack')
        else:
            print('Present : ' + _dir)

    for _dir in [paths.MANUAL_DIR, paths.RESULTS_DIR]:
        if(not os.path.exists(_dir)):
            print('Created : ' + _dir)
            os.makedirs(_dir)
        else:
            print('Present : ' + _dir)

    for _dir in [paths.MULTI_MARKED_DIR, paths.ERRORS_DIR, paths.BAD_ROLLS_DIR]:
        if(not os.path.exists(_dir)):
            print('Created : ' + _dir)
            os.makedirs(_dir)
        else:
            print('Present : ' + _dir)


class MainOperations:
    """Perform primary functions such as displaying images and reading responses
    """
    def __init__(self):
        self.image_metrics = ImageMetrics()
        self.image_utils = ImageUtils()

    def waitQ(self):
        ESC_KEY = 27
        while cv2.waitKey(1) & 0xFF not in [ord("q"), ESC_KEY]:
            pass
        self.image_metrics.window_x = 0
        self.image_metrics.window_y = 0
        cv2.destroyAllWindows()

    def show(self, name, orig, pause=1, resize=False, resetpos=None):
        if type(orig) == type(None):
            print(name, " NoneType image to show!")
            if pause:
                cv2.destroyAllWindows()
            return
        # origDim = orig.shape[:2]
        img = (
            ImageUtils.resize_util(orig, config.dimensions.display_width)
            if resize
            else orig
        )
        cv2.imshow(name, img)
        if resetpos:
            self.image_metrics.window_x = resetpos[0]
            self.image_metrics.window_y = resetpos[1]
        cv2.moveWindow(name, self.image_metrics.window_x, self.image_metrics.window_y)

        h, w = img.shape[:2]

        # Set next window position
        margin = 25
        w += margin
        h += margin
        if self.image_metrics.window_x + w > config.dimensions.window_width:
            self.image_metrics.window_x = 0
            if self.image_metrics.window_y + h > config.dimensions.window_height:
                self.image_metrics.window_y = 0
            else:
                self.image_metrics.window_y += h
        else:
            self.image_metrics.window_x += w

        if pause:
            print(
                "Showing '"
                + name
                + "'\n\tPress Q on image to continue Press Ctrl + C in terminal to exit"
            )
            self.waitQ()

    def readResponse(self, template, image, name, savedir=None, autoAlign=False):
        # global clahe

        try:
            img = image.copy()
            # origDim = img.shape[:2]
            img = ImageUtils.resize_util(
                img, template.dimensions[0], template.dimensions[1]
            )
            if img.max() > img.min():
                img = normalize_util(img)
            # Processing copies
            transp_layer = img.copy()
            final_marked = img.copy()
            # putLabel(final_marked,"Crop Size: " + str(origDim[0])+"x"+str(origDim[1]) + " "+name, size=1)

            morph = img.copy()
            ImageUtils.append_save_img(3, morph)

            # TODO: evaluate if CLAHE is really req
            if autoAlign:
                # Note: clahe is good for morphology, bad for thresholding
                morph = self.image_metrics.clahe.apply(morph)
                ImageUtils.append_save_img(3, morph)
                # Remove shadows further, make columns/boxes darker (less gamma)
                morph = adjust_gamma(morph, config.threshold_params.GAMMA_LOW)
                # TODO: all numbers should come from either constants or config
                _, morph = cv2.threshold(morph, 220, 220, cv2.THRESH_TRUNC)
                morph = normalize_util(morph)
                ImageUtils.append_save_img(3, morph)
                if config.outputs.show_image_level >= 4:
                    self.show("morph1", morph, 0, 1)

            # Move them to data class if needed
            # Overlay Transparencies
            alpha = 0.65
            # alpha1 = 0.55

            boxW, boxH = template.bubbleDimensions
            # lang = ['E', 'H']
            OMRresponse = {}

            multimarked, multiroll = 0, 0

            # TODO Make this part useful for visualizing status checks
            # blackVals=[0]
            # whiteVals=[255]

            if config.outputs.show_image_level >= 5:
                allCBoxvals = {"int": [], "mcq": []}
                # ,"QTYPE_ROLL":[]}#,"QTYPE_MED":[]}
                qNums = {"int": [], "mcq": []}

            # Find Shifts for the qBlocks --> Before calculating threshold!
            if autoAlign:
                # print("Begin Alignment")
                # Open : erode then dilate
                # Vertical kernel
                v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 10))
                morph_v = cv2.morphologyEx(
                    morph, cv2.MORPH_OPEN, v_kernel, iterations=3
                )
                _, morph_v = cv2.threshold(morph_v, 200, 200, cv2.THRESH_TRUNC)
                morph_v = 255 - normalize_util(morph_v)

                if config.outputs.show_image_level >= 3:
                    self.show("morphed_vertical", morph_v, 0, 1)

                # show("morph1",morph,0,1)
                # show("morphed_vertical",morph_v,0,1)

                ImageUtils.append_save_img(3, morph_v)

                morphTHR = 60  # for Mobile images
                # morphTHR = 40 # for scan Images
                # best tuned to 5x5 now
                _, morph_v = cv2.threshold(morph_v, morphTHR, 255, cv2.THRESH_BINARY)
                morph_v = cv2.erode(morph_v, np.ones((5, 5), np.uint8), iterations=2)

                ImageUtils.append_save_img(3, morph_v)
                # h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 2))
                # morph_h = cv2.morphologyEx(morph, cv2.MORPH_OPEN, h_kernel, iterations=3)
                # ret, morph_h = cv2.threshold(morph_h,200,200,cv2.THRESH_TRUNC)
                # morph_h = 255 - normalize_util(morph_h)
                # show("morph_h",morph_h,0,1)
                # _, morph_h = cv2.threshold(morph_h,morphTHR,255,cv2.THRESH_BINARY)
                # morph_h = cv2.erode(morph_h,  np.ones((5,5),np.uint8), iterations = 2)
                if config.outputs.show_image_level >= 3:
                    self.show("morph_thr_eroded", morph_v, 0, 1)

                ImageUtils.append_save_img(6, morph_v)

                # template alignment code (relative alignment algo)
                # OUTPUT : each QBlock.shift is updated
                for QBlock in template.qBlocks:
                    s, d = QBlock.orig, QBlock.dimensions
                    # internal constants - wont need change much
                    # TODO - ALIGN_STRIDE would depend on template's dimensions
                    MATCH_COL, MAX_STEPS, ALIGN_STRIDE, THK = itemgetter(
                        [
                            "match_col",
                            "max_steps",
                            "stride",
                            "thickness",
                        ]
                    )(config.alignment_params)
                    shift, steps = 0, 0
                    while steps < MAX_STEPS:
                        L = np.mean(
                            morph_v[
                                s[1] : s[1] + d[1],
                                s[0] + shift - THK : -THK + s[0] + shift + MATCH_COL,
                            ]
                        )
                        R = np.mean(
                            morph_v[
                                s[1] : s[1] + d[1],
                                s[0]
                                + shift
                                - MATCH_COL
                                + d[0]
                                + THK : THK
                                + s[0]
                                + shift
                                + d[0],
                            ]
                        )

                        # For demonstration purposes-
                        # if(QBlock.key == "int1"):
                        #     ret = morph_v.copy()
                        #     cv2.rectangle(ret,
                        #                   (s[0]+shift-THK,s[1]),
                        #                   (s[0]+shift+THK+d[0],s[1]+d[1]),
                        #                   constants.CLR_WHITE,
                        #                   3)
                        #     appendSaveImg(6,ret)

                        # print(shift, L, R)
                        LW, RW = L > 100, R > 100
                        if LW:
                            if RW:
                                break
                            else:
                                shift -= ALIGN_STRIDE
                        else:
                            if RW:
                                shift += ALIGN_STRIDE
                            else:
                                break
                        steps += 1

                    QBlock.shift = shift
                    # print("Aligned QBlock: ",QBlock.key,"Corrected Shift:", QBlock.shift,", dimensions:", QBlock.dimensions, "orig:", QBlock.orig,'\n')
                # print("End Alignment")

            final_align = None
            if config.outputs.show_image_level >= 2:
                initial_align = drawTemplateLayout(img, template, shifted=False)
                final_align = drawTemplateLayout(
                    img, template, shifted=True, draw_qvals=True
                )
                # appendSaveImg(4,mean_vals)
                ImageUtils.append_save_img(2, initial_align)
                ImageUtils.append_save_img(2, final_align)
                ImageUtils.append_save_img(5, img)
                if autoAlign:
                    final_align = np.hstack((initial_align, final_align))

            # Get mean vals n other stats
            allQVals, allQStripArrs, allQStdVals = [], [], []
            totalQStripNo = 0
            for QBlock in template.qBlocks:
                QStdVals = []
                for _, qBoxPts in QBlock.traverse_pts:
                    QStripvals = []
                    for pt in qBoxPts:
                        # shifted
                        x, y = (pt.x + QBlock.shift, pt.y)
                        rect = [y, y + boxH, x, x + boxW]
                        QStripvals.append(
                            cv2.mean(img[rect[0] : rect[1], rect[2] : rect[3]])[0]
                            # detectCross(img, rect) ? 100 : 0
                        )
                    QStdVals.append(round(np.std(QStripvals), 2))
                    allQStripArrs.append(QStripvals)
                    # _, _, _ = getGlobalThreshold(QStripvals, "QStrip Plot", plotShow=False, sortInPlot=True)
                    # hist = getPlotImg()
                    # show("QStrip "+qBoxPts[0].qNo, hist, 0, 1)
                    allQVals.extend(QStripvals)
                    # print(totalQStripNo, qBoxPts[0].qNo, QStdVals[len(QStdVals)-1])
                    totalQStripNo += 1
                allQStdVals.extend(QStdVals)
            # print("Begin getGlobalThresholdStd")
            globalStdTHR, _, _ = getGlobalThreshold(
                allQStdVals
            )  # , "Q-wise Std-dev Plot", plotShow=True, sortInPlot=True)
            # print("End getGlobalThresholdStd")
            # print("Begin getGlobalThreshold")
            # plt.show()
            # hist = getPlotImg()
            # show("StdHist", hist, 0, 1)

            # Note: Plotting takes Significant times here --> Change Plotting args
            # to support show_image_level
            # , "Mean Intensity Histogram",plotShow=True, sortInPlot=True)
            globalTHR, _, _ = getGlobalThreshold(allQVals, looseness=4)

            # TODO colorama
            print(
                "Thresholding:\t\t globalTHR: ",
                round(globalTHR, 2),
                "\tglobalStdTHR: ",
                round(globalStdTHR, 2),
                "\t(Looks like a Xeroxed OMR)" if (globalTHR == 255) else "",
            )
            # plt.show()
            # hist = getPlotImg()
            # show("StdHist", hist, 0, 1)

            # print("End getGlobalThreshold")

            # if(config.outputs.show_image_level>=1):
            #     hist = getPlotImg()
            #     show("Hist", hist, 0, 1)
            #     appendSaveImg(4,hist)
            #     appendSaveImg(5,hist)
            #     appendSaveImg(2,hist)

            perOMRThresholdAvg, totalQStripNo, totalQBoxNo = 0, 0, 0
            for QBlock in template.qBlocks:
                blockQStripNo = 1
                shift = QBlock.shift
                s, d = QBlock.orig, QBlock.dimensions
                key = QBlock.key[:3]
                # cv2.rectangle(final_marked,(s[0]+shift,s[1]),(s[0]+shift+d[0],s[1]+d[1]),CLR_BLACK,3)
                for _, qBoxPts in QBlock.traverse_pts:
                    # All Black or All White case
                    noOutliers = allQStdVals[totalQStripNo] < globalStdTHR
                    # print(totalQStripNo, qBoxPts[0].qNo, allQStdVals[totalQStripNo], "noOutliers:", noOutliers)
                    perQStripThreshold = getLocalThreshold(
                        qBoxPts[0].qNo,
                        allQStripArrs[totalQStripNo],
                        globalTHR,
                        noOutliers,
                        "Mean Intensity Histogram for "
                        + key
                        + "."
                        + qBoxPts[0].qNo
                        + "."
                        + str(blockQStripNo),
                        config.outputs.show_image_level >= 6,
                    )
                    # print(qBoxPts[0].qNo,key,blockQStripNo, "THR: ",round(perQStripThreshold,2))
                    perOMRThresholdAvg += perQStripThreshold

                    # Note: Little debugging visualization - view the particular Qstrip
                    # if(
                    #     0
                    #     # or "q17" in (qBoxPts[0].qNo)
                    #     # or (qBoxPts[0].qNo+str(blockQStripNo))=="q15"
                    #  ):
                    #     st, end = qStrip
                    #     show("QStrip: "+key+"-"+str(blockQStripNo), img[st[1] : end[1], st[0]+shift : end[0]+shift],0)

                    for pt in qBoxPts:
                        # shifted
                        x, y = (pt.x + QBlock.shift, pt.y)
                        boxval0 = allQVals[totalQBoxNo]
                        detected = perQStripThreshold > boxval0

                        # TODO: add an option to select PLUS SIGN RESPONSE READING
                        # extra_check_rects = []
                        # # [y,y+boxH,x,x+boxW]
                        # for rect in extra_check_rects:
                        #     # Note: This is NOT pixel-based thresholding, It is boxed mean-thresholding
                        #     boxval = cv2.mean(img[  rect[0]:rect[1] , rect[2]:rect[3] ])[0]
                        #     if(perQStripThreshold > boxval):
                        #         # for critical analysis
                        #         boxval0 = max(boxval,boxval0)
                        #         detected=True
                        #         break

                        if detected:
                            cv2.rectangle(
                                final_marked,
                                (int(x + boxW / 12), int(y + boxH / 12)),
                                (int(x + boxW - boxW / 12), int(y + boxH - boxH / 12)),
                                constants.CLR_DARK_GRAY,
                                3,
                            )
                        else:
                            cv2.rectangle(
                                final_marked,
                                (int(x + boxW / 10), int(y + boxH / 10)),
                                (int(x + boxW - boxW / 10), int(y + boxH - boxH / 10)),
                                constants.CLR_GRAY,
                                -1,
                            )

                        # TODO Make this part useful! (Abstract visualizer to check status)
                        if detected:
                            q, val = pt.qNo, str(pt.val)
                            cv2.putText(
                                final_marked,
                                val,
                                (x, y),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                constants.TEXT_SIZE,
                                (20, 20, 10),
                                int(1 + 3.5 * constants.TEXT_SIZE),
                            )
                            # Only send rolls multi-marked in the directory
                            multimarkedL = q in OMRresponse
                            multimarked = multimarkedL or multimarked
                            OMRresponse[q] = (
                                (OMRresponse[q] + val) if multimarkedL else val
                            )
                            multiroll = multimarkedL and "roll" in str(q)
                            # blackVals.append(boxval0)
                        # else:
                        # whiteVals.append(boxval0)

                        totalQBoxNo += 1
                        # /for qBoxPts
                    # /for qStrip

                    if config.outputs.show_image_level >= 5:
                        if key in allCBoxvals:
                            qNums[key].append(key[:2] + "_c" + str(blockQStripNo))
                            allCBoxvals[key].append(allQStripArrs[totalQStripNo])

                    blockQStripNo += 1
                    totalQStripNo += 1
                # /for QBlock

            # TODO: move this validation into template.py -
            if totalQStripNo == 0:
                print(
                    "\n\t UNEXPECTED Template Incorrect Error: totalQStripNo is zero! qBlocks: ",
                    template.qBlocks,
                )
                exit(21)

            perOMRThresholdAvg /= totalQStripNo
            perOMRThresholdAvg = round(perOMRThresholdAvg, 2)
            # Translucent
            cv2.addWeighted(
                final_marked, alpha, transp_layer, 1 - alpha, 0, final_marked
            )
            # Box types
            if config.outputs.show_image_level >= 5:
                # plt.draw()
                f, axes = plt.subplots(len(allCBoxvals), sharey=True)
                f.canvas.set_window_title(name)
                ctr = 0
                typeName = {"int": "Integer", "mcq": "MCQ", "med": "MED", "rol": "Roll"}
                for k, boxvals in allCBoxvals.items():
                    axes[ctr].title.set_text(typeName[k] + " Type")
                    axes[ctr].boxplot(boxvals)
                    # thrline=axes[ctr].axhline(perOMRThresholdAvg,color='red',ls='--')
                    # thrline.set_label("Average THR")
                    axes[ctr].set_ylabel("Intensity")
                    axes[ctr].set_xticklabels(qNums[k])
                    # axes[ctr].legend()
                    ctr += 1
                # imshow will do the waiting
                plt.tight_layout(pad=0.5)
                plt.show()

            if config.outputs.show_image_level >= 3 and final_align is not None:
                final_align = ImageUtils.resize_util_h(
                    final_align, int(config.dimensions.display_height)
                )
                # [final_align.shape[1],0])
                self.show("Template Alignment Adjustment", final_align, 0, 0)

            # TODO: refactor "type(savedir) != type(None) "
            if config.outputs.save_detections and type(savedir) != type(None):
                if multiroll:
                    savedir = savedir + "_MULTI_/"
                ImageUtils.saveImg(savedir + name, final_marked)

            ImageUtils.append_save_img(2, final_marked)

            for i in range(config.outputs.save_image_level):
                ImageUtils.saveOrShowStacks(i + 1, name, savedir)

            return OMRresponse, final_marked, multimarked, multiroll

        except Exception as e:
            raise e
        #     exc_type, exc_obj, exc_tb = sys.exc_info()
        #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        #     print("Error from readResponse: ", e)
        #     print(exc_type, fname, exc_tb.tb_lineno)


def printbuf(x):
    sys.stdout.write(str(x))
    sys.stdout.write("\r")