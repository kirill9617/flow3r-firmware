cmake_minimum_required(VERSION 3.12)

set(IDF_TARGET esp32s3)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsingle-precision-constant -Wdouble-promotion")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(flow3r)

