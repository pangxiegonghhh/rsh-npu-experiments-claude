file(REMOVE_RECURSE
  "lib/libe2_kernel.a"
  "lib/libe2_kernel.pdb"
)

# Per-language clean rules from dependency scanning.
foreach(lang CXX)
  include(CMakeFiles/e2_kernel.dir/cmake_clean_${lang}.cmake OPTIONAL)
endforeach()
