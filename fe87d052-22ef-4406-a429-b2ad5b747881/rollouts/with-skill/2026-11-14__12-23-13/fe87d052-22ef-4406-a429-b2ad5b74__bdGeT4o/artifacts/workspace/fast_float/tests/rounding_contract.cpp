#include <fast_float/fast_float.h>
#include <cstring>
#include <string>
#include <cstdint>
#include <iostream>
int failures=0;
template<class T> uint64_t bits(T x) { uint64_t u=0; std::memcpy(&u,&x,sizeof x); return u; }
template<class C,class T> void check(const std::string &s,uint64_t expected,std::errc ec={}) {
 std::basic_string<C> text(s.begin(),s.end()); T v=T(42);
 auto r=fast_float::from_chars(text.data(),text.data()+text.size(),v);
 if(bits(v)!=expected || r.ec!=ec || r.ptr!=text.data()+text.size()) {++failures;}
}
template<class C> void run(){
 check<C,float>("16777219",0x4b800002);
 check<C,float>("216211103515625e-10",0x46a8ea38);
 check<C,float>("52428803125e-5",0x49000000);
 check<C,float>("4e38",0x7f800000,std::errc::result_out_of_range);
 check<C,double>("2e308",UINT64_C(0x7ff0000000000000),std::errc::result_out_of_range);
 check<C,double>("1.5"+std::string(100000,'0'),UINT64_C(0x3ff8000000000000));
 check<C,float>("1.000000059604644775390625"+std::string(100000,'0'),0x3f800000);
 check<C,float>("1.000000059604644775390625"+std::string(1000,'0')+"1",0x3f800001);
 check<C,double>("-0e9999999999999999999999999",UINT64_C(0x8000000000000000));
 check<C,double>("-1e-9999999999999999999999999",UINT64_C(0x8000000000000000),std::errc::result_out_of_range);
}
int main(){run<char>();run<char16_t>();run<char32_t>();
 if(bits(fast_float::integer_times_pow10<float>(uint64_t(16777219),0))!=0x4b800002)++failures;
 if(bits(fast_float::integer_times_pow10<float>(int64_t(-16777219),0))!=0xcb800002)++failures;
 if(bits(fast_float::integer_times_pow10<double>(uint64_t(2),308))!=UINT64_C(0x7ff0000000000000))++failures;
 if(failures)std::cerr<<failures<<" failures\n";
 return failures?1:0;
}
