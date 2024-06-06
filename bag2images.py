#!/usr/bin/env python3

from __future__ import division
import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.image import message_to_cvimage
from timeit import default_timer as timer
import sys, os, cv2, glob
import imageio
import argparse
import logging
import traceback
from pathlib import Path
from cv_bridge import CvBridge
from concurrent.futures import ThreadPoolExecutor, wait
import concurrent.futures

import bag2lib
from bag2lib import stamp_to_sec, sec_to_ns

def write_image( outpath, image ):
    imageio.imwrite(outpath, image )

def write_frames(bag_reader, outdir, topics, sizes, start_time=0,
                    stop_time=sys.maxsize, viz=False, encoding='bgr8', skip=1):
    bridge = CvBridge()
    convert = { topics[i]:i for i in range(len(topics))}

    images = [np.zeros((sizes[i][1],sizes[i][0],3), np.uint8) for i in range(len(topics))]

    start = timer()
    num_msgs = 0

    pending = []

    with ThreadPoolExecutor(max_workers=2) as executor:

        connections = [x for x in bag_reader.connections if x.topic in topics]
        for connection, t, rawdata in bag_reader.messages(connections=connections, start=sec_to_ns(start_time), stop=sec_to_ns(stop_time)):
            topic = connection.topic
            msg = bag_reader.deserialize(rawdata, connection.msgtype)
            time = stamp_to_sec(msg.header.stamp)

            logging.debug('Topic %s updated at time %s seconds' % (topic, time ))

            if (num_msgs % skip == 0):

                # record the current information up to this point in time
                logging.info('Writing image %s at time %.6f seconds.' % (num_msgs, time) )
                image = np.asarray(bridge.imgmsg_to_cv2(msg, encoding))
                images[convert[topic]] = image
                merged_image = bag2lib.merge_images(images, sizes)

                outpath = outdir / ( "image_%06d.png" % num_msgs )
                logging.debug("Writing %s" % outpath)

                pending.append(executor.submit( write_image, outpath, merged_image ))
                #imageio.imwrite( outpath, merged_image )

                if len(pending) > 10:
                    wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)

            num_msgs += 1


    end = timer()
    logging.info(f"Wrote {num_msgs} messages in {end-start:.2f} seconds")


def main():
    parser = argparse.ArgumentParser(description='Extract and encode video from bag files.')

    parser.add_argument('bagfiles', nargs="+", help='Specifies the location of the bag file.')

    parser.add_argument('--topic', nargs=1, help='Image topic to show in output video (maybe specified multiple times).')

    parser.add_argument('--index', '-i', action='store',default=0, type=int,
                        help='Resizes all images to match the height of the topic specified. Default 0.')
    parser.add_argument('--scale', '-x', action='store',default=1, type=float,
                        help='Global scale for all images. Default 1.')
    parser.add_argument('--outdir', '-o', action='store', required=True, type=Path,
                        help='Destination directory for output')

    parser.add_argument('--start', '-s', action='store', default=0, type=float,
                        help='Rostime representing where to start in the bag.')
    parser.add_argument('--end', '-e', action='store', default=sys.maxsize, type=float,
                        help='Rostime representing where to stop in the bag.')

    parser.add_argument('--skip', default=1, type=int,
                        help='Extract every N\'th image.')


    parser.add_argument('--encoding', choices=('rgb8', 'bgr8', 'mono8'), default='bgr8',
                        help='Encoding of the deserialized image. Default bgr8.')

    parser.add_argument('--log', '-l',action='store',default='INFO',
                        help='Logging level. Default INFO.')

    parser.add_argument("--timestamp", action='store_true', help="Write timestamp into each image")


    args = parser.parse_args()

    # logging setup
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',level=numeric_level)
    logging.info('Logging at level %s.',args.log.upper())

    args.outdir.mkdir(exist_ok=True)

    # convert numbers into rospy Time
    start_time=args.start
    stop_time=args.end

    try:
        assert start_time <= stop_time
    except:
        logging.critical("Start time is after stop time.")
        traceback.print_exc()
        sys.exit(1)

    try:
        assert args.index < len(args.topic)
    except:
        logging.critical("Index specified for resizing is out of bounds.")
        traceback.print_exc()
        sys.exit(1)

    for bagfile in args.bagfiles:
        logging.info('Proccessing bag %s.'% bagfile)
        bag_reader = AnyReader([Path(os.path.join(Path.cwd(), Path(bagfile)))])
        bag_reader.open()

        logging.info('Calculating video sizes.')
        sizes = bag2lib.get_sizes(bag_reader, topics=args.topic, index=args.index,scale = args.scale)

        logging.info('Calculating final image size.')
        out_width, out_height = bag2lib.calc_out_size(sizes)
        logging.info('Resulting video of width %s and height %s.'%(out_width,out_height))

        write_frames(bag_reader=bag_reader, outdir=args.outdir, topics=args.topic, sizes=sizes,
                         start_time=start_time, stop_time=stop_time, encoding=args.encoding, skip=args.skip)

        logging.info('Done.')

if __name__ == '__main__':
    main()