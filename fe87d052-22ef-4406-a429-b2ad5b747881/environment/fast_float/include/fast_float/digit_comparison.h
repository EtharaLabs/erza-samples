#ifndef FASTFLOAT_DIGIT_COMPARISON_H
#define FASTFLOAT_DIGIT_COMPARISON_H

#include <cstdint>
#include <cstring>
#include <iterator>

#include "float_common.h"
#include "bigint.h"
#include "ascii_number.h"

namespace fast_float {

constexpr static uint64_t pow10_u64[] = {1UL,
                                                    10UL,
                                                    100UL,
                                                    1000UL,
                                                    10000UL,
                                                    100000UL,
                                                    1000000UL,
                                                    10000000UL,
                                                    100000000UL,
                                                    1000000000UL,
                                                    10000000000UL,
                                                    100000000000UL,
                                                    1000000000000UL,
                                                    10000000000000UL,
                                                    100000000000000UL,
                                                    1000000000000000UL,
                                                    10000000000000000UL,
                                                    100000000000000000UL,
                                                    1000000000000000000UL,
                                                    10000000000000000000UL};

fastfloat_really_inline FASTFLOAT_CONSTEXPR14 int32_t
decimal_magnitude(uint64_t mantissa, int32_t exponent) noexcept {
  while (mantissa >= 10000) {
    mantissa /= 10000;
    exponent += 4;
  }
  while (mantissa >= 100) {
    mantissa /= 100;
    exponent += 2;
  }
  while (mantissa >= 10) {
    mantissa /= 10;
    exponent += 1;
  }
  return exponent;
}

template <typename T>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa
unpack_float(T value) noexcept {
  using equiv_uint = equiv_uint_t<T>;
  constexpr equiv_uint exponent_mask = binary_format<T>::exponent_mask();
  constexpr equiv_uint mantissa_mask = binary_format<T>::mantissa_mask();
  constexpr equiv_uint hidden_bit_mask = binary_format<T>::hidden_bit_mask();

  adjusted_mantissa am;
  int32_t bias = binary_format<T>::mantissa_explicit_bits() -
                 binary_format<T>::minimum_exponent();
  equiv_uint bits;
#if FASTFLOAT_HAS_BIT_CAST
  bits = std::bit_cast<equiv_uint>(value);
#else
  ::memcpy(&bits, &value, sizeof(T));
#endif
  if ((bits & exponent_mask) == 0) {

    am.power2 = 1 - bias;
    am.mantissa = bits & mantissa_mask;
  } else {

    am.power2 = int32_t((bits & exponent_mask) >>
                        binary_format<T>::mantissa_explicit_bits());
    am.power2 -= bias;
    am.mantissa = (bits & mantissa_mask) | hidden_bit_mask;
  }

  return am;
}

template <typename T>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa
midpoint_above(T value) noexcept {
  adjusted_mantissa am = unpack_float(value);
  am.mantissa <<= 1;
  am.mantissa += 1;
  am.power2 -= 1;
  return am;
}

template <typename T, typename callback>
fastfloat_really_inline FASTFLOAT_CONSTEXPR14 void round(adjusted_mantissa &am,
                                                         callback cb) noexcept {
  int32_t mantissa_shift = 64 - binary_format<T>::mantissa_explicit_bits() - 1;
  if (-am.power2 >= mantissa_shift) {

    int32_t shift = -am.power2 + 1;
    cb(am, (shift < 64 ? shift : 64));

    am.power2 = (am.mantissa <
                 (uint64_t(1) << binary_format<T>::mantissa_explicit_bits()))
                    ? 0
                    : 1;
    return;
  }

  cb(am, mantissa_shift);

  if (am.mantissa >=
      (uint64_t(2) << binary_format<T>::mantissa_explicit_bits())) {
    am.mantissa = (uint64_t(1) << binary_format<T>::mantissa_explicit_bits());
    am.power2++;
  }

  am.mantissa &= ~(uint64_t(1) << binary_format<T>::mantissa_explicit_bits());
  if (am.power2 >= binary_format<T>::infinite_power()) {
    am.power2 = binary_format<T>::infinite_power();
    am.mantissa = 0;
  }
}

template <typename callback>
fastfloat_really_inline FASTFLOAT_CONSTEXPR14 void
round_half_even(adjusted_mantissa &am, int32_t shift,
                       callback cb) noexcept {
  uint64_t const mask = (shift == 64) ? UINT64_MAX : (uint64_t(1) << shift) - 1;
  uint64_t const halfway = (shift == 0) ? 0 : uint64_t(1) << (shift - 1);
  uint64_t truncated_bits = am.mantissa & mask;
  bool is_above = truncated_bits > halfway;
  bool is_halfway = truncated_bits == halfway;

  if (shift == 64) {
    am.mantissa = 0;
  } else {
    am.mantissa >>= shift;
  }
  am.power2 += shift;

  bool is_odd = (am.mantissa & 1) == 1;
  am.mantissa += uint64_t(cb(is_odd, is_halfway, is_above));
}

fastfloat_really_inline FASTFLOAT_CONSTEXPR14 void
truncate_bits(adjusted_mantissa &am, int32_t shift) noexcept {
  if (shift == 64) {
    am.mantissa = 0;
  } else {
    am.mantissa >>= shift;
  }
  am.power2 += shift;
}

template <typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 void
skip_leading_zeros(UC const *&first, UC const *last) noexcept {
  uint64_t val;
  while (!cpp20_and_in_constexpr() &&
         std::distance(first, last) >= int_cmp_len<UC>()) {
    ::memcpy(&val, first, sizeof(uint64_t));
    if (val != int_cmp_zeros<UC>()) {
      break;
    }
    first += int_cmp_len<UC>();
  }
  while (first != last) {
    if (*first != UC('0')) {
      break;
    }
    first++;
  }
}

template <typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 bool
has_nonzero_digits(UC const *first, UC const *last) noexcept {

  uint64_t val;
  while (!cpp20_and_in_constexpr() &&
         std::distance(first, last) >= int_cmp_len<UC>()) {
    ::memcpy(&val, first, sizeof(uint64_t));
    if (val != int_cmp_zeros<UC>()) {
      return true;
    }
    first += int_cmp_len<UC>();
  }
  while (first != last) {
    if (*first != UC('0')) {
      return true;
    }
    ++first;
  }
  return false;
}

template <typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 bool
has_nonzero_digits(span<UC const> s) noexcept {
  return has_nonzero_digits(s.ptr, s.ptr + s.len());
}

template <typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR20 void
take_eight_digits(UC const *&p, limb &value, size_t &counter,
                   size_t &count) noexcept {
  value = value * 100000000 + parse_eight_digits_unrolled(p);
  p += 8;
  counter += 8;
  count += 8;
}

template <typename UC>
fastfloat_really_inline FASTFLOAT_CONSTEXPR14 void
take_digit(UC const *&p, limb &value, size_t &counter,
                size_t &count) noexcept {
  value = value * 10 + limb(*p - UC('0'));
  p++;
  counter++;
  count++;
}

fastfloat_really_inline FASTFLOAT_CONSTEXPR20 void
mul_add_limb(bigint &big, limb power, limb value) noexcept {
  big.mul(power);
  big.add(value);
}

fastfloat_really_inline FASTFLOAT_CONSTEXPR20 void
bump_last_digit(bigint &big, size_t &count) noexcept {

  mul_add_limb(big, 10, 1);
  count++;
}

template <typename UC>
inline FASTFLOAT_CONSTEXPR20 void
load_significand(bigint &result, parsed_number_string_t<UC> &num,
               size_t max_digits, size_t &digits) noexcept {

  size_t counter = 0;
  digits = 0;
  limb value = 0;
#ifdef FASTFLOAT_64BIT_LIMB
  size_t step = 19;
#else
  size_t step = 9;
#endif

  UC const *p = num.integer.ptr;
  UC const *pend = p + num.integer.len();
  skip_leading_zeros(p, pend);

  while (p != pend) {
    while ((std::distance(p, pend) >= 8) && (step - counter >= 8) &&
           (max_digits - digits >= 8)) {
      take_eight_digits(p, value, counter, digits);
    }
    while (counter < step && p != pend && digits < max_digits) {
      take_digit(p, value, counter, digits);
    }
    if (digits == max_digits) {

      mul_add_limb(result, limb(pow10_u64[counter]), value);
      bool truncated = has_nonzero_digits(p, pend);
      if (num.fraction.ptr != nullptr) {
        truncated |= has_nonzero_digits(num.fraction);
      }
      if (truncated) {
        bump_last_digit(result, digits);
      }
      return;
    } else {
      mul_add_limb(result, limb(pow10_u64[counter]), value);
      counter = 0;
      value = 0;
    }
  }

  if (num.fraction.ptr != nullptr) {
    p = num.fraction.ptr;
    pend = p + num.fraction.len();
    if (digits == 0) {
      skip_leading_zeros(p, pend);
    }

    while (p != pend) {
      while ((std::distance(p, pend) >= 8) && (step - counter >= 8) &&
             (max_digits - digits >= 8)) {
        take_eight_digits(p, value, counter, digits);
      }
      while (counter < step && p != pend && digits < max_digits) {
        take_digit(p, value, counter, digits);
      }
      if (digits == max_digits) {

        mul_add_limb(result, limb(pow10_u64[counter]), value);
        bool truncated = false;
        while (!truncated && p != pend) {
          UC const *chunk_end = pend - p > 8 ? p + 8 : pend;
          truncated = has_nonzero_digits(p, pend);
          p = chunk_end;
        }
        if (truncated) {
          bump_last_digit(result, digits);
        }
        return;
      } else {
        mul_add_limb(result, limb(pow10_u64[counter]), value);
        counter = 0;
        value = 0;
      }
    }
  }
}

template <typename T>
inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa
exact_compare_pos(bigint &bigmant, int32_t exponent) noexcept {
  FASTFLOAT_ASSERT(bigmant.pow10(uint32_t(exponent)));
  adjusted_mantissa answer;
  bool truncated;
  answer.mantissa = bigmant.hi64(truncated);
  int bias = binary_format<T>::mantissa_explicit_bits() -
             binary_format<T>::minimum_exponent();
  answer.power2 = bigmant.bit_length() - 64 + bias;

  round<T>(answer, [truncated](adjusted_mantissa &a, int32_t shift) {
    round_half_even(
        a, shift,
        [truncated](bool is_odd, bool is_halfway, bool is_above) -> bool {
          return is_above || (is_halfway && truncated) ||
                 (is_odd && is_halfway);
        });
  });

  return answer;
}

template <typename T>
inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa exact_compare_neg(
    bigint &bigmant, adjusted_mantissa am, int32_t exponent) noexcept {
  bigint &real_digits = bigmant;
  int32_t real_exp = exponent;

  adjusted_mantissa am_b = am;

  round<T>(am_b,
           [](adjusted_mantissa &a, int32_t shift) { truncate_bits(a, shift); });
  T b;
  to_float(false, am_b, b);
  adjusted_mantissa theor = midpoint_above(b);
  bigint theor_digits(theor.mantissa);
  int32_t theor_exp = theor.power2;

  int32_t pow2_exp = theor_exp - real_exp;
  uint32_t pow5_exp = uint32_t(-real_exp);
  if (pow5_exp != 0) {
    FASTFLOAT_ASSERT(theor_digits.pow5(pow5_exp));
  }
  if (pow2_exp > 0) {
    FASTFLOAT_ASSERT(theor_digits.pow2(uint32_t(pow2_exp)));
  } else if (pow2_exp < 0) {
    FASTFLOAT_ASSERT(real_digits.pow2(uint32_t(-pow2_exp)));
  }

  int ord = real_digits.compare(theor_digits);
  adjusted_mantissa answer = am;
  round<T>(answer, [ord](adjusted_mantissa &a, int32_t shift) {
    round_half_even(
        a, shift, [ord](bool is_odd, bool _, bool __) -> bool {
          static_cast<void>(_);
          static_cast<void>(__);
          if (ord > 0) {
            return true;
          } else if (ord < 0) {
            return false;
          } else {
            return is_odd;
          }
        });
  });

  return answer;
}

template <typename T, typename UC>
inline FASTFLOAT_CONSTEXPR20 adjusted_mantissa
exact_compare(parsed_number_string_t<UC> &num, adjusted_mantissa am) noexcept {

  am.power2 -= unresolved_bias;

  int32_t sci_exp =
      decimal_magnitude(num.mantissa, static_cast<int32_t>(num.exponent));
  size_t max_digits = binary_format<T>::max_digits();
  size_t digits = 0;
  bigint bigmant;
  load_significand(bigmant, num, max_digits, digits);

  int32_t exponent = sci_exp + 1 - int32_t(digits);
  if (exponent >= 0) {
    return exact_compare_pos<T>(bigmant, exponent);
  } else {
    return exact_compare_neg<T>(bigmant, am, exponent);
  }
}

}

#endif
