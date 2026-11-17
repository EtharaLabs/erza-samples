#ifndef FASTFLOAT_DECIMAL_TO_BINARY_H
#define FASTFLOAT_DECIMAL_TO_BINARY_H

#include "float_common.h"
#include "fast_table.h"
#include <cfloat>
#include <cinttypes>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>

namespace fast_float {

template <int bit_precision>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 value128
pow5_product(int64_t q, uint64_t w) {
  int const index = 2 * int(q - powers::smallest_power_of_five);

  value128 firstproduct =
      full_multiplication(w, powers::power_of_five_128[index]);
  static_assert((bit_precision >= 0) && (bit_precision <= 64),
                " precision should  be in (0,64]");
  constexpr uint64_t precision_mask =
      (bit_precision < 64) ? (uint64_t(0xFFFFFFFFFFFFFFFF) >> bit_precision)
                           : uint64_t(0xFFFFFFFFFFFFFFFF);
  if ((firstproduct.high & precision_mask) ==
      precision_mask) {

    value128 secondproduct =
        full_multiplication(w, powers::power_of_five_128[index + 1]);
    firstproduct.low += secondproduct.high;
    if (secondproduct.high > firstproduct.low) {
      firstproduct.high++;
    }
  }
  return firstproduct;
}

namespace detail {

constexpr fastfloat_really_inline int32_t power(int32_t q) noexcept {
  return (((152170 + 65536) * q + (2048 * 65536)) >> 16) - 2048 + 63;
}
}

template <typename binary>
fastfloat_really_inline FASTFLOAT_CONSTEXPR14 adjusted_mantissa
scaled_binary_shifted(int64_t q, uint64_t w, int lz) noexcept {
  int hilz = int(w >> 63) ^ 1;
  adjusted_mantissa answer;
  answer.mantissa = w << hilz;
  int bias = binary::mantissa_explicit_bits() - binary::minimum_exponent();
  answer.power2 = int32_t(detail::power(int32_t(q)) + bias - hilz - lz - 62 +
                          unresolved_bias);
  return answer;
}

template <typename binary>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa
scaled_binary(int64_t q, uint64_t w) noexcept {
  int lz = leading_zeroes(w);
  w <<= lz;
  value128 product =
      pow5_product<binary::mantissa_explicit_bits() + 3>(q, w);
  return scaled_binary_shifted<binary>(q, product.high, lz);
}

template <typename binary>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa
nearest_binary(int64_t q, uint64_t w) noexcept {
  adjusted_mantissa answer;
  if ((w == 0) || (q < binary::smallest_power_of_ten())) {
    answer.power2 = 0;
    answer.mantissa = 0;

    return answer;
  }
  if (q > binary::largest_power_of_ten()) {

    answer.power2 = binary::infinite_power();
    answer.mantissa = 0;
    return answer;
  }

  int lz = leading_zeroes(w);
  w <<= lz;

  value128 product =
      pow5_product<binary::mantissa_explicit_bits() + 3>(q, w);

  int upperbit = int(product.high >> 63);
  int shift = upperbit + 64 - binary::mantissa_explicit_bits() - 3;

  answer.mantissa = product.high >> shift;

  answer.power2 = int32_t(detail::power(int32_t(q)) + upperbit - lz -
                          binary::minimum_exponent());
  if (answer.power2 <= 0) {

    if (-answer.power2 + 1 >=
        64) {

      answer.power2 = 0;
      answer.mantissa = 0;

      return answer;
    }

    int const subnormal_shift = -answer.power2 + 1;
    answer.mantissa >>= subnormal_shift;

    if (binary::subnormal_ties_possible() && (product.low <= 1) &&
        (q >= binary::min_exponent_round_to_even()) &&
        (q <= binary::max_exponent_round_to_even()) &&
        ((answer.mantissa & 3) == 1)) {
      if (((answer.mantissa << subnormal_shift) << shift) == product.high) {
        answer.mantissa &= ~uint64_t(1);
      }
    }
    answer.mantissa += (answer.mantissa & 1);
    answer.mantissa >>= 1;

    answer.power2 =
        (answer.mantissa < (uint64_t(1) << binary::mantissa_explicit_bits()))
            ? 0
            : 1;
    return answer;
  }

  if ((product.low <= 1) && (q >= binary::min_exponent_round_to_even()) &&
      (q <= binary::max_exponent_round_to_even()) &&
      ((answer.mantissa & 1) == 1)) {

    if ((answer.mantissa << shift) == product.high) {
      answer.mantissa &= ~uint64_t(1);
    }
  }

  answer.mantissa += (answer.mantissa & 1);
  answer.mantissa >>= 1;

#ifdef __clang__
#pragma clang diagnostic push
#if (!defined(__APPLE_CC__) && __clang_major__ >= 10) || (__clang_major__ >= 13)
#pragma clang diagnostic ignored "-Wc++20-extensions"
#endif
#endif
  if fastfloat_clang_unlikely (answer.mantissa >=
                               (uint64_t(2)
                                << binary::mantissa_explicit_bits())) {
    answer.mantissa = (uint64_t(1) << binary::mantissa_explicit_bits());
    answer.power2++;
  }

  answer.mantissa &= ~(uint64_t(1) << binary::mantissa_explicit_bits());
  if fastfloat_clang_unlikely (answer.power2 > binary::infinite_power()) {

    answer.power2 = binary::infinite_power();
    answer.mantissa = 0;
  }
#ifdef __clang__
#pragma clang diagnostic pop
#endif
  return answer;
}

}

#endif
