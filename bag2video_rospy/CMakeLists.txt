cmake_minimum_required(VERSION 3.0.2)
project(bag2video)

find_package(catkin REQUIRED COMPONENTS
  sensor_msgs
)

catkin_python_setup()

catkin_package()

catkin_install_python(PROGRAMS
  scripts/bag2images
  scripts/bag2video
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
