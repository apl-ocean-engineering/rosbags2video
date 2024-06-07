from __future__ import division
from rosbags.highlevel import AnyReader
from rosbags.image import message_to_cvimage
from timeit import default_timer as timer
from pathlib import Path
from datetime import datetime
import numpy as np
import sys, cv2
import logging
import traceback

def stamp_to_sec(stamp):
    return stamp.sec + 10.0e-10 * stamp.nanosec

def sec_to_ns(sec):
    return int(sec * 1e9)

def get_sizes(bag_reader, topics=None, index=0, scale=1.0):
    logging.debug(f"Resizing height to topic {topics[index]} (index {index}).")
    sizes = []

    for topic in topics:
        try:
            connections = [x for x in bag_reader.connections if x.topic == topic]
            for connection, timestamp, rawdata in bag_reader.messages(connections=connections):
                msg = bag_reader.deserialize(rawdata, connection.msgtype) # read one message

                # message_to_cvimage will transparently handle either Image of CompressedImage
                img = message_to_cvimage(msg)
                img_sz = img.shape

                # width, height
                sizes.append((img_sz[1], img_sz[0]))
                break
        except:
            logging.critical(f"No messages found for topic {topic}, or message does not have height/width.")
            traceback.print_exc()
            sys.exit(1)

    target_height = int(sizes[index][1]*scale)

    # output original and scaled sizes
    for i in range(len(topics)):
        logging.info(f"Topic {topics[i]} originally {sizes[i][0]} x {sizes[i][1]}" )
        image_height = sizes[i][1]
        image_width = sizes[i][0]

        # rescale to desired height while keeping aspect ratio
        sizes[i] = (int(1.0*image_width*target_height/image_height),target_height)
        logging.info(f"Topic {topics[i]} rescaled to {sizes[i][0]} x {sizes[i][1]}" )

    return sizes

def get_frequency(bag_reader,topics=None, start_time=0,stop_time=sys.maxsize):
    # uses the highest topic message frequency as framerate
    duration = min(10.0e-10 * bag_reader.duration, (stop_time-start_time))
    highest_freq = 0
    for topic in topics:
        msgcount = bag_reader.topics[topic].msgcount
        frequency = msgcount / duration
        highest_freq = max(highest_freq, frequency)

    try:
        assert highest_freq>0
    except:
        logging.critical("Unable to calculate framerate from topic frequency.")
        logging.critical("May be caused by a lack of messages.")
        traceback.print_exc()
        sys.exit(1)
    return highest_freq

def calc_out_size(sizes):
    return (sum(size[0] for size in sizes),sizes[0][1])

def merge_images(images, sizes):
    return cv2.hconcat([cv2.resize(images[i],sizes[i]) for i in range(len(images))])