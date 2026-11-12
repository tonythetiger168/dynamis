import argparse
import json
from pathlib import Path
import subprocess
import tempfile

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]/'src/txdpi.cpp')
p.add_argument('--output',type=Path);a=p.parse_args()
cases=[('write','addr=3,data=7'),('say"hello','path=C:\\rtl\\input'),('line\nkind','value=tab\tCR\rLF\n'),
       ('controls','value='+''.join(chr(i) for i in range(1,32))),('交易','value=漢字 δύναμις'),('','')]
results=[]
with tempfile.TemporaryDirectory(prefix='dynamis-recorder-') as tmp:
    folder=Path(tmp);harness=folder/'test.cpp';binary=folder/'test'
    harness.write_text('''#include <fstream>
#include <sstream>
#include <string>
extern "C" void tx_open(const char*);
extern "C" void tx_record(const char*,long long,const char*);
extern "C" void tx_close();
int main(int argc,char** argv){
std::ifstream k(argv[1],std::ios::binary),p(argv[2],std::ios::binary);
std::stringstream a,b;a<<k.rdbuf();b<<p.rdbuf();
tx_open(argv[3]);tx_record(a.str().c_str(),7,b.str().c_str());tx_record(nullptr,8,nullptr);tx_close();
}
''')
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-I','/usr/share/verilator/include/vltstd',
                    str(a.source.resolve()),str(harness),'-o',str(binary)],check=True,capture_output=True,timeout=30)
    for i,(kind,payload) in enumerate(cases):
        (folder/'kind').write_text(kind,encoding='utf-8');(folder/'payload').write_text(payload,encoding='utf-8',newline='')
        subprocess.run([str(binary),str(folder/'kind'),str(folder/'payload'),str(folder/'out')],check=True,timeout=10)
        try:
            rows=[json.loads(line) for line in (folder/'out').read_text(encoding='utf-8').splitlines()]
            passed=rows==[{'kind':kind,'t':7,'payload':payload},{'kind':'','t':8,'payload':''}]
            valid=True
        except (ValueError,UnicodeError):passed=False;valid=False;rows=[]
        results.append({'case':i,'pass':passed,'valid_json':valid,
                        'payload_roundtrip':bool(rows) and rows[0]=={'kind':kind,'t':7,'payload':payload}})
report={'cases':results,'passed':sum(r['pass'] for r in results),'total':len(results),
        'scope':'native C++ recorder JSON roundtrip, not DPI simulator execution'}
if a.output:
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2))
print(json.dumps(report));raise SystemExit(report['passed']!=report['total'])
