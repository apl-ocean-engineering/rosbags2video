#
# This setup.py describes the rospy / rosbag toolset
# and it designed to be imported by catkin_python_setup()
# in CMakeLists.txt
#
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    version="0.0.1",
    packages={"bag2video": "rospy_src" },
    python_requires='>=3.6',
    install_requires=['numpy', 'opencv-python', 'imageio[ffmpeg]', 'rospy'],
)
