# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2022-2025, Intel Corporation

# All pcm-* executables
set(PROJECT_NAMES
    pcm pcm-numa pcm-latency pcm-power pcm-msr pcm-memory pcm-tsx pcm-pcie
    pcm-core pcm-iio pcm-pcicfg pcm-mmio pcm-tpmi pcm-raw pcm-accel
    pcm-sensor-server)
if (UNIX)
    list(APPEND PROJECT_NAMES pcm-sensor)
endif()

# Source files
set(PCM_SOURCES
    pcm-accel-common.cpp msr.cpp cpucounters.cpp pci.cpp mmio.cpp tpmi.cpp
    pmt.cpp bw.cpp utils.cpp topology.cpp debug.cpp threadpool.cpp
    uncore_pmu_discovery.cpp pcm-iio-pmu.cpp pcm-iio-topology.cpp lspci.cpp
    dashboard.cpp)
if (UNIX AND NOT APPLE)
    list(APPEND PCM_SOURCES resctrl.cpp)
endif()
if (MSVC)
    list(APPEND PCM_SOURCES winpmem/winpmem.cpp)
endif()

# Flags and dependencies
add_library(pcm-core-flags INTERFACE)
if(FREE_BSD)
    target_link_libraries(pcm-core-flags INTERFACE execinfo)  # needed by utils
endif()
target_link_libraries(pcm-core-flags INTERFACE pcm-pugixml)
target_link_libraries(pcm-core-flags INTERFACE pcm-private-flags pcm-hardening-flags)

# Headers
add_library(pcm-headers INTERFACE)
target_sources(pcm-headers INTERFACE FILE_SET HEADERS
    BASE_DIRS ${CMAKE_CURRENT_SOURCE_DIR}
    FILES uncore_pmu_discovery.h mmio.h pmt.h favicon.ico.h resctrl.h
          topology.h msr.h cpuasynchcounter.h pcm-iio-topology.h dashboard.h
          cpucounters.h mutex.h pci.h debug.h topologyentry.h threadpool.h
          exceptions/unsupported_processor_exception.hpp lspci.h tpmi.h types.h
          bw.h pcm-accel-common.h pcm-pcie.h version.h width_extender.h pcm-iio-pmu.h)
target_link_libraries(pcm-headers INTERFACE pcm-public-flags)

if (UNIX)  # LINUX, FREE_BSD, APPLE
    # libpcm.a
    add_library(pcm-static STATIC ${PCM_SOURCES})
    add_library(PCM_STATIC ALIAS pcm-static) # backwards compatibility
    set_target_properties(pcm-static PROPERTIES OUTPUT_NAME pcm)
    target_link_libraries(pcm-static PRIVATE pcm-core-flags PUBLIC pcm-headers)

    # libpcm.a with -DPCM_SILENT for Release*
    add_library(pcm-static-silent STATIC ${PCM_SOURCES})
    add_library(PCM_STATIC_SILENT ALIAS pcm-static-silent)
    set_target_properties(pcm-static-silent PROPERTIES OUTPUT_NAME pcm-silent)
    set(PCM_SILENT_DEF $<$<CONFIG:Release,MinSizeRel,RelWithDebInfo>:PCM_SILENT>)
    target_compile_definitions(pcm-static-silent PRIVATE ${PCM_SILENT_DEF})
    target_link_libraries(pcm-static-silent PRIVATE pcm-core-flags PUBLIC pcm-headers)

    # libpcm.so
    add_library(pcm-lib SHARED pcm-core.cpp)
    add_library(PCM_SHARED ALIAS pcm-lib) # backwards compatibility
    set_target_properties(pcm-lib PROPERTIES OUTPUT_NAME pcm)
    target_compile_definitions(pcm-lib PRIVATE PCM_SHARED_LIBRARY)
    # PCM_SILENT in Release* for pcm-core.cpp
    target_compile_definitions(pcm-lib PRIVATE ${PCM_SILENT_DEF})
    target_link_libraries(pcm-lib PRIVATE pcm-pugixml)
    target_link_libraries(pcm-lib PRIVATE pcm-private-flags pcm-hardening-flags)
    target_link_libraries(pcm-lib PUBLIC pcm-headers)

    if (APPLE)
        add_subdirectory(MacMSRDriver)
        # TODO: check why the comment below was added and fix it
        include_directories("${CMAKE_SOURCE_DIR}/src/MacMSRDriver") # target_include_directories doesn't work
        target_link_libraries(pcm-lib PRIVATE pcm-static-silent PcmMsr Threads::Threads)
    else()
        target_link_libraries(pcm-lib PRIVATE pcm-static-silent Threads::Threads)
    endif()
endif(UNIX)

