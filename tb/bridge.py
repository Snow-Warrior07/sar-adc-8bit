"""Real Icarus RTL simulation with a portable, closed-loop stdin/stdout bridge.

The Python response is computed from observed RTL outputs on every clock.
This avoids a platform-specific VPI installation; it is not an RTL reimplementation.
"""
from dataclasses import dataclass
from pathlib import Path
import subprocess
from tools.common import ROOT,TOOLCHAIN,executable,tool_env


@dataclass
class Snapshot:
    cycle:int;state:int;bit:int;trial:int;data:int;valid:int;ready:int;busy:int;clamp:int;sample:int;evaluate:int


class Bridge:
    def __init__(self,waves=False,rtl_source='rtl/sar_controller.sv'):
        build=ROOT/'build';build.mkdir(exist_ok=True)
        self.image=build/'interactive.vvp'
        ivl_base=TOOLCHAIN/'lib'/'ivl'
        compiler_options=['-B',str(ivl_base)] if ivl_base.exists() else []
        subprocess.run([executable('iverilog')]+compiler_options+['-g2012','-s','interactive_tb','-o',str(self.image),
                        rtl_source,'tb/interactive_tb.sv'],cwd=ROOT,env=tool_env(),check=True,capture_output=True,text=True)
        self.p=subprocess.Popen([executable('vvp'),str(self.image)]+(['+waves'] if waves else []),
                     cwd=ROOT,env=tool_env(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.snapshot=self._read()

    def _read(self):
        while True:
            line=self.p.stdout.readline()
            if not line:raise RuntimeError('RTL bridge terminated: '+self.p.stderr.read()[-2000:])
            if line.startswith('STEP '):return Snapshot(*map(int,line.split()[1:]))

    def step(self,reset=1,start=0,cmp=0):
        self.p.stdin.write(f'{reset} {start} {int(cmp)}\n');self.p.stdin.flush()
        self.snapshot=self._read()
        return self.snapshot

    def reset(self):
        self.step(reset=0);self.step(reset=1)
        assert self.snapshot.state==0 and self.snapshot.data==0 and not self.snapshot.valid

    def convert(self,vin,decision=None,busy_starts=False):
        assert self.snapshot.ready
        accepted=self.snapshot.cycle+1
        self.step(start=1)
        trace=[]
        for _ in range(40):
            s=self.snapshot
            trace.append(vars(s).copy())
            if s.valid:
                return s.data,trace,s.cycle-accepted
            cmp=(vin>=(-.5+s.trial/256)) if decision is None else decision(s)
            self.step(start=int(busy_starts),cmp=cmp)
        raise AssertionError('Conversion did not complete')

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.write('-1 0 0\n');self.p.stdin.flush()
            try:self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:self.p.kill();self.p.wait()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
