# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/usr/local/Ascend/cann-9.0.0/tools/tikcpp/ascendc_kernel_cmake/legacy_modules/device_precompile_project"
  "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/src/e2_kernel_precompile-build"
  "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix"
  "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/tmp"
  "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/src/e2_kernel_precompile-stamp"
  "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/src"
  "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/src/e2_kernel_precompile-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/src/e2_kernel_precompile-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/data/e2-20261022-r1/build/e2_kernel_precompile-prefix/src/e2_kernel_precompile-stamp${cfgdir}") # cfgdir has leading slash
endif()
