"""Create cross-size numeric tables and measured charts, retaining evidence labels."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from ppbench.crossreport import cross_summary

def main():
    p=argparse.ArgumentParser();p.add_argument('runs',nargs='+');p.add_argument('--output',required=True);p.add_argument('--png',action='store_true');a=p.parse_args();cross_summary(a.runs,a.output,a.png)
if __name__=='__main__':main()
