# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2009-2025, Intel Corporation

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_TEST_BINARY_DIR}/utests)

project(pcm_utests LANGUAGES CXX)
enable_testing()

if(APPLE)
    include_directories("${CMAKE_SOURCE_DIR}/src/MacMSRDriver") # target_include_directories doesn't work
    set(LIBS PcmMsr Threads::Threads pcm::pcm-static)
else()
    set(LIBS Threads::Threads pcm::pcm-static)
endif()

add_executable(lspci-utest lspci-utest.cpp ../../src/lspci.cpp)
add_executable(pcm-iio-utest pcm-iio-utest.cpp ../../src/pcm-iio-pmu.cpp ../../src/pcm-iio-topology.cpp)
add_executable(read-number-utest read-number-utest.cpp)

configure_file(
    ${CMAKE_SOURCE_DIR}/src/opCode-6-174.txt
    ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/opCode-6-174.txt
    COPYONLY
)

target_link_libraries(
    lspci-utest
    GTest::gtest_main
    GTest::gmock_main
    ${LIBS}
)

target_link_libraries(
    pcm-iio-utest
    GTest::gtest_main
    GTest::gmock_main
    ${LIBS}
)

target_link_libraries(
    read-number-utest
    GTest::gtest_main
    GTest::gmock_main
    ${LIBS}
)

include(GoogleTest)
gtest_discover_tests(lspci-utest
    PROPERTIES WORKING_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})
gtest_discover_tests(pcm-iio-utest
    PROPERTIES WORKING_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})
gtest_discover_tests(read-number-utest
    PROPERTIES WORKING_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})
