#include <fast_float/fast_float.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <limits>
#include <cstdlib>

template<class T> uint64_t bits(T x) { uint64_t b=0; std::memcpy(&b,&x,sizeof x); return b; }
template<class C,class T> void check(const std::string &s,uint64_t b,std::errc ec={}) {
  std::basic_string<C> w(s.begin(),s.end()); T x=T(42);
  auto r=fast_float::from_chars(w.data(),w.data()+w.size(),x);
  if(bits(x)!=b||r.ec!=ec||r.ptr!=w.data()+w.size()) std::abort();
}
template<class C> void run() {
  check<C,double>("7539960883769189760e-1",0x43a4ed76e5237b08ULL);
  check<C,double>("9007199254740995e-1",0x430999999999999cULL);
  check<C,double>("2142139806994845388e290",0x7ff0000000000000ULL,std::errc::result_out_of_range);
  check<C,double>("-2142139806994845388e290",0xfff0000000000000ULL,std::errc::result_out_of_range);
  check<C,float>("3.5e38",0x7f800000,std::errc::result_out_of_range);
  check<C,double>("1.0000000000000000000000000000000000000001",0x3ff0000000000000ULL);
  // Exact midpoint, then a nonzero digit beyond the bigint digit limit.
  std::string midpoint="1.00000000000000011102230246251565404236316680908203125";
  check<C,double>(midpoint,0x3ff0000000000000ULL);
  check<C,double>(midpoint+std::string(3000,'0')+"1",0x3ff0000000000001ULL);
  check<C,double>(midpoint+std::string(3000,'0'),0x3ff0000000000000ULL);
  check<C,double>("-0e999999999999999999999999",0x8000000000000000ULL);
  check<C,float>("1e-99999999999999999999",0,std::errc::result_out_of_range);
}
int main(){run<char>();run<char16_t>();run<char32_t>();
 if(bits(fast_float::integer_times_pow10<double>(uint64_t(9007199254740995ULL),-1))!=0x430999999999999cULL) return 1;
 if(bits(fast_float::integer_times_pow10<double>(int64_t(-2142139806994845388LL),290))!=0xfff0000000000000ULL) return 1;
}
