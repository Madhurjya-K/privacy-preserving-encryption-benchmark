"""Generate paper input only from complete secure-size public-data Spark evidence."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from ppbench.crossreport import latex_results

def main():
    p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',required=True);a=p.parse_args();latex_results(a.runs,a.output)
if __name__=='__main__':main()