if (MSVC)
    # windows/* files -> PCM_STATIC
    add_library(pcm-static STATIC ${PCM_SOURCES} windows/stdafx.cpp freegetopt/getopt.cpp)
    add_library(PCM_STATIC ALIAS pcm-static)
    target_compile_definitions(pcm-static PRIVATE _CONSOLE)
    target_link_libraries(pcm-static PRIVATE pcm-core-flags PUBLIC pcm-headers)

    # Graphical perfmon front-end: pcm-lib, pcm-service
    add_library(pcm-lib SHARED ${PCM_SOURCES} dllmain.cpp pcm-lib.cpp)
    set_target_properties(pcm-lib PROPERTIES OUTPUT_NAME pcm-lib)
    target_compile_definitions(pcm-lib PRIVATE _WINDOWS _USRDLL PCM_EXPORTS _WINDLL)
    target_link_libraries(pcm-lib PRIVATE pcm-core-flags PUBLIC pcm-headers)

    # Pcm-service files: PCM_SHARED + AssemblyInfo.cpp PCMInstaller.cpp PCMService.cpp
    add_executable(pcm-service windows/PCMInstaller.cpp windows/PCMService.cpp windows/AssemblyInfo.cpp)
    target_compile_definitions(pcm-service PRIVATE _CONSOLE)
    set_target_properties(pcm-service PROPERTIES LINK_FLAGS "/INCREMENTAL:NO" COMMON_LANGUAGE_RUNTIME "")
    set_property(TARGET pcm-service PROPERTY VS_DOTNET_REFERENCES "System;System.Configuration.Install;System.Data;System.Management;System.ServiceProcess;System.Xml")
    target_link_libraries(pcm-service PRIVATE pcm-lib)
    target_link_libraries(pcm-service PRIVATE pcm-private-flags pcm-hardening-flags)
endif(MSVC)

if (PCM_BUILD_EXECUTABLES)
    foreach(PROJ_NAME ${PROJECT_NAMES})
        add_executable(${PROJ_NAME} ${PROJ_NAME}.cpp)
        target_link_libraries(${PROJ_NAME} PRIVATE pcm-static)
        target_link_libraries(${PROJ_NAME} PRIVATE pcm-private-flags pcm-hardening-flags)

        if(PROJ_NAME STREQUAL pcm-raw)
            target_link_libraries(${PROJ_NAME} PRIVATE pcm-simdjson)
        elseif(PROJ_NAME STREQUAL pcm-sensor-server)
            target_link_libraries(${PROJ_NAME} PRIVATE pcm-openssl)
            target_sources(${PROJ_NAME} PRIVATE pcm-accel-common.cpp)
            target_sources(${PROJ_NAME} PRIVATE FILE_SET HEADERS
                BASE_DIRS ${CMAKE_SOURCE_DIR} FILES pcm-accel-common.h)
        endif()

        if(LINUX OR FREE_BSD)
            target_link_libraries(${PROJ_NAME} PRIVATE Threads::Threads)
        elseif(APPLE)
            target_link_libraries(${PROJ_NAME} PRIVATE Threads::Threads PcmMsr)
        elseif(MSVC)
            # TODO: the comment below does not seem to be accurate
            target_compile_definitions(${PROJ_NAME} PRIVATE _CONSOLE) # for all, except pcm-lib and pcm-service
        endif()
    endforeach()
endif()

if(LINUX)
    # Daemon & client
    add_executable(daemon "daemon/daemon.cpp" "daemon/main.cpp")
    set_target_properties(daemon PROPERTIES OUTPUT_NAME "pcm-daemon")
    target_link_libraries(daemon PRIVATE pcm-static Threads::Threads)
    target_link_libraries(daemon PRIVATE pcm-private-flags pcm-hardening-flags)

    add_executable(client "client/client.cpp" "client/main.cpp")
    set_target_properties(client PROPERTIES OUTPUT_NAME "pcm-client")
    target_link_libraries(client PRIVATE Threads::Threads)
    target_link_libraries(client PRIVATE pcm-private-flags pcm-hardening-flags)
endif()

#######################
# Install
#######################

# Install executables
if (PCM_BUILD_EXECUTABLES)
    foreach(PROJ_NAME ${PROJECT_NAMES})
        if(PROJ_NAME STREQUAL pcm-sensor-server)
            if(LINUX_SYSTEMD)
                configure_file(pcm-sensor-server.service.in ${CMAKE_BINARY_DIR}/pcm-sensor-server.service @ONLY)
                install(FILES ${CMAKE_BINARY_DIR}/pcm-sensor-server.service DESTINATION "${LINUX_SYSTEMD_UNITDIR}")
            endif()
        endif()

        if(UNIX)
            install(TARGETS ${PROJ_NAME} RUNTIME DESTINATION ${CMAKE_INSTALL_SBINDIR})
        endif()
        # TODO: Why no Windows install?
    endforeach()
