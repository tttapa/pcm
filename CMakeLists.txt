# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2022-2025, Intel Corporation

cmake_minimum_required(VERSION 3.26...4.2)

project(PCM VERSION 0000)
include(CTest)

include(CMakeDependentOption)
option(PCM_FUZZ "Enable fuzzing" OFF)
option(PCM_BUILD_EXECUTABLES "Build PCM utilities" ON)
option(PCM_VENDOR_PUGIXML "Use vendored pugixml library" ON)
option(PCM_WITH_PUGIXML "Use the pugixml library (using find_package)" OFF)
option(PCM_VENDOR_SIMDJSON "Use vendored simdjson library" ON)
option(PCM_WITH_SIMDJSON "Use the simdjson library (using find_package)" OFF)
option(PCM_WITH_OPENSSL "Use the OpenSSL library (using find_package)" OFF)
cmake_dependent_option(PCM_VENDOR_GTEST "Use vendored GoogleTest library" ON
                       "BUILD_TESTING" OFF)

if (NO_SSL)  # Deprecated, use PCM_WITH_OPENSSL=OFF instead
    message(STATUS "SSL is disabled")
    set(PCM_WITH_OPENSSL OFF)
endif()

include(GNUInstallDirs)
include(CheckCXXCompilerFlag)
include(CheckPIESupported)

message(STATUS "System: ${CMAKE_SYSTEM}")
if (UNIX AND NOT APPLE)
    if (${CMAKE_SYSTEM_NAME} STREQUAL "FreeBSD")
        set(FREE_BSD TRUE)
    else()
        set(LINUX TRUE)
    endif()
endif()

add_library(pcm-public-flags INTERFACE)
add_library(pcm-private-flags INTERFACE)
target_link_libraries(pcm-private-flags INTERFACE pcm-public-flags)
target_compile_definitions(pcm-public-flags INTERFACE
    "$<$<BOOL:${CMAKE_INSTALL_PREFIX}>:CMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}>")
# MSVC exception handling
target_compile_options(pcm-public-flags INTERFACE
    $<$<CXX_COMPILER_ID:MSVC>:/EHa>)
target_compile_definitions(pcm-public-flags INTERFACE
    $<$<CXX_COMPILER_ID:MSVC>:UNICODE _UNICODE>)
# Compiler warnings
target_compile_options(pcm-private-flags INTERFACE
    $<BUILD_INTERFACE:
        $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang,Intel,IntelLLVM>:
            -Wall -Wextra -Wno-unknown-pragmas>
        $<$<CXX_COMPILER_ID:MSVC>:
            /W3 /wd4251 /wd4273>>)

# Hardening
add_library(pcm-hardening-flags INTERFACE)
check_cxx_compiler_flag(-fstack-protector-strong HAS_SSP)
if(HAS_SSP)
    target_compile_options(pcm-hardening-flags INTERFACE -fstack-protector-strong)
endif()
check_pie_supported()
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(UNIX)  # APPLE, LINUX, FREE_BSD
    if(LINUX)
        target_compile_definitions(pcm-public-flags INTERFACE PCM_USE_PERF)
        target_link_options(pcm-private-flags INTERFACE
            $<$<CXX_COMPILER_ID:GNU,Clang,Intel,IntelLLVM>:-Wl,-z,now -Wl,-z,relro -Wl,-z,noexecstack>)
    endif()
    # TODO: these belong in a toolchain file or a preset, not in the main CMakeLists.txt
    target_compile_options(pcm-hardening-flags INTERFACE
        $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang,Intel,IntelLLVM>:
            -fstack-protector -ftrapv -fwrapv
            -fno-delete-null-pointer-checks -fno-strict-overflow
            -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer>)
    target_compile_definitions(pcm-hardening-flags INTERFACE
        $<$<CONFIG:Release,MinSizeRel,RelWithDebInfo>:_FORTIFY_SOURCE=2>)

endif()

