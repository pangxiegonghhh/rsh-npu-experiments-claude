# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/usr/local/Ascend/cann-9.0.0/tools/tikcpp/ascendc_kernel_cmake/legacy_modules/host_project"
  "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/src/e1_decode_lib_host-build"
  "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix"
  "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/tmp"
  "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/src/e1_decode_lib_host-stamp"
  "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/src"
  "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/src/e1_decode_lib_host-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/src/e1_decode_lib_host-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/data/e1-20261022-r1/build/e1_decode_lib_host-prefix/src/e1_decode_lib_host-stamp${cfgdir}") # cfgdir has leading slash
endif()
