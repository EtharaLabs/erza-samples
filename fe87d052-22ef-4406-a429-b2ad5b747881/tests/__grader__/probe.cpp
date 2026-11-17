// The verifier's probe driver. Reads lines "<kind> <text>" on stdin and writes, for each, one
// record "<kind> <hex bits> <errc> <ptr offset>" to file descriptor 3, so nothing the library
// under test prints on stdout or stderr can reach a record. The value starts at a fixed
// sentinel, so a call that leaves it unmodified is visible in the bits.
//   f, d   from_chars on char input, float or double
//   a, b   from_chars on char16_t input, float or double
//   p, q   from_chars on char32_t input, float or double
//   j, i   integer_times_pow10 for float or double; text is "<mantissa> <decimal exponent>",
//          a mantissa with a leading '-' calls the int64_t overload, otherwise the uint64_t one;
//          errc and ptr are written as 0
#include "fast_float/fast_float.h"

#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <system_error>

namespace {

template <typename T> void put_bits(std::FILE *out, char kind, T value, int ec, long ptr) {
  if (sizeof(T) == 8) {
    std::uint64_t bits;
    std::memcpy(&bits, &value, sizeof bits);
    std::fprintf(out, "%c %016" PRIx64 " %d %ld\n", kind, bits, ec, ptr);
  } else {
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof bits);
    std::fprintf(out, "%c %08" PRIx32 " %d %ld\n", kind, bits, ec, ptr);
  }
}

template <typename T, typename UC> void parse(std::FILE *out, char kind, const std::string &text) {
  std::basic_string<UC> wide(text.begin(), text.end());
  const UC *first = wide.data();
  T value = T(-12345.0);
  fast_float::from_chars_result_t<UC> r = fast_float::from_chars(first, first + wide.size(), value);
  put_bits(out, kind, value, static_cast<int>(r.ec), static_cast<long>(r.ptr - first));
}

template <typename T> bool scale(std::FILE *out, char kind, const std::string &text) {
  const std::size_t space = text.find(' ');
  if (space == std::string::npos) {
    return false;
  }
  const std::string mantissa = text.substr(0, space);
  const int exponent = std::atoi(text.c_str() + space + 1);
  T value;
  if (!mantissa.empty() && mantissa[0] == '-') {
    value = fast_float::integer_times_pow10<T>(static_cast<std::int64_t>(std::strtoll(mantissa.c_str(), nullptr, 10)), exponent);
  } else {
    value = fast_float::integer_times_pow10<T>(static_cast<std::uint64_t>(std::strtoull(mantissa.c_str(), nullptr, 10)), exponent);
  }
  put_bits(out, kind, value, 0, 0);
  return true;
}

}  // namespace

int main() {
  std::FILE *out = fdopen(3, "w");
  if (out == nullptr) {
    return 2;
  }
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.size() < 2 || line[1] != ' ') {
      return 3;
    }
    const char kind = line[0];
    const std::string text = line.substr(2);
    switch (kind) {
      case 'f': parse<float, char>(out, kind, text); break;
      case 'd': parse<double, char>(out, kind, text); break;
      case 'a': parse<float, char16_t>(out, kind, text); break;
      case 'b': parse<double, char16_t>(out, kind, text); break;
      case 'p': parse<float, char32_t>(out, kind, text); break;
      case 'q': parse<double, char32_t>(out, kind, text); break;
      case 'j': if (!scale<float>(out, kind, text)) return 3; break;
      case 'i': if (!scale<double>(out, kind, text)) return 3; break;
      default: return 3;
    }
  }
  return std::fclose(out) == 0 ? 0 : 4;
}
