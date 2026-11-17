#ifndef FASTFLOAT_PARSE_NUMBER_H
#define FASTFLOAT_PARSE_NUMBER_H

#include "ascii_number.h"
#include "decimal_to_binary.h"
#include "digit_comparison.h"
#include "float_common.h"

#include <cmath>
#include <cstring>
#include <limits>
#include <system_error>

namespace fast_float {

namespace detail {

template <typename T, typename UC>
from_chars_result_t<UC>
    FASTFLOAT_CONSTEXPR14 parse_infnan(UC const *first, UC const *last,
                                       T &value, chars_format fmt) noexcept {
  from_chars_result_t<UC> answer{};
  answer.ptr = first;
  answer.ec = std::errc();

  bool const minusSign = (*first == UC('-'));

  if ((*first == UC('-')) ||
      (uint64_t(fmt & chars_format::allow_leading_plus) &&
       (*first == UC('+')))) {
    ++first;
  }
  if (last - first >= 3) {
    if (fastfloat_strncasecmp(first, str_const_nan<UC>(), 3)) {
      answer.ptr = (first += 3);
      value = minusSign ? -std::numeric_limits<T>::quiet_NaN()
                        : std::numeric_limits<T>::quiet_NaN();

      if (first != last && *first == UC('(')) {
        for (UC const *ptr = first + 1; ptr != last; ++ptr) {
          if (*ptr == UC(')')) {
            answer.ptr = ptr + 1;
            break;
          } else if (!((UC('a') <= *ptr && *ptr <= UC('z')) ||
                       (UC('A') <= *ptr && *ptr <= UC('Z')) ||
                       (UC('0') <= *ptr && *ptr <= UC('9')) || *ptr == UC('_')))
            break;
        }
      }
      return answer;
    }
    if (fastfloat_strncasecmp(first, str_const_inf<UC>(), 3)) {
      if ((last - first >= 8) &&
          fastfloat_strncasecmp(first + 3, str_const_inf<UC>() + 3, 5)) {
        answer.ptr = first + 8;
      } else {
        answer.ptr = first + 3;
      }
      value = minusSign ? -std::numeric_limits<T>::infinity()
                        : std::numeric_limits<T>::infinity();
      return answer;
    }
  }
  answer.ec = std::errc::invalid_argument;
  return answer;
}

fastfloat_really_inline bool rounds_to_nearest() noexcept {

#if (FLT_EVAL_METHOD != 1) && (FLT_EVAL_METHOD != 0)
  return false;
#endif

  static float volatile fmin = (std::numeric_limits<float>::min)();
  float fmini = fmin;

#ifdef FASTFLOAT_VISUAL_STUDIO
#pragma warning(push)

#elif defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wfloat-equal"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wfloat-equal"
#endif
  return (fmini + 1.0f == 1.0f - fmini);
#ifdef FASTFLOAT_VISUAL_STUDIO
#pragma warning(pop)
#elif defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
}

}

template <typename T> struct from_chars_caller {
  template <typename UC>
  fastfloat_clang_really_inline
      FASTFLOAT_CONSTEXPR20 static from_chars_result_t<UC>
      call(UC const *first, UC const *last, T &value,
           parse_options_t<UC> options) noexcept {
    return from_chars_advanced(first, last, value, options);
  }
};

#ifdef __STDCPP_FLOAT32_T__
template <> struct from_chars_caller<std::float32_t> {
  template <typename UC>
  FASTFLOAT_CONSTEXPR20 static from_chars_result_t<UC>
  call(UC const *first, UC const *last, std::float32_t &value,
       parse_options_t<UC> options) noexcept {

    float val = 0.0f;
    auto ret = from_chars_advanced(first, last, val, options);

    if (ret.ec != std::errc::invalid_argument) {
      value = val;
    }
    return ret;
  }
};
#endif

#ifdef __STDCPP_FLOAT64_T__
template <> struct from_chars_caller<std::float64_t> {
  template <typename UC>
  FASTFLOAT_CONSTEXPR20 static from_chars_result_t<UC>
  call(UC const *first, UC const *last, std::float64_t &value,
       parse_options_t<UC> options) noexcept {

    double val = 0.0;
    auto ret = from_chars_advanced(first, last, val, options);

    if (ret.ec != std::errc::invalid_argument) {
      value = val;
    }
    return ret;
  }
};
#endif

#ifdef __clang__

template <typename T, typename UC, chars_format Fmt>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_fixed_format(UC const *first, UC const *last, T &value) noexcept {
  return from_chars_caller<T>::call(first, last, value,
                                    parse_options_t<UC>(Fmt));
}
#endif

template <typename T, typename UC, typename>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars(UC const *first, UC const *last, T &value,
           chars_format fmt ) noexcept {
#ifdef __clang__
  if (fmt == chars_format::general) {
    return from_chars_fixed_format<T, UC, chars_format::general>(first, last,
                                                                 value);
  }
#endif
  return from_chars_caller<T>::call(first, last, value,
                                    parse_options_t<UC>(fmt));
}

template <typename T>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 bool
exact_small_product(uint64_t mantissa, int64_t exponent, bool is_negative,
                       T &value) noexcept {

  if (binary_format<T>::min_exponent_fast_path() <= exponent &&
      exponent <= binary_format<T>::max_exponent_fast_path() &&
      mantissa <= binary_format<T>::max_mantissa_fast_path()) {

    if (!cpp20_and_in_constexpr() && detail::rounds_to_nearest()) {

      value = T(mantissa);
      if (exponent < 0) {
        value = value / binary_format<T>::exact_power_of_ten(-exponent);
      } else {
        value = value * binary_format<T>::exact_power_of_ten(exponent);

        if (binary_format<T>::fast_path_can_overflow() &&
            value > (std::numeric_limits<T>::max)()) {
          return false;
        }
      }
      if (is_negative) {
        value = -value;
      }
      return true;
    } else {

      if (exponent >= 0 &&
          mantissa <= binary_format<T>::max_mantissa_fast_path(exponent)) {
#if defined(__clang__) || defined(FASTFLOAT_32BIT)

        if (mantissa == 0) {
          value = is_negative ? T(-0.) : T(0.);
          return true;
        }
#endif
        value = T(mantissa) * binary_format<T>::exact_power_of_ten(exponent);
        if (is_negative) {
          value = -value;
        }
        return true;
      }
    }
  }
  return false;
}

template <typename T, typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_advanced(parsed_number_string_t<UC> &pns, T &value) noexcept {
  static_assert(is_supported_float_type<T>::value,
                "only some floating-point types are supported");
  static_assert(is_supported_char_type<UC>::value,
                "only char, wchar_t, char16_t and char32_t are supported");

  from_chars_result_t<UC> answer;

  answer.ec = std::errc();
  answer.ptr = pns.lastmatch;

  if (!pns.too_many_digits &&
      exact_small_product(pns.mantissa, pns.exponent, pns.negative, value))
    return answer;

  adjusted_mantissa am =
      nearest_binary<binary_format<T>>(pns.exponent, pns.mantissa);
  if (pns.too_many_digits && am.power2 >= 0 &&
      pns.exponent >= binary_format<T>::smallest_power_of_ten() &&
      pns.exponent <= binary_format<T>::largest_power_of_ten()) {
    if (am != nearest_binary<binary_format<T>>(pns.exponent, pns.mantissa + 1)) {
      am = scaled_binary<binary_format<T>>(pns.exponent, pns.mantissa);
    }
  }

  if (am.power2 < 0) {
    am = exact_compare<T>(pns, am);
  }
  to_float(pns.negative, am, value);

  if ((pns.mantissa != 0 && am.mantissa == 0 && am.power2 == 0) ||
      am.power2 == binary_format<T>::infinite_power()) {
    answer.ec = std::errc::result_out_of_range;
  }
  return answer;
}

template <typename T, typename UC>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
reparse_with_spans(UC const *first, UC const *last, T &value,
                       parse_options_t<UC> options, bool bjf) noexcept {
  parsed_number_string_t<UC> pns =
      bjf ? parse_number_string_impl<true, false, UC>(first, last, options,
                                                      true)
          : parse_number_string_impl<false, false, UC>(first, last, options,
                                                       true);
  return from_chars_advanced(pns, value);
}

template <typename T, typename UC>
fastfloat_never_inline FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_float_javascript(UC const *first, UC const *last, T &value,
                            parse_options_t<UC> options) noexcept {
  chars_format const fmt = detail::adjust_for_feature_macros(options.format);
  if (uint64_t(fmt & chars_format::skip_white_space)) {
    while ((first != last) && fast_float::is_space(*first)) {
      first++;
    }
  }
  from_chars_result_t<UC> answer;
  answer.ec = std::errc::invalid_argument;
  answer.ptr = first;
  if (first == last) {
    return answer;
  }
  parsed_number_string_t<UC> pns =
      parse_number_string_javascript<UC>(first, last, options, true);
  if (!pns.valid) {
    if (uint64_t(fmt & chars_format::no_infnan)) {
      return answer;
    }
    return detail::parse_infnan(first, last, value, fmt);
  }
  return from_chars_advanced(pns, value);
}

template <typename T, typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_float_advanced(UC const *first, UC const *last, T &value,
                          parse_options_t<UC> options) noexcept {

  static_assert(is_supported_float_type<T>::value,
                "only some floating-point types are supported");
  static_assert(is_supported_char_type<UC>::value,
                "only char, wchar_t, char16_t and char32_t are supported");

  chars_format const fmt = detail::adjust_for_feature_macros(options.format);

#ifdef __clang__
#pragma clang diagnostic push
#if (!defined(__APPLE_CC__) && __clang_major__ >= 10) || (__clang_major__ >= 13)
#pragma clang diagnostic ignored "-Wc++20-extensions"
#endif
#endif
  if fastfloat_unlikely (uint64_t(fmt & detail::basic_javascript_fmt)) {
    return from_chars_float_javascript<T, UC>(first, last, value, options);
  }
#ifdef __clang__
#pragma clang diagnostic pop
#endif

  from_chars_result_t<UC> answer;
  if (uint64_t(fmt & chars_format::skip_white_space)) {
    while ((first != last) && fast_float::is_space(*first)) {
      first++;
    }
  }
  if (first == last) {
    answer.ec = std::errc::invalid_argument;
    answer.ptr = first;
    return answer;
  }
  bool const bjf = uint64_t(fmt & detail::basic_json_fmt) != 0;

  parsed_number_string_t<UC> pns =
      bjf ? parse_number_string_impl<true, false, UC>(first, last, options,
                                                      false)
          : parse_number_string_impl<false, false, UC>(first, last, options,
                                                       false);
  if (!pns.valid) {
    if (uint64_t(fmt & chars_format::no_infnan)) {
      answer.ec = std::errc::invalid_argument;
      answer.ptr = first;
      return answer;
    } else {
      return detail::parse_infnan(first, last, value, fmt);
    }
  }

#ifdef __clang__
#pragma clang diagnostic push
#if (!defined(__APPLE_CC__) && __clang_major__ >= 10) || (__clang_major__ >= 13)
#pragma clang diagnostic ignored "-Wc++20-extensions"
#endif
#endif
  if fastfloat_unlikely (pns.too_many_digits) {
    return reparse_with_spans<T, UC>(first, last, value, options, bjf);
  }
  answer.ec = std::errc();
  answer.ptr = pns.lastmatch;

  if (exact_small_product(pns.mantissa, pns.exponent, pns.negative, value)) {
    return answer;
  }

  adjusted_mantissa am =
      nearest_binary<binary_format<T>>(pns.exponent, pns.mantissa);

  if fastfloat_unlikely (am.power2 < 0) {
    return reparse_with_spans<T, UC>(first, last, value, options, bjf);
  }
  to_float(pns.negative, am, value);

  if fastfloat_clang_unlikely ((pns.mantissa != 0 && am.mantissa == 0 &&
                                am.power2 == 0) ||
                               am.power2 ==
                                   binary_format<T>::infinite_power()) {
    answer.ec = std::errc::result_out_of_range;
  }
#ifdef __clang__
#pragma clang diagnostic pop
#endif
  return answer;
}

template <typename T, typename UC, typename>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars(UC const *first, UC const *last, T &value, int base) noexcept {

  static_assert(is_supported_integer_type<T>::value,
                "only integer types are supported");
  static_assert(is_supported_char_type<UC>::value,
                "only char, wchar_t, char16_t and char32_t are supported");

  parse_options_t<UC> options;
  options.base = base;
  return from_chars_advanced(first, last, value, options);
}

template <typename T>
FASTFLOAT_CONSTEXPR20
    typename std::enable_if<is_supported_float_type<T>::value, T>::type
    integer_times_pow10(uint64_t mantissa, int decimal_exponent) noexcept {
  T value;
  if (exact_small_product(mantissa, decimal_exponent, false, value))
    return value;

  adjusted_mantissa am =
      nearest_binary<binary_format<T>>(decimal_exponent, mantissa);
  if (am.power2 < 0) {
    bigint digits(mantissa);
    am.power2 -= unresolved_bias;
    am = decimal_exponent >= 0
             ? exact_compare_pos<T>(digits, decimal_exponent)
             : exact_compare_neg<T>(digits, am, decimal_exponent);
  }
  to_float(false, am, value);
  return value;
}

template <typename T>
FASTFLOAT_CONSTEXPR20
    typename std::enable_if<is_supported_float_type<T>::value, T>::type
    integer_times_pow10(int64_t mantissa, int decimal_exponent) noexcept {
  const bool is_negative = mantissa < 0;

  const uint64_t m = is_negative ? uint64_t(0) - static_cast<uint64_t>(mantissa)
                                 : static_cast<uint64_t>(mantissa);

  T value;
  if (exact_small_product(m, decimal_exponent, is_negative, value))
    return value;

  adjusted_mantissa am = nearest_binary<binary_format<T>>(decimal_exponent, m);
  if (am.power2 < 0) {
    bigint digits(m);
    am.power2 -= unresolved_bias;
    am = decimal_exponent >= 0
             ? exact_compare_pos<T>(digits, decimal_exponent)
             : exact_compare_neg<T>(digits, am, decimal_exponent);
  }
  to_float(is_negative, am, value);
  return value;
}

FASTFLOAT_CONSTEXPR20 inline double
integer_times_pow10(uint64_t mantissa, int decimal_exponent) noexcept {
  return integer_times_pow10<double>(mantissa, decimal_exponent);
}

FASTFLOAT_CONSTEXPR20 inline double
integer_times_pow10(int64_t mantissa, int decimal_exponent) noexcept {
  return integer_times_pow10<double>(mantissa, decimal_exponent);
}

template <typename T, typename Int>
FASTFLOAT_CONSTEXPR20 typename std::enable_if<
    is_supported_float_type<T>::value && std::is_integral<Int>::value &&
        sizeof(Int) <= sizeof(uint64_t) && !std::is_signed<Int>::value,
    T>::type
integer_times_pow10(Int mantissa, int decimal_exponent) noexcept {
  return integer_times_pow10<T>(static_cast<uint64_t>(mantissa),
                                decimal_exponent);
}

template <typename T, typename Int>
FASTFLOAT_CONSTEXPR20 typename std::enable_if<
    is_supported_float_type<T>::value && std::is_integral<Int>::value &&
        sizeof(Int) <= sizeof(int64_t) && std::is_signed<Int>::value,
    T>::type
integer_times_pow10(Int mantissa, int decimal_exponent) noexcept {
  return integer_times_pow10<T>(static_cast<int64_t>(mantissa),
                                decimal_exponent);
}

template <typename Int>
FASTFLOAT_CONSTEXPR20
    typename std::enable_if<std::is_integral<Int>::value &&
                                sizeof(Int) <= sizeof(uint64_t) &&
                                !std::is_signed<Int>::value,
                            double>::type
    integer_times_pow10(Int mantissa, int decimal_exponent) noexcept {
  return integer_times_pow10(static_cast<uint64_t>(mantissa), decimal_exponent);
}

template <typename Int>
FASTFLOAT_CONSTEXPR20
    typename std::enable_if<std::is_integral<Int>::value &&
                                sizeof(Int) <= sizeof(int64_t) &&
                                std::is_signed<Int>::value,
                            double>::type
    integer_times_pow10(Int mantissa, int decimal_exponent) noexcept {
  return integer_times_pow10(static_cast<int64_t>(mantissa), decimal_exponent);
}

template <typename T, typename UC>
FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_int_advanced(UC const *first, UC const *last, T &value,
                        parse_options_t<UC> options) noexcept {

  static_assert(is_supported_integer_type<T>::value,
                "only integer types are supported");
  static_assert(is_supported_char_type<UC>::value,
                "only char, wchar_t, char16_t and char32_t are supported");

  chars_format const fmt = detail::adjust_for_feature_macros(options.format);
  int const base = options.base;

  from_chars_result_t<UC> answer;
  if (uint64_t(fmt & chars_format::skip_white_space)) {
    while ((first != last) && fast_float::is_space(*first)) {
      first++;
    }
  }
  if (first == last || base < 2 || base > 36) {
    answer.ec = std::errc::invalid_argument;
    answer.ptr = first;
    return answer;
  }

  return parse_int_string(first, last, value, options);
}

template <size_t TypeIx> struct from_chars_advanced_caller {
  static_assert(TypeIx > 0, "unsupported type");
};

template <> struct from_chars_advanced_caller<1> {
  template <typename T, typename UC>
  fastfloat_really_inline FASTFLOAT_CONSTEXPR20 static from_chars_result_t<UC>
  call(UC const *first, UC const *last, T &value,
       parse_options_t<UC> options) noexcept {
    return from_chars_float_advanced(first, last, value, options);
  }
};

template <> struct from_chars_advanced_caller<2> {
  template <typename T, typename UC>
  fastfloat_really_inline FASTFLOAT_CONSTEXPR20 static from_chars_result_t<UC>
  call(UC const *first, UC const *last, T &value,
       parse_options_t<UC> options) noexcept {
    return from_chars_int_advanced(first, last, value, options);
  }
};

template <typename T, typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 from_chars_result_t<UC>
from_chars_advanced(UC const *first, UC const *last, T &value,
                    parse_options_t<UC> options) noexcept {
  return from_chars_advanced_caller<
      size_t(is_supported_float_type<T>::value) +
      2 * size_t(is_supported_integer_type<T>::value)>::call(first, last, value,
                                                             options);
}

}

#endif
