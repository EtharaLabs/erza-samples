// Cost meter: loads "<kind> <text>" lines (the probe's kinds), then converts them all inside
// convert_all(), the only function callgrind counts.
#include "fast_float/fast_float.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
struct Item { char kind; std::string text; std::u16string w16; std::u32string w32; std::uint64_t m; std::int64_t sm; int e; bool neg; };
template <typename T> std::uint64_t bits(T v) { std::uint64_t b = 0; std::memcpy(&b, &v, sizeof v); return b; }
template <typename T, typename UC> std::uint64_t one(const UC *f, std::size_t n) { T v = T(0); auto r = fast_float::from_chars(f, f + n, v); return bits(v) * 3 + std::uint64_t(r.ec); }
__attribute__((noinline)) std::uint64_t convert_all(const std::vector<Item> &items) {
  std::uint64_t acc = 0;
  for (const Item &it : items) {
    std::uint64_t x = 0;
    switch (it.kind) {
      case 'f': x = one<float>(it.text.data(), it.text.size()); break;
      case 'd': x = one<double>(it.text.data(), it.text.size()); break;
      case 'a': x = one<float>(it.w16.data(), it.w16.size()); break;
      case 'b': x = one<double>(it.w16.data(), it.w16.size()); break;
      case 'p': x = one<float>(it.w32.data(), it.w32.size()); break;
      case 'q': x = one<double>(it.w32.data(), it.w32.size()); break;
      case 'j': x = it.neg ? bits(fast_float::integer_times_pow10<float>(it.sm, it.e)) : bits(fast_float::integer_times_pow10<float>(it.m, it.e)); break;
      case 'i': x = it.neg ? bits(fast_float::integer_times_pow10<double>(it.sm, it.e)) : bits(fast_float::integer_times_pow10<double>(it.m, it.e)); break;
    }
    acc = acc * 1000003 + x;
  }
  return acc;
}
int main() {
  std::vector<Item> items; std::string line;
  while (std::getline(std::cin, line)) {
    if (line.size() < 2) continue;
    Item it{line[0], line.substr(2), {}, {}, 0, 0, 0, false};
    it.w16.assign(it.text.begin(), it.text.end()); it.w32.assign(it.text.begin(), it.text.end());
    if (it.kind == 'i' || it.kind == 'j') {
      std::size_t sp = it.text.find(' '); std::string m = it.text.substr(0, sp); it.e = std::atoi(it.text.c_str() + sp + 1);
      it.neg = !m.empty() && m[0] == '-'; it.sm = std::strtoll(m.c_str(), nullptr, 10); it.m = std::strtoull(m.c_str(), nullptr, 10);
    }
    items.push_back(it);
  }
  std::printf("%016llx\n", (unsigned long long)convert_all(items));
}
