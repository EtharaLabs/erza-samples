# Builds the upstream tests kept in this copy. Each test is one translation unit with its own
# main() and reads no data file, so the build needs no network.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
foreach(TEST_NAME rcppfastfloat_test wide_char_test supported_chars_test example_test example_comma_test example_integer_times_pow10 p2497 fast_int json_fmt javascript_fmt fortran)
  add_executable(${TEST_NAME} ${TEST_NAME}.cpp)
  target_link_libraries(${TEST_NAME} PUBLIC fast_float)
  add_test(NAME ${TEST_NAME} COMMAND ${TEST_NAME})
endforeach()
