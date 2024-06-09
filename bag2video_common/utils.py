#!/usr/bin/env python3

import cv2


def stamp_to_sec(stamp):
    return stamp.sec + 10.0e-10 * stamp.nanosec


def sec_to_ns(sec):
    return int(sec * 1e9)


def calc_out_size(sizes):
    return (sum(size[0] for size in sizes), sizes[0][1])


def merge_images(images, sizes):
    return cv2.hconcat([cv2.resize(images[i], sizes[i]) for i in range(len(images))])
