"""External admission/order policy. Does not modify vLLM's internal scheduler."""
def decision(pending, active, now, mode):
    if mode != 'adaptive':
        return int(mode), 64, 'fifo'
    short_fraction = sum(r['group']=='short' for r in pending)/max(1,len(pending))
    congested = len(pending)>=8
    # Increase admission only for a predominantly short backlog; throttle mixed
    # prefills. Active work is never preempted when the limit decreases.
    limit = 64 if congested and short_fraction>=.75 else 16
    quantum = 8 if congested else 1
    return limit, quantum, 'aged_shortest' if congested else 'fifo'

def pick(pending, now, order):
    if order=='fifo': return 0
    aged=[i for i,r in enumerate(pending) if now-r['enqueued_s']>=1.0]
    if aged: return min(aged,key=lambda i:pending[i]['enqueued_s'])
    return min(range(len(pending)),key=lambda i:(pending[i]['input_tokens_estimate'],pending[i]['enqueued_s']))
