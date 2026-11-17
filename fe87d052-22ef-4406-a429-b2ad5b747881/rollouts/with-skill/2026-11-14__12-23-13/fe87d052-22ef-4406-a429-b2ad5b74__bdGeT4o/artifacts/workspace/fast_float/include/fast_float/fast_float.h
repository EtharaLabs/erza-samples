
#ifndef FASTFLOAT_FAST_FLOAT_H
#define FASTFLOAT_FAST_FLOAT_H

#include "float_common.h"

namespace fast_float {

template <typename T, typename UC = char,
          typename = FASTFLOAT_ENABLE_IF(is_supported_float_type<T>::value)>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars(UC const *first, UC const *last, T &value,
           chars_format fmt = chars_format::general) noexcept;

template <typename T, typename UC = char>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_advanced(UC const *first, UC const *last, T &value,
                    parse_options_t<UC> options) noexcept;

FASTFLOAT_CONSTEXPR20 inline double
integer_times_pow10(uint64_t mantissa, int decimal_exponent) noexcept;
FASTFLOAT_CONSTEXPR20 inline double
integer_times_pow10(int64_t mantissa, int decimal_exponent) noexcept;

template <typename T>
FASTFLOAT_CONSTEXPR20
    typename std::enable_if<is_supported_float_type<T>::value, T>::type
    integer_times_pow10(uint64_t mantissa, int decimal_exponent) noexcept;
template <typename T>
FASTFLOAT_CONSTEXPR20
    typename std::enable_if<is_supported_float_type<T>::value, T>::type
    integer_times_pow10(int64_t mantissa, int decimal_exponent) noexcept;

template <typename T, typename UC = char,
          typename = FASTFLOAT_ENABLE_IF(is_supported_integer_type<T>::value)>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars(UC const *first, UC const *last, T &value, int base = 10) noexcept;

}

#include "parse_number.h"
#endif
