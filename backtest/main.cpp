#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <chrono>
// Long/cash, one bar execution delay, proportional fee + slippage per turnover.
int main(int argc,char**argv) { try {
 if(argc<2) throw std::runtime_error("usage: backtest signals.csv [cost_bps=10]");
 double cost=argc>2?std::stod(argv[2])/10000.:0.001;
 if(!std::isfinite(cost)||cost<0||cost>=1) throw std::runtime_error("invalid cost");
 std::ifstream f(argv[1]); if(!f) throw std::runtime_error("cannot open input");
 std::string line; std::getline(f,line); if(line!="timestamp,close,signal") throw std::runtime_error("invalid header");
 double equity=1,peak=1,dd=0,prev=0; int held=0,pending=0; long long last=-1; size_t n=0,trades=0;
 auto start=std::chrono::steady_clock::now();
 while(std::getline(f,line)) {
  std::istringstream row(line); std::string t,p,s,extra;
  if(!std::getline(row,t,',')||!std::getline(row,p,',')||!std::getline(row,s,',')||std::getline(row,extra,',')) throw std::runtime_error("invalid row");
  size_t used; auto timestamp=std::stoll(t,&used); if(used!=t.size()) throw std::runtime_error("invalid timestamp");
  double price=std::stod(p,&used); if(used!=p.size()||!std::isfinite(price)||price<=0) throw std::runtime_error("invalid price");
  int signal=std::stoi(s,&used); if(used!=s.size()||(signal!=0&&signal!=1)) throw std::runtime_error("invalid signal");
  if(n && timestamp!=last+60000) throw std::runtime_error("noncontiguous timestamps");
  if(n) {equity*=1+held*(price/prev-1); if(pending!=held){equity*=1-cost; ++trades;} held=pending;}
  peak=std::max(peak,equity); dd=std::max(dd,1-equity/peak);
  pending=signal; prev=price;last=timestamp;++n;
 }
 if(n<2) throw std::runtime_error("need two rows");
 if(held){equity*=1-cost;++trades;dd=std::max(dd,1-equity/peak);}
 double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 std::cout<<"{\"rows\":"<<n<<",\"equity\":"<<equity<<",\"return\":"<<equity-1<<",\"max_drawdown\":"<<dd<<",\"fills\":"<<trades<<",\"seconds\":"<<seconds<<"}\n";
 } catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;} }
