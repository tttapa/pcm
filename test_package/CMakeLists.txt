cmake_minimum_required(VERSION 3.15)
project(PackageTest C CXX)

find_package(pcm CONFIG REQUIRED)

add_executable(example example.c)
target_link_libraries(example PRIVATE pcm::pcm-lib)
