file(REMOVE_RECURSE
  "lib/libe1_decode_lib.a"
  "lib/libe1_decode_lib.pdb"
)

# Per-language clean rules from dependency scanning.
foreach(lang CXX)
  include(CMakeFiles/e1_decode_lib.dir/cmake_clean_${lang}.cmake OPTIONAL)
endforeach()
