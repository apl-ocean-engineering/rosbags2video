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

import rosbags2video
from rosbags2video import sec_to_ns, stamp_to_sec


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
    add_raw_timestamp=False,
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
                merged_image = rosbags2video.merge_images(images, sizes)

                merged_image = embed_timestamp(
                    merged_image, time, add_timestamp, add_raw_timestamp
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


def embed_timestamp(merged_image, time, add_timestamp, add_raw_timestamp):
    raw_y_offset = 0

    ts_font = cv2.FONT_HERSHEY_SIMPLEX
    ts_thickness = 2
    ts_color = (0, 255, 0)

    ts_height = int(merged_image.shape[0] * 0.05)
    ts_scale = cv2.getFontScaleFromHeight(ts_font, ts_height, ts_thickness)

    text_width = 0

    if add_timestamp:
        dt = datetime.fromtimestamp(time)

        datestr = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        text_sz, baseline = cv2.getTextSize(datestr, ts_font, ts_scale, ts_thickness)

        merged_image = cv2.rectangle(
            merged_image, (0, 0), (text_sz[0], text_sz[1] + 15), (0, 0, 0, 0), -1
        )

        merged_image = cv2.putText(
            merged_image,
            datestr,
            (0, ts_height + 10),
            ts_font,
            ts_scale,
            ts_color,
            ts_thickness,
            cv2.LINE_AA,
        )

        raw_y_offset = text_sz[1] + 15
        text_width = text_sz[0]

    if add_raw_timestamp:
        timestr = f"{time:.4f}"

        text_sz, baseline = cv2.getTextSize(timestr, ts_font, ts_scale, ts_thickness)

        box_width = max(text_width, text_sz[0])

        merged_image = cv2.rectangle(
            merged_image,
            (0, raw_y_offset),
            (box_width, raw_y_offset + text_sz[1] + 15),
            (0, 0, 0, 0),
            -1,
        )

        merged_image = cv2.putText(
            merged_image,
            timestr,
            (0, raw_y_offset + ts_height + 10),
            ts_font,
            ts_scale,
            ts_color,
            ts_thickness,
            cv2.LINE_AA,
        )

    return merged_image


def imshow(win, img):
    logging.debug("Window redrawn.")
    cv2.imshow(win, img)
    cv2.waitKey(1)


def main():
    args = rosbags2video.video_argparser()

    writer = None

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
                fps = rosbags2video.get_frequency(
                    bag_reader, args.topic, args.start, args.end
                )
                logging.info("Output framerate of %.3f." % fps)
            else:
                logging.info("Using manually set framerate of %.3f." % fps)

            logging.info("Calculating video sizes.")
            sizes = rosbags2video.get_sizes(
                bag_reader, topics=args.topic, index=args.index, scale=args.scale
            )

            logging.info("Calculating final image size.")
            out_width, out_height = rosbags2video.calc_out_size(sizes)
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
            viz=args.imshow,
            encoding=args.encoding,
            start_time=args.start,
            stop_time=args.end,
            add_timestamp=args.timestamp,
            add_raw_timestamp=args.raw_timestamp,
        )
        logging.info("Done.")
        bag_reader.close()

    writer.close()


if __name__ == "__main__":
    main()
