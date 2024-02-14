#!/usr/bin/env python3

from __future__ import division
from pathlib import Path
import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.image import message_to_cvimage
import sys, os, cv2, glob
from itertools import repeat
import imageio
import argparse
import logging
import traceback

def get_sizes(bag_reader, topics=None, index=0, scale=1.0, start_time=0, stop_time=sys.maxsize):
    logging.debug("Resizing height to topic %s (index %d)." % (topics[index] , index))
    sizes = []

    for topic in topics:
        try:
            connections = [x for x in bag_reader.connections if x.topic == topic]
            for connection, timestamp, rawdata in bag_reader.messages(connections=connections):
                msg = bag_reader.deserialize(rawdata, connection.msgtype) # read one message
                sizes.append((msg.width, msg.height))
                break
        except:
            logging.critical("No messages found for topic %s, or message does not have height/width." % topic)
            traceback.print_exc()
            sys.exit(1)

    target_height = int(sizes[index][1]*scale)

    # output original and scaled sizes
    for i in range(len(topics)):
        logging.info('Topic %s originally of height %s and width %s' % (topics[i],sizes[i][0],sizes[i][1]))
        image_height = sizes[i][1]
        image_width = sizes[i][0]

        # rescale to desired height while keeping aspect ratio
        sizes[i] = (int(1.0*image_width*target_height/image_height),target_height)
        logging.info('Topic %s rescaled to height %s and width %s.' % (topics[i],sizes[i][0],sizes[i][1]))

    return sizes

def get_frequency(bag_reader,topics=None, start_time=0,stop_time=sys.maxsize):
    # uses the highest topic message frequency as framerate
    duration = 10.0e-10 * min(bag_reader.duration, (stop_time-start_time))
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

def write_frames(bag_reader, writer, topics, sizes, fps, start_time=0, stop_time=sys.maxsize, viz=False, encoding='bgr8'):
    convert = { topics[i]:i for i in range(len(topics))}
    frame_duration = 1.0/fps

    images = [np.zeros((sizes[i][1],sizes[i][0],3), np.uint8) for i in range(len(topics))]
    frame_num = 0
    count = 1

    init = True

    connections = [x for x in bag_reader.connections if x.topic in topics]
    for connection, t, rawdata in bag_reader.messages(connections=connections):
        topic = connection.topic
        msg = bag_reader.deserialize(rawdata, connection.msgtype)
        # print(f'DEBUG: {msg.header.stamp}')
        # exit(0)
        time = to_sec(msg.header.stamp)
        if (init): 
            image = message_to_cvimage(msg, encoding)
            images[convert[topic]] = image
            frame_num = int(time/frame_duration)
            init = False
        else: 
            frame_num_next = int(time/frame_duration)
            reps = frame_num_next-frame_num
            logging.debug('Topic %s updated at time %s seconds, frame %s.' % (topic, time, frame_num_next))
            # prevent unnecessary calculations
            if reps>0:
                # record the current information up to this point in time
                logging.info('Writing image %s at time %.6f seconds, frame %s for %s frames.' % (count, time, frame_num, reps))
                merged_image = merge_images(images, sizes)
                for i in range(reps):
                    #writer.write(merged_image) # opencv
                    writer.append_data(merged_image) # imageio
                imshow('win', merged_image)
                frame_num = frame_num_next
                count += 1

            image = message_to_cvimage(msg, encoding)
            images[convert[topic]] = image

def imshow(win, img):
    logging.debug("Window redrawn.")
    cv2.imshow(win, img)
    cv2.waitKey(1)

def noshow(win, img):
    pass

def to_sec(stamp):
    return stamp.sec + 10.0e-10 * stamp.nanosec

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract and encode video from bag files.')
    parser.add_argument('bagfile', help='Specifies the location of the bag file.')
    parser.add_argument('topics', nargs='+',help='Image topics to merge in output video.')
    parser.add_argument('--index', '-i', action='store',default=0, type=int,
                        help='Resizes all images to match the height of the topic specified. Default 0.')
    parser.add_argument('--scale', '-x', action='store',default=1, type=float,
                        help='Global scale for all images. Default 1.')
    parser.add_argument('--outfile', '-o', action='store', default=None,
                        help='Destination of the video file. Defaults to the folder of the bag file.')
    parser.add_argument('--fps', '-f', action='store', default=None, type=float,
                        help='FPS of the output video. If not specified, FPS will be set to the maximum frequency of the topics.')
    parser.add_argument('--viz', '-v', action='store_true', help='Display frames in a GUI window.')
    parser.add_argument('--start', '-s', action='store', default=0, type=float,
                        help='Rostime representing where to start in the bag.')
    parser.add_argument('--end', '-e', action='store', default=sys.maxsize, type=float,
                        help='Rostime representing where to stop in the bag.')
    parser.add_argument('--encoding', choices=('rgb8', 'bgr8', 'mono8'), default='rgb8',
                        help='Encoding of the deserialized image. Default rgb8.')
    parser.add_argument('--codec', '-c', action='store', default='h264',
                        help='Specifies FFMPEG codec to use.  Defaults to h264')
    parser.add_argument('--log', '-l',action='store',default='INFO',
                        help='Logging level. Default INFO.')

    args = parser.parse_args()

    # logging setup
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',level=numeric_level)
    logging.info('Logging at level %s.',args.log.upper())
    if not args.viz:
        imshow = noshow

    try:
        assert args.start <= args.end
    except:
        logging.critical("Start time is after stop time.")
        traceback.print_exc()
        sys.exit(1)

    try:
        assert args.index < len(args.topics)
    except:
        logging.critical("Index specified for resizing is out of bounds.")
        traceback.print_exc()
        sys.exit(1)

    for bagfile in glob.glob(args.bagfile):
        logging.info('Proccessing bag %s.'% bagfile)
        outfile = args.outfile
        if outfile is None:
            folder, name = os.path.split(bagfile)
            outfile = os.path.join(folder, name[:name.rfind('.')]) + '.mp4'
        bag_reader = AnyReader([Path(os.path.join(Path.cwd(), Path(bagfile)))])
        bag_reader.open()

        fps = args.fps
        if not fps:
            logging.info('Calculating ideal output framerate.')
            fps = get_frequency(bag_reader, args.topics, args.start, args.end)
            logging.info('Output framerate of %.3f.'%fps)
        else:
            logging.info('Using manually set framerate of %.3f.'%fps)

        logging.info('Calculating video sizes.')
        sizes = get_sizes(bag_reader, topics=args.topics, index=args.index,scale = args.scale, start_time=args.start, stop_time=args.end)

        logging.info('Calculating final image size.')
        out_width, out_height = calc_out_size(sizes)
        logging.info('Resulting video of width %s and height %s.'%(out_width,out_height))

        logging.info('Opening video writer.')
        #fourcc = cv2.VideoWriter_fourcc(*args.fourcc) # opencv
        #writer = cv2.VideoWriter(outfile, fourcc, fps, (out_width,out_height)) # opencv
        writer = imageio.get_writer(outfile, format='FFMPEG', mode='I', fps=fps, quality=10, codec=args.codec)
        #writer = imageio.get_writer(outfile, fps=fps, mode='I', format="FFMPEG", macro_block_size=1) # imageio

        logging.info('Writing video at %s.'% outfile)
        write_frames(bag_reader=bag_reader, writer=writer, topics=args.topics, sizes=sizes, fps=fps, start_time=args.start, stop_time=args.end, encoding=args.encoding)
        #writer.release() # opencv
        writer.close() # imageio

        logging.info('Done.')
        bag_reader.close()
