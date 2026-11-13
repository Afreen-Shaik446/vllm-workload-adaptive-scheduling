"""Requires genuine engine allocation records; mock/no-change logs fail.
This checks consistency, not cryptographic authenticity or model execution.
"""
import argparse,json
from pathlib import Path

def verify(rows,adaptive=True):
    if not rows:raise ValueError('No scheduler steps')
    budgets=set();nonempty=0
    for r in rows:
        alloc=r.get('num_scheduled_tokens')
        if not isinstance(alloc,dict):raise ValueError('Missing real SchedulerOutput allocations')
        if any(not isinstance(n,int) or n<0 for n in alloc.values()):raise ValueError('Invalid allocation')
        total=sum(alloc.values())
        if total!=r['actual_tokens'] or not 0<=total<=r['budget']<=r['ceiling']:raise ValueError('Allocation/budget mismatch')
        budgets.add(r['budget']);nonempty+=bool(total)
    if not nonempty:raise ValueError('No actual scheduled work')
    if adaptive and (len(budgets)<2 or not any(r['actual_tokens']>0 and r['budget']<r['ceiling'] for r in rows)):raise ValueError('No demonstrated adaptation with scheduled work; increase pressure in a separate integration run')
    return dict(steps=len(rows),nonempty_steps=nonempty,budgets=sorted(budgets),status='allocation consistency passed; verify model response and process provenance separately')
def main():
    p=argparse.ArgumentParser();p.add_argument('log');p.add_argument('--fixed',action='store_true');a=p.parse_args()
    print(json.dumps(verify([json.loads(s) for s in Path(a.log).read_text().splitlines()],not a.fixed),indent=2))
if __name__=='__main__':main()
