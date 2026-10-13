"""Optional sampled process-tree RSS and CPU snapshots, NOT full-system/PSS accounting."""
import os,threading,time
DEFINITION={'rss':'peak over polling snapshots of sum of resident bytes for root Python process and recursively discoverable descendants (including local JVM/Python Spark workers); includes baseline resident memory; shared pages may be counted more than once; not PSS or total machine memory',
'cpu':'sum of maximum observed cumulative user+system CPU seconds per (pid,creation_time) minus the initial snapshot for existing processes; newly observed processes created during measurement start from zero. Short-lived or inaccessible processes may be missed. Sampling thread CPU is included in root.',
'limits':'sampling may miss transient peaks and exited processes; remote workers/non-descendant services excluded; no swap/page-cache/other-machine accounting; AccessDenied and disappeared processes recorded'}

class ProcessTreeMonitor:
    def __init__(self,interval=.05):
        if interval<=0:raise ValueError('positive sample interval required')
        self.interval=interval;self.stop_event=threading.Event();self.thread=None;self.started=time.time();self.baseline={};self.maximum={};self.pids=set();self.peak=0;self.polls=0;self.errors=0;self.available=False
        try:
            import psutil
            self.psutil=psutil;self.root=psutil.Process(os.getpid());self.available=True
        except ImportError:pass
    def _poll(self,initial=False):
        if not self.available:return
        try:processes=[self.root]+self.root.children(recursive=True)
        except (self.psutil.NoSuchProcess,self.psutil.AccessDenied):self.errors+=1;processes=[self.root]
        rss=0
        for p in processes:
            try:
                ident=(p.pid,p.create_time());cpu=p.cpu_times();value=cpu.user+cpu.system;rss+=p.memory_info().rss
                if ident not in self.baseline:self.baseline[ident]=value if initial or ident[1]<self.started else 0.0
                self.maximum[ident]=max(value,self.maximum.get(ident,value));self.pids.add(ident)
            except (self.psutil.NoSuchProcess,self.psutil.AccessDenied):self.errors+=1
        self.peak=max(self.peak,rss);self.polls+=1
    def _loop(self):
        while not self.stop_event.wait(self.interval):self._poll()
    def start(self):
        self.started=time.time();self._poll(initial=True)
        if self.available:self.thread=threading.Thread(target=self._loop,daemon=True);self.thread.start()
        return self
    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join()
        self._poll()
        return {'available':self.available,'sample_interval_sec':self.interval,'peak_tree_rss_bytes':self.peak if self.available else None,'tree_cpu_seconds':sum(max(0,self.maximum[k]-self.baseline[k]) for k in self.maximum) if self.available else None,'snapshots':self.polls,'distinct_processes':len(self.pids),'process_access_errors':self.errors,'definition':DEFINITION}
