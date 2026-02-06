# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2022-2024, Intel Corporation

set(CMAKE_TEST_BINARY_DIR ${CMAKE_BINARY_DIR}/bin/tests)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_TEST_BINARY_DIR})

if (UNIX)
    # daemon_alignment_test on Linux and Unix
    add_executable(daemon_alignment_test daemon_alignment_test.cpp)

    if (LINUX)
        add_executable(urltest urltest.cpp)
        target_link_libraries(urltest Threads::Threads pcm::pcm-static)
    endif()

    # GoogleTest
    if (PCM_VENDOR_GTEST)
        if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/googletest/googletest/include/gtest/gtest.h")
            add_subdirectory(googletest EXCLUDE_FROM_ALL)
        else()
            message(WARNING
                "Local googletest does not exist - unit tests will not be built.\n"
                "If you need unit tests, please update submodules with the command: 'git submodule update --init --recursive'.\n")
        endif()
    else()
        find_package(GTest REQUIRED)
    endif()
    if (TARGET GTest::gtest)
        add_subdirectory(utests)
    else()
        message(WARNING "GTest not found, unit tests will not be built.")
    endif()
endif(UNIX)

if (PCM_FUZZ)
    if (NOT TARGET OpenSSL::SSL)
        message(FATAL_ERROR "OpenSSL is required for fuzzing targets. Please enable OpenSSL support with -DPCM_WITH_OPENSSL=ON")
    endif()
    set(SSL_LIBS OpenSSL::SSL OpenSSL::Crypto)
    add_executable(urltest-fuzz urltest-fuzz.cpp)
    add_executable(pcm-sensor-server-fuzz pcm-sensor-server-fuzz.cpp)
    add_executable(pcm-sensor-server-ssl-fuzz pcm-sensor-server-fuzz.cpp)
    target_compile_options(pcm-sensor-server-fuzz PRIVATE -DUSE_SSL=1)
    target_compile_options(pcm-sensor-server-ssl-fuzz PRIVATE -DUSE_SSL=1 -DFUZZ_USE_SSL=1)
    add_executable(pcm-fuzz pcm-fuzz.cpp)
    add_executable(pcm-memory-fuzz pcm-memory-fuzz.cpp)
    target_link_libraries(urltest-fuzz Threads::Threads pcm::pcm-static)
    target_link_libraries(pcm-sensor-server-fuzz Threads::Threads pcm::pcm-static ${SSL_LIBS})
    target_link_libraries(pcm-sensor-server-ssl-fuzz Threads::Threads pcm::pcm-static ${SSL_LIBS})
    target_link_libraries(pcm-fuzz Threads::Threads pcm::pcm-static)
    target_link_libraries(pcm-memory-fuzz Threads::Threads pcm::pcm-static)
endif()
