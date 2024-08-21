import argparse
import sys
import logging
from pathlib import Path


def argparser_common(which_output):
    parser = argparse.ArgumentParser(
        description=f"Extract and encode {which_output} from bag files."
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
        "--log",
        "-l",
        action="store",
        default="INFO",
        help="Logging level. Default INFO.",
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

    logging.info(f"Movie will contain topics: {args.topic}")

    if args.start > args.end:
        parser.error("Start time is after stop time.")

    if args.index >= len(args.topic):
        parser.error("Index specified for resizing is out of bounds.")

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
