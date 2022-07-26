cmake_minimum_required(VERSION 3.0.2)
project(bag2video)

find_package(catkin REQUIRED COMPONENTS
  sensor_msgs
)

catkin_python_setup()

catkin_package()

catkin_install_python(PROGRAMS
  bag2images.py
  bag2video.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
