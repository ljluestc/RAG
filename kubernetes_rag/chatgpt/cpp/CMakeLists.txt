cmake_minimum_required(VERSION 3.16)
project(inference_scheduler CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(inference_scheduler inference_scheduler.cpp)
target_link_libraries(inference_scheduler PRIVATE pthread)