endif()

# Copy extra files to build directory for executables to find them in build tree
if (PCM_BUILD_EXECUTABLES)
    file(GLOB OPCODE_FILES "opCode*.txt")
    foreach(opcode_file ${OPCODE_FILES})
        add_custom_command(TARGET pcm-iio POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                ${opcode_file}
                $<TARGET_FILE_DIR:pcm-iio>)
    endforeach()

    add_custom_command(TARGET pcm-raw POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory_if_different
            ${PROJECT_SOURCE_DIR}/src/PMURegisterDeclarations
            $<TARGET_FILE_DIR:pcm-raw>/PMURegisterDeclarations)

    if(MSVC)
        add_custom_command(TARGET pcm-service POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                ${PROJECT_SOURCE_DIR}/src/windows/pcm-service.exe.config
                $<TARGET_FILE_DIR:pcm-service>)
    endif(MSVC)
endif()

if (LINUX)
    install(TARGETS daemon client RUNTIME DESTINATION ${CMAKE_INSTALL_SBINDIR})
endif()

if (UNIX) # APPLE, LINUX, FREE_BSD
    # Install extra files
    install(FILES pcm-bw-histogram.sh
            DESTINATION ${CMAKE_INSTALL_SBINDIR}
            RENAME pcm-bw-histogram
            PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ GROUP_EXECUTE GROUP_READ WORLD_EXECUTE WORLD_READ)
    file(GLOB OPCODE_FILES "opCode*.txt")
    foreach(opcode_file ${OPCODE_FILES})
        install(FILES ${opcode_file} DESTINATION ${CMAKE_INSTALL_DATADIR}/pcm)
    endforeach()

    install(DIRECTORY "PMURegisterDeclarations" DESTINATION ${CMAKE_INSTALL_DATADIR}/pcm)

    # Install docs
    install(FILES ${CMAKE_SOURCE_DIR}/LICENSE DESTINATION ${CMAKE_INSTALL_DATADIR}/licenses/pcm)
    install(FILES ${CMAKE_SOURCE_DIR}/README.md DESTINATION ${CMAKE_INSTALL_DOCDIR})

    file(GLOB DOC_FILES  ${CMAKE_SOURCE_DIR}/doc/*.txt  ${CMAKE_SOURCE_DIR}/doc/*.md)
    foreach(doc_file ${DOC_FILES})
        get_filename_component(doc_file_name ${doc_file} NAME)
        configure_file(${doc_file} ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/${doc_file_name} COPYONLY)
        install(FILES ${doc_file} DESTINATION ${CMAKE_INSTALL_DOCDIR})
    endforeach()
endif(UNIX)

# Library install
include(CMakePackageConfigHelpers)

add_library(pcm::pcm-lib ALIAS pcm-lib)
add_library(pcm::pcm-static ALIAS pcm-static)
add_library(pcm::pcm-static-silent ALIAS pcm-static-silent)
install(
    TARGETS
        pcm-core-flags
        pcm-headers
        pcm-lib
        pcm-static
        pcm-static-silent
        pcm-public-flags
        pcm-private-flags
        pcm-hardening-flags
        pcm-pugixml
        pcm-simdjson
    EXPORT pcmTargets
    RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
        COMPONENT lib
    LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
        COMPONENT lib
        NAMELINK_COMPONENT dev
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
        COMPONENT dev
    FILE_SET HEADERS DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
        COMPONENT dev)

# Install the target CMake definitions
install(EXPORT pcmTargets FILE pcmTargets.cmake
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/pcm"
        COMPONENT ${COMP}
        NAMESPACE pcm::)
# Add all targets to the build tree export set
export(EXPORT pcmTargets FILE "${PROJECT_BINARY_DIR}/pcmTargets.cmake"
       NAMESPACE pcm::)
# Generate the config file that includes the exports
configure_package_config_file("${CMAKE_CURRENT_SOURCE_DIR}/cmake/pcmConfig.cmake.in"
                              "${PROJECT_BINARY_DIR}/pcmConfig.cmake"
    INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/pcm"
    NO_SET_AND_CHECK_MACRO)
write_basic_package_version_file("${PROJECT_BINARY_DIR}/pcmConfigVersion.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMinorVersion)
# Install the pcmConfig.cmake and pcmConfigVersion.cmake
install(FILES "${PROJECT_BINARY_DIR}/pcmConfig.cmake"
              "${PROJECT_BINARY_DIR}/pcmConfigVersion.cmake"
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/pcm"
        COMPONENT ${COMP})