if (MSVC)
    # SDL429 security flags: ASLR (/DYNAMICBASE) and DEP (/NXCOMPAT)
    target_link_options(pcm-hardening-flags INTERFACE
        /DYNAMICBASE /NXCOMPAT)
    # Optional Spectre mitigation for newer MSVC versions
    if (MSVC_TOOLSET_VERSION GREATER_EQUAL 141)
        target_compile_options(pcm-hardening-flags INTERFACE /Qspectre)
    endif()
endif()

if(PCM_FUZZ)
    target_compile_options(pcm-hardening-flags INTERFACE
        -fsanitize=fuzzer,address -fprofile-instr-generate -fcoverage-mapping)
endif(PCM_FUZZ)

if (UNIX)  # TODO: use a proper export header
    set(CMAKE_CXX_VISIBILITY_PRESET "default")
endif()

# TODO: apply ENABLE_EXPORTS property to all targets that need it instead of global CMAKE setting
set(CMAKE_ENABLE_EXPORTS ON)

# Installation
if (UNIX)
    if(LINUX)
        option(LINUX_SYSTEMD "Enable systemd unit file generation" OFF)
        set(LINUX_SYSTEMD_UNITDIR "${CMAKE_INSTALL_LIBDIR}/systemd/system"
            CACHE PATH "Directory to install systemd unit files")
        if(LINUX_SYSTEMD)
            message(STATUS "A systemd unit file will be generated")
            message(STATUS "LINUX_SYSTEMD_UNITDIR:${LINUX_SYSTEMD_UNITDIR}")
        else()
            message(STATUS "Set LINUX_SYSTEMD=TRUE for a systemd unit file.")
        endif()
    endif()
    # TODO: do we need to install all files in perfmon or just the ones needed for PCM to run?
    install(DIRECTORY "perfmon" DESTINATION ${CMAKE_INSTALL_DATADIR}/pcm)
endif()

