add_library(ascendc_runtime_obj OBJECT IMPORTED)
set_target_properties(ascendc_runtime_obj PROPERTIES
    IMPORTED_OBJECTS "/data/e2-20261022-r1/build/ascendc_runtime.cpp.o;/data/e2-20261022-r1/build/aicpu_rt.cpp.o;/data/e2-20261022-r1/build/ascendc_elf_tool.c.o"
)
