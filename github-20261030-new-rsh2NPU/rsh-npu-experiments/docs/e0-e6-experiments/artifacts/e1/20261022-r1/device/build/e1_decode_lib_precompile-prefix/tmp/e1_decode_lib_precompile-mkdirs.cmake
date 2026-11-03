# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/usr/local/Ascend/cann-9.0.0/tools/tikcpp/ascendc_kernel_cmake/legacy_modules/device_precompile_project"
  "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/src/e1_decode_lib_precompile-build"
  "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix"
  "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/tmp"
  "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/src/e1_decode_lib_precompile-stamp"
  "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/src"
  "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/src/e1_decode_lib_precompile-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/src/e1_decode_lib_precompile-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/data/e1-20261022-r1/build/e1_decode_lib_precompile-prefix/src/e1_decode_lib_precompile-stamp${cfgdir}") # cfgdir has leading slash
endif()
