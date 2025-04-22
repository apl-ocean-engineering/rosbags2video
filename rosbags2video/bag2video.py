#!/usr/bin/env python3

from __future__ import division
from rosbags.highlevel import AnyReader
from rosbags.image import message_to_cvimage
from timeit import default_timer as timer
from datetime import datetime
import numpy as np
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
    start_time=None,
    stop_time=None,
    add_timestamp=False,
    use_bagtime=False,
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

    if start_time:
        start_time = sec_to_ns(start_time)

    if stop_time:
        stop_time = sec_to_ns(stop_time)

    connections = [x for x in bag_reader.connections if x.topic in topics]
    for connection, t, rawdata in bag_reader.messages(
        connections=connections, start=start_time, stop=stop_time
    ):
        topic = connection.topic
        msg = bag_reader.deserialize(rawdata, connection.msgtype)
        # print(f'DEBUG: {msg.header.stamp}, {t}')
        # exit(0)

        if use_bagtime:
            time = t / 1e9
        else:
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
    args = rosbags2video.video_argparser()

    writer = None

    logging.info("Processing bags %s." % (args.bagfiles))

    outfile = args.outfile
    if outfile is None:
        if len(args.bagfiles) == 1:
            folder, name = os.path.split(args.bagfiles[0])
            outfile = os.path.join(folder, name[: name.rfind(".")]) + ".mp4"
        else:
            logging.error(
                "Multiple bagfiles specified, but no output file.  Can't automatically set output filename."
            )
            exit(-1)
    elif outfile.suffix == "":
        outfile = outfile.with_suffix(".mp4")

    with AnyReader(args.bagfiles) as bag_reader:
        fps = args.fps
        if fps:
            logging.info("Using manually set framerate of %.3f." % fps)
        else:
            logging.info("Calculating ideal output framerate.")
            logging.info(f"Start time: {args.start}")
            logging.info(f"End time: {args.end}")

            fps = rosbags2video.get_frequency(
                bag_reader, args.topic, args.start, args.end
            )
            logging.info("Output framerate of %.3f." % fps)

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
        with imageio.get_writer(
            outfile,
            format="FFMPEG",
            mode="I",
            fps=fps,
            quality=10,
            codec=args.codec,
        ) as writer:
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
                use_bagtime=args.bag_time,
            )
            logging.info("Done.")


if __name__ == "__main__":
    main()
