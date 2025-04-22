import argparse
import logging
from pathlib import Path
from rosbags.highlevel import AnyReader


def argparser_common(which_output):
    parser = argparse.ArgumentParser(
        description=f"Extract and encode {which_output} from bag files."
    )

    parser.add_argument(
        "bagfiles", nargs="+", type=Path, help="Specifies the location of the bag file."
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
        "--start",
        "-s",
        action="store",
        default=None,
        type=float,
        help="Rostime representing where to start in the bag.",
    )

    parser.add_argument(
        "--end",
        "-e",
        action="store",
        default=None,
        type=float,
        help="Rostime representing where to stop in the bag.",
    )

    parser.add_argument(
        "--log",
        "-l",
        action="store",
        default="INFO",
        help="Logging level. Default INFO.",
    )

    parser.add_argument(
        "--bag-time",
        action="store_true",
        help="Use bagfile time rather than header.stamp",
    )

    parser.add_argument(
        "--timestamp", action="store_true", help="Write timestamp into each image"
    )

    return parser


def parse_and_validate(parser):
    args = parser.parse_args()

    # logging setup
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % numeric_level)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=numeric_level
    )
    logging.info("Logging at level %s.", args.log.upper())

    # Checking for the topic
    topics = args.topic

    if topics is None or len(topics) == 0:
        # ignore args.topic
        for bagfile in args.bagfiles:
            logging.info("No topics specified, checking bags for image topics")

            with AnyReader(args.bagfiles) as bag_reader:
                image_topics_list = [
                    conn.topic
                    for conn in bag_reader.connections
                    if "Image" in conn.msgtype
                ]

                if len(image_topics_list) > 1:
                    logging.info(
                        f"Multiple image topics detected: {str(image_topics_list)}"
                    )
                    logging.info(
                        "Please specify image topics using the --topic argument."
                    )
                    exit(0)
                else:
                    topics = image_topics_list
                    break

    logging.info(f"Output will contain the topic: {topics}")

    if args.start and args.end and args.start > args.end:
        parser.error("Start time is after stop time.")

    if args.index >= len(topics):
        parser.error("Index specified for resizing is out of bounds.")

    args.topic = topics
    return args


def video_argparser():
    parser = argparser_common("video")

    parser.add_argument(
        "--outfile",
        "-o",
        type=Path,
        required=True,
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
        "--imshow",
        action="store_true",
        default=False,
        help="Display frames in a GUI window.",
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

    return parse_and_validate(parser)


def images_argparser():
    parser = argparser_common("images")

    parser.add_argument(
        "--outdir",
        "-o",
        type=Path,
        required=True,
        help="Destination directory for output",
    )

    parser.add_argument("--skip", default=1, type=int, help="Extract every N'th image.")

    parser.add_argument(
        "--encoding",
        choices=("rgb8", "bgr8", "mono8"),
        default="bgr8",
        help="Encoding of the deserialized image. Default bgr8.",
    )

    return parse_and_validate(parser)
