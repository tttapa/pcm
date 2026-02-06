import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps


class PCMRecipe(ConanFile):
    name = "intel-pcm"
    version = "0000"
    package_type = "library"

    license = "BSD-3-Clause"
    url = "https://github.com/intel/pcm"
    description = "Intel® Performance Counter Monitor (Intel® PCM)"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_executables": [True, False],
        "with_pugixml": [True, False],
        "with_simdjson": [True, False],
        "with_openssl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_executables": False,
        "with_pugixml": True,
        "with_simdjson": True,
        "with_openssl": True,
    }

    exports_sources = (
        "CMakeLists.txt",
        "examples/*",
        "perfmon/*",
        "src/*",
        "tests/*",
        "LICENSE",
        "README.md",
    )

    def config_options(self):
        if self.settings.get_safe("os") == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        if self.options.with_pugixml:
            self.requires("pugixml/1.15")
        if self.options.with_simdjson:
            self.requires("simdjson/4.2.4")
        if self.options.with_openssl:
            self.requires("openssl/3.6.1")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.26 <5]")
        self.test_requires("gtest/1.17.0")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["PCM_BUILD_EXECUTABLES"] = self.options.with_executables
        tc.variables["PCM_VENDOR_PUGIXML"] = False
        tc.variables["PCM_WITH_PUGIXML"] = self.options.with_pugixml
        tc.variables["PCM_VENDOR_SIMDJSON"] = False
        tc.variables["PCM_WITH_SIMDJSON"] = self.options.with_simdjson
        tc.variables["PCM_WITH_OPENSSL"] = self.options.with_openssl
        tc.variables["PCM_VENDOR_GTEST"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake", "pcm"))
