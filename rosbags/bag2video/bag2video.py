#!/usr/bin/env python3

from __future__ import division
from rosbags.highlevel import AnyReader
from rosbags.image import message_to_cvimage
from timeit import default_timer as timer
from pathlib import Path
from datetime import datetime
import numpy as np
import sys
import os
import cv2
import logging
import imageio
import argparse
import traceback

import bag2video
from bag2video import sec_to_ns, stamp_to_sec


def write_frames(
    bag_reader,
    writer,
    topics,
    sizes,
    fps,
    viz,
    encoding="bgr8",
    start_time=0,
    stop_time=sys.maxsize,
    add_timestamp=False,
):
    convert = {topics[i]: i for i in range(len(topics))}
    frame_duration = 1.0 / fps

    images = [
        np.zeros((sizes[i][1], sizes[i][0], 3), np.uint8) for i in range(len(topics))
    ]
    frame_num = 0

    start = timer()
    num_frames = 0
    num_msgs = 0

    init = True

    connections = [x for x in bag_reader.connections if x.topic in topics]
    for connection, t, rawdata in bag_reader.messages(
        connections=connections, start=sec_to_ns(start_time), stop=sec_to_ns(stop_time)
    ):
        topic = connection.topic
        msg = bag_reader.deserialize(rawdata, connection.msgtype)
        # print(f'DEBUG: {msg.header.stamp}')
        # exit(0)
        time = stamp_to_sec(msg.header.stamp)
        if init:
            image = message_to_cvimage(msg, encoding)
            images[convert[topic]] = image
            frame_num = int(time / frame_duration)
            init = False
        else:
            frame_num_next = int(time / frame_duration)
            reps = frame_num_next - frame_num
            logging.debug(
                "Topic %s updated at time %s seconds, frame %s."
                % (topic, time, frame_num_next)
            )
            # prevent unnecessary calculations
            if reps > 0:
                # record the current information up to this point in time
                logging.info(
                    "Writing image %s at time %.6f seconds, frame %s for %s frames."
                    % (num_msgs, time, frame_num, reps)
                )
                merged_image = bag2video.merge_images(images, sizes)

                if add_timestamp:
                    dt = datetime.fromtimestamp(time)

                    ts_font = cv2.FONT_HERSHEY_SIMPLEX
                    ts_thickness = 1
                    ts_color = (255, 0, 0)

                    ts_height = int(merged_image.shape[0] * 0.05)
                    ts_scale = cv2.getFontScaleFromHeight(
                        ts_font, ts_height, ts_thickness
                    )

                    datestr = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    merged_image = cv2.putText(
                        merged_image,
                        datestr,
                        (0, ts_height + 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        ts_scale,
                        ts_color,
                        ts_thickness,
                        cv2.LINE_AA,
                    )

                for i in range(reps):
                    # writer.write(merged_image) # opencv
                    writer.append_data(merged_image)  # imageio
                    num_frames += 1

                if viz:
                    imshow("win", merged_image)

                frame_num = frame_num_next
                num_msgs += 1

            image = message_to_cvimage(msg, encoding)
            images[convert[topic]] = image

    end = timer()
    logging.info(
        f"Wrote {num_msgs} messages to {num_frames} frames in {end-start:.2f} seconds"
    )


def imshow(win, img):
    logging.debug("Window redrawn.")
    cv2.imshow(win, img)
    cv2.waitKey(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract and encode video from bag files."
    )

    parser.add_argument(
        "bagfiles", nargs="+", help="Specifies the location of the bag file."
    )

    parser.add_argument(
        "--topic",
        action="append",
        help="Image topic to show in output video (maybe specified multiple times).",
    )

    parser.add_argument(
        "--index",
        "-i",
        action="store",
        default=0,
        type=int,
        help="Resizes all images to match the height of the topic specified. Default 0.",
    )
    parser.add_argument(
        "--scale",
        "-x",
        action="store",
        default=1,
        type=float,
        help="Global scale for all images. Default 1.",
    )
    parser.add_argument(
        "--outfile",
        "-o",
        action="store",
        default=None,
        help="Destination of the video file. Defaults to the folder of the bag file.",
    )
    parser.add_argument(
        "--fps",
        "-f",
        action="store",
        default=None,
        type=float,
        help="FPS of the output video. If not specified, FPS will be set to the maximum frequency of the topics.",
    )
    parser.add_argument(
        "--viz",
        "-v",
        action="store",
        default=False,
        help="Display frames in a GUI window.",
    )
    parser.add_argument(
        "--start",
        "-s",
        action="store",
        default=0,
        type=float,
        help="Rostime representing where to start in the bag.",
    )
    parser.add_argument(
        "--end",
        "-e",
        action="store",
        default=sys.maxsize,
        type=float,
        help="Rostime representing where to stop in the bag.",
    )
    parser.add_argument(
        "--encoding",
        choices=("rgb8", "bgr8", "mono8"),
        default="rgb8",
        help="Encoding of the deserialized image. Default rgb8.",
    )
    parser.add_argument(
        "--codec",
        "-c",
        action="store",
        default="h264",
        help="Specifies FFMPEG codec to use.  Defaults to h264",
    )
    parser.add_argument(
        "--log",
        "-l",
        action="store",
        default="INFO",
        help="Logging level. Default INFO.",
    )

    parser.add_argument(
        "--timestamp", action="store_true", help="Write timestamp into each image"
    )

    args = parser.parse_args()

    # logging setup
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % numeric_level)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=numeric_level
    )
    logging.info("Logging at level %s.", args.log.upper())

    logging.info(f"Movie will contain topics: {args.topic}")

    if args.start > args.end:
        logging.critical("Start time is after stop time.")
        traceback.print_exc()
        sys.exit(1)

    writer = None

    if args.index >= len(args.topic):
        logging.critical("Index specified for resizing is out of bounds.")
        traceback.print_exc()
        sys.exit(1)

    for bagfile in args.bagfiles:
        logging.info("Proccessing bag %s." % bagfile)
        outfile = args.outfile
        if outfile is None:
            folder, name = os.path.split(bagfile)
            outfile = os.path.join(folder, name[: name.rfind(".")]) + ".mp4"
        bag_reader = AnyReader([Path(os.path.join(Path.cwd(), Path(bagfile)))])
        bag_reader.open()

        if not writer:
            fps = args.fps
            if not fps:
                logging.info("Calculating ideal output framerate.")
                fps = bag2video.get_frequency(
                    bag_reader, args.topic, args.start, args.end
                )
                logging.info("Output framerate of %.3f." % fps)
            else:
                logging.info("Using manually set framerate of %.3f." % fps)

            logging.info("Calculating video sizes.")
            sizes = bag2video.get_sizes(
                bag_reader, topics=args.topic, index=args.index, scale=args.scale
            )

            logging.info("Calculating final image size.")
            out_width, out_height = bag2video.calc_out_size(sizes)
            logging.info(
                "Resulting video of width %s and height %s." % (out_width, out_height)
            )

            logging.info("Opening video writer.")
            writer = imageio.get_writer(
                outfile,
                format="FFMPEG",
                mode="I",
                fps=fps,
                quality=10,
                codec=args.codec,
            )

        logging.info("Writing video at %s." % outfile)
        write_frames(
            bag_reader=bag_reader,
            writer=writer,
            topics=args.topic,
            sizes=sizes,
            fps=fps,
            viz=args.viz,
            encoding=args.encoding,
            start_time=args.start,
            stop_time=args.end,
            add_timestamp=args.timestamp,
        )
        logging.info("Done.")
        bag_reader.close()

    writer.close()


if __name__ == "__main__":
    main()