# Threading library dependency
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# pugixml dependency
add_library(pcm-pugixml INTERFACE)
if (PCM_VENDOR_PUGIXML)
    set(PUGIXML_VENDOR_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/pugixml/src")
    if (EXISTS "${PUGIXML_VENDOR_DIR}/pugixml.cpp")
        message(STATUS "Local pugixml exists: ${PUGIXML_VENDOR_DIR}/pugixml.cpp")
        add_library(pugixml OBJECT ${PUGIXML_VENDOR_DIR}/pugixml.cpp)
        target_include_directories(pugixml PUBLIC ${PUGIXML_VENDOR_DIR})
        target_link_libraries(pugixml PRIVATE pcm-private-flags pcm-hardening-flags)
        target_link_libraries(pcm-pugixml INTERFACE $<BUILD_INTERFACE:pugixml>)
        target_compile_definitions(pcm-pugixml INTERFACE PCM_PUGIXML_AVAILABLE)
    else()
        message(WARNING "Local pugixml doesn't exist")
    endif()
elseif(PCM_WITH_PUGIXML)
    find_package(pugixml REQUIRED)
    target_link_libraries(pcm-pugixml INTERFACE pugixml::pugixml)
    target_compile_definitions(pcm-pugixml INTERFACE PCM_PUGIXML_AVAILABLE)
endif()

# simdjson dependency
add_library(pcm-simdjson INTERFACE)
if (PCM_VENDOR_SIMDJSON)
    set(SIMDJSON_VENDOR_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/simdjson/singleheader")
    if (EXISTS "${SIMDJSON_VENDOR_DIR}/simdjson.h")
        message(STATUS "Local simdjson exists: ${SIMDJSON_VENDOR_DIR}/simdjson.h")
        target_sources(pcm-simdjson INTERFACE $<BUILD_INTERFACE:${SIMDJSON_VENDOR_DIR}/simdjson.cpp>)
        target_include_directories(pcm-simdjson INTERFACE $<BUILD_INTERFACE:${SIMDJSON_VENDOR_DIR}>)
        target_compile_definitions(pcm-simdjson INTERFACE PCM_SIMDJSON_AVAILABLE)
    else()
        message(WARNING
            " ${SIMDJSON_VENDOR_DIR}/simdjson.h doesn't exist\n"
            " Use `git clone --recursive` flag when cloning pcm repository to clone simdjson submodule as well or\n"
            " update submodule with command 'git submodule update --init --recursive' or\n"
            " run 'git clone https://github.com/simdjson/simdjson.git' in 'src' directory to get simdjson library")
    endif()
elseif(PCM_WITH_SIMDJSON)
    find_package(simdjson REQUIRED)
    target_link_libraries(pcm-simdjson INTERFACE simdjson::simdjson)
    target_compile_definitions(pcm-simdjson INTERFACE SYSTEM_SIMDJSON)
    target_compile_definitions(pcm-simdjson INTERFACE PCM_SIMDJSON_AVAILABLE)
endif()

# OpenSSL dependency
add_library(pcm-openssl INTERFACE)
if (PCM_WITH_OPENSSL)
    message(STATUS "Compiling with SSL support, requires libssl-dev or openssl-devel or libopenssl-devel or libopenssl-dev package installed")
    message(STATUS "To disable SSL support, use -DPCM_WITH_OPENSSL=OFF option")
    find_package(OpenSSL 1.1.1 REQUIRED)
    target_link_libraries(pcm-openssl INTERFACE OpenSSL::SSL OpenSSL::Crypto)
    target_compile_definitions(pcm-openssl INTERFACE USE_SSL)
endif()

#######################
# Install
#######################

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

add_subdirectory(src)
add_subdirectory(examples)
if (BUILD_TESTING)
    add_subdirectory(tests)
endif()

message(STATUS "Install directory: ${CMAKE_INSTALL_PREFIX}")

#######################
# CPack (only UNIX)
#######################
if(UNIX)
    if(EXISTS "/etc/debian_version")      # for Debian family
        set(CPACK_GENERATOR "DEB")
        message(STATUS "CPACK_GENERATOR is DEB")
    elseif(EXISTS "/etc/redhat-release")  # for RHEL, Fedora, CentOs
        set(CPACK_GENERATOR "RPM")
        message(STATUS "CPACK_GENERATOR is RPM")
    else()
        if(EXISTS "/etc/os-release")
            file(READ "/etc/os-release" OS_PARAMS)
            string(REGEX MATCH "suse" OUT ${OS_PARAMS})  # for Suse-like systems
            if(OUT STREQUAL "suse")
                 set(CPACK_GENERATOR "RPM")
                 message(STATUS "CPACK_GENERATOR is RPM")
            else()
                set(CPACK_GENERATOR "TXZ")
                set(CPACK_SET_DESTDIR ON)
                message(STATUS "CPACK_GENERATOR is TXZ")
            endif()
        else()
            set(CPACK_GENERATOR "TXZ")
            set(CPACK_SET_DESTDIR ON)
            message(STATUS "CPACK_GENERATOR is TXZ")
        endif()
    endif()

    set(CPACK_PACKAGE_CONTACT "intel <roman.dementiev@intel.com>")
    set(CPACK_PACKAGE_NAME    "pcm")
    set(CPACK_PACKAGE_VERSION "0000")

    set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Intel(r) Performance Counter Monitor (Intel(r) PCM)")
    set(CPACK_PACKAGE_DESCRIPTION "\
    Intel(r) Performance Counter Monitor (Intel(r) PCM) is an application programming\n\
    interface (API) and a set of tools based on the API to monitor\n\
    performance and energy metrics of Intel(r) Core(tm), Xeon(r), Atom(tm)\n\
    and Xeon Phi(tm) processors. PCM works on Linux, Windows, Mac OS X,\n\
    FreeBSD and DragonFlyBSD operating systems.")
    set(CPACK_RPM_PACKAGE_DESCRIPTION ${CPACK_PACKAGE_DESCRIPTION})

    set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
    set(CPACK_RPM_PACKAGE_LICENSE   "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")

    set(CPACK_PACKAGE_INSTALL_DIRECTORY             ${CMAKE_INSTALL_PREFIX})
    set(CPACK_INSTALL_DEFAULT_DIRECTORY_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

    set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)
    set(CPACK_RPM_PACKAGE_RELOCATABLE  TRUE)

    set(CPACK_DEB_COMPONENT_INSTALL ON)
    set(CPACK_RPM_COMPONENT_INSTALL ON)

    include (CPack)
endif(UNIX)
