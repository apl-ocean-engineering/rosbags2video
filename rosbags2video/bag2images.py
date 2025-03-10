#!/usr/bin/env python3

from __future__ import division
import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.image import message_to_cvimage
from timeit import default_timer as timer
import sys
import os
import imageio
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait
import concurrent.futures

import rosbags2video
from rosbags2video import stamp_to_sec, sec_to_ns


def write_image(outpath, image):
    imageio.imwrite(outpath, image)


def write_frames(
    bag_reader,
    outdir,
    topics,
    sizes,
    start_time=0,
    stop_time=sys.maxsize,
    viz=False,
    encoding="bgr8",
    skip=1,
    use_bagtime=False,
):
    convert = {topics[i]: i for i in range(len(topics))}

    images = [
        np.zeros((sizes[i][1], sizes[i][0], 3), np.uint8) for i in range(len(topics))
    ]

    start = timer()
    num_msgs = 0

    pending = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        connections = [x for x in bag_reader.connections if x.topic in topics]
        for connection, t, rawdata in bag_reader.messages(
            connections=connections,
            start=sec_to_ns(start_time),
            stop=sec_to_ns(stop_time),
        ):
            topic = connection.topic
            msg = bag_reader.deserialize(rawdata, connection.msgtype)

            if use_bagtime:
                time = t / 1e9
            else:
                time = stamp_to_sec(msg.header.stamp)

            logging.debug("Topic %s updated at time %s seconds" % (topic, time))

            if num_msgs % skip == 0:
                # record the current information up to this point in time
                logging.info(
                    "Writing image %s at time %.6f seconds." % (num_msgs, time)
                )
                image = message_to_cvimage(msg, encoding)
                images[convert[topic]] = image
                merged_image = rosbags2video.merge_images(images, sizes)

                outpath = outdir / ("image_%06d.png" % num_msgs)
                logging.debug("Writing %s" % outpath)

                pending.append(executor.submit(write_image, outpath, merged_image))
                # imageio.imwrite( outpath, merged_image )

                if len(pending) > 10:
                    wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)

            num_msgs += 1

    end = timer()
    logging.info(f"Wrote {num_msgs} messages in {end-start:.2f} seconds")


def main():
    args = rosbags2video.images_argparser()

    args.outdir.mkdir(exist_ok=True)

    # convert numbers into rospy Time
    start_time = args.start
    stop_time = args.end

    for bagfile in args.bagfiles:
        logging.info("Proccessing bag %s." % bagfile)
        bag_reader = AnyReader([Path(os.path.join(Path.cwd(), Path(bagfile)))])
        bag_reader.open()

        logging.info("Calculating video sizes.")
        sizes = rosbags2video.get_sizes(
            bag_reader, topics=args.topic, index=args.index, scale=args.scale
        )

        logging.info("Calculating final image size.")
        out_width, out_height = rosbags2video.calc_out_size(sizes)
        logging.info(
            "Resulting video of width %s and height %s." % (out_width, out_height)
        )

        write_frames(
            bag_reader=bag_reader,
            outdir=args.outdir,
            topics=args.topic,
            sizes=sizes,
            start_time=start_time,
            stop_time=stop_time,
            encoding=args.encoding,
            skip=args.skip,
            use_bagtime=args.bag_time,
        )

        logging.info("Done.")


if __name__ == "__main__":
    main()
