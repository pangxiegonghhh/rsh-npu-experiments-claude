#include "layouts_flatco.cpp"
#include <cassert>
#include <iostream>
#include <map>
#include <random>

static int checks=0;
static void compare(const vector<uint64_t>&input,uint64_t bound){
 FlatCoCounts flat(bound);unordered_map<uint64_t,uint32_t>reference;
 for(uint64_t key:input){flat.add(key);reference[key]++;}
 map<uint64_t,uint32_t>actual,expected(reference.begin(),reference.end());
 for(size_t i=0;i<flat.keys.size();i++)if(flat.keys[i]!=FlatCoCounts::EMPTY)actual[flat.keys[i]]=flat.values[i];
 assert(actual==expected&&flat.used==reference.size());checks++;
}
int main(){
 assert(FlatCoCounts::capacity_for(0)==1);
 assert(FlatCoCounts::capacity_for(1)==2);
 assert(FlatCoCounts::capacity_for(CO_PAIR_LIMIT+1)==268435456ULL);checks++;
 compare({},0);
 compare(vector<uint64_t>(100,0),1);
 compare({(2147483646ULL<<32)|2147483647ULL,1,(2147483646ULL<<32)|2147483647ULL},2);
 vector<uint64_t>collisions;
 for(uint64_t k=0;collisions.size()<32;k++)if((FlatCoCounts::mix(k)&63)==17)collisions.push_back(k);
 auto repeated=collisions;repeated.insert(repeated.end(),collisions.rbegin(),collisions.rend());compare(repeated,32);
 std::mt19937_64 rng(73915);vector<uint64_t>random;
 for(int i=0;i<30000;i++){uint32_t a=rng()%2147483647,b=rng()%2147483647;if(a==b)b^=1;if(a>b)swap(a,b);uint64_t k=(uint64_t(a)<<32)|b;for(int j=0;j<1+int(rng()%7);j++)random.push_back(k);}
 compare(random,30000);
 compare(vector<uint64_t>(70000,(40000ULL<<32)|50000ULL),1);
 string actual_error,reference_error;FlatCoCounts limited(16,15);unordered_map<uint64_t,int>reference;
 try{for(uint64_t k=1;k<=16;k++)limited.add(k);}catch(const runtime_error&e){actual_error=e.what();}
 try{for(uint64_t k=1;k<=16;k++){reference[k]++;if(reference.size()>15)throw runtime_error("co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE");}}catch(const runtime_error&e){reference_error=e.what();}
 assert(!actual_error.empty()&&actual_error==reference_error&&limited.used==reference.size());checks++;
 bool bound_error=false;try{FlatCoCounts bad(1);bad.add(1);bad.add(2);}catch(const logic_error&){bound_error=true;}assert(bound_error);checks++;
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"random_seed\":73915,\"random_additions\":"<<random.size()<<",\"collision_keys\":32,\"high_count\":70000,\"limit_fixture\":15,\"production_limit\":"<<CO_PAIR_LIMIT<<",\"scientific_computation\":false}\n";
}
