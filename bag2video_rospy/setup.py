#
# This setup.py describes the rospy / rosbag toolset
# and it designed to be imported by catkin_python_setup()
# in CMakeLists.txt
#
import setuptools

setuptools.setup(
    version="0.0.1",
    python_requires=">=3.6",
    install_requires=["numpy", "opencv-python", "imageio[ffmpeg]", "rospy"],
)
