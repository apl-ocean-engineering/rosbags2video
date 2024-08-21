rosbags2video
=========

This codebase has migrate to using [rosbags](https://pypi.org/project/rosbags/) and [rosbags-image](https://pypi.org/project/rosbags-image/), and is designed to be installed with PDM (see below).

This version **does not** depend on having ROS installed.

## Dependencies

This version depends on:

* `imageio-ffmpeg`
* `numpy`
* `opencv-python`
* `rosbags`
* `rosbags-image`

PDM will automatically resolve these dependencies for the rosbags version.

## Installing the rosbags / rosbags-image version

This version uses [PDM](https://pdm-project.org/en/latest/) as its build engine.  To use:

1. Install PDM per the [install instructions](https://pdm-project.org/en/latest/#recommended-installation-method).

2. In the `rosbags2video` direectory

```
pdm use
pdm install
```

This will install dependencies in a venv.

3.  Activate the venv:

```
eval $(pdm venv activate)
```

The scripts can be called as `bag2video` or `bag2images`.  From there, see the `Usage` instructions below.

## Usage

```
usage: bag2video [-h]
                 [--topic TOPIC]
                 [--index INDEX]
                 [--scale SCALE]
                 [--outfile OUTFILE]
                 [--fps FPS]
                 [--imshow]
                 [--start START]
                 [--end END]
                 [--encoding {rgb8,bgr8,mono8}]
                 [--codec CODEC]
                 [--log LOG]
                 [--timestamp]
                 bagfiles [bagfiles ...]
```

The minimal usage requires an image topic, an output location, and one or more bagfiles:


```
bag2video -o test.mp4 --topic /image_raw a_bagfile.bag
```

If multiple bagfiles are specified, they are combined into a single, continuous movie.

Other options:

* `--scale` will scale the images by SCALE before adding to the video/image.  Typically SCALE is less than zero, e.g. 0.5 means shrink the image by 1/2 in both dimensions (1/4 the original number of pixels).
* `--timestamp` writes a timestamp in the image.

Every effort is made for the rospy and rosbags versions to have the same options and behavior.

# License

This version is heavily modified from code originally released by Oregon State University, and retains the original's [LICENSE](license).


-----
-----

# Original README

Convert images from multiple topics in a rosbag to a constant framerate video with topics displayed side to side. Conversion from timestamps to constant framerate is achieved through duplicating frames. Images for each topic will be scaled to the same height and placed side to side horizontally.

This should not be used for precise conversions. The primary purpose is to provide a quick visual representation for the image contents of a bag file for multiple topics at once. There are several quirks present as a tradeoff for simplicity and faster processing:

* The program updates for every relevant message in the bag file. Each update, the most recently processed images from each topic are horizontally concatenated. The resulting image is written for duration equal to the time since the last update. Black images are used as substitutes for topics that have not had a message.
* If a particular topic ends earlier than the rest, then the program will continue using the most recent image from that topic. This behavior may or may not be desirable.
* Because bag files use timestamps, there is no information on how long the last message should last. The program avoids this problem for the last output image by not writing it at all.

This script is heavily modified from the original; it uses Python 3.

# Usage
    usage: bag2video.py [-h] [--index INDEX] [--scale SCALE] [--outfile OUTFILE] [--fps FPS]
                        [--viz] [--start START] [--end END] [--encoding {rgb8,bgr8,mono8}]
                        [--fourcc FOURCC] [--log LOG]
                        bagfile topics [topics ...]

    Extract and encode video from bag files.

    positional arguments:
      bagfile               Specifies the location of the bag file.
      topics                Image topics to merge in output video.

    optional arguments:
      -h, --help            show this help message and exit
      --index INDEX, -i INDEX
                            Resizes all images to match the height of the topic specified.
                            Default 0.
      --scale SCALE, -x SCALE
                            Global scale for all images. Default 1.
      --outfile OUTFILE, -o OUTFILE
                            Destination of the video file. Defaults to the folder of the bag
                            file.
      --fps FPS, -f FPS     FPS of the output video. If not specified, FPS will be set to the
                            maximum frequency of the topics.
      --viz, -v             Display frames in a GUI window.
      --start START, -s START
                            Rostime representing where to start in the bag.
      --end END, -e END     Rostime representing where to stop in the bag.
      --encoding {rgb8,bgr8,mono8}
                            Encoding of the deserialized image. Default bgr8.
      --fourcc FOURCC, -c FOURCC
                            Specifies FourCC for the output video. Default MJPG.
      --log LOG, -l LOG     Logging level. Default INFO.


# License
