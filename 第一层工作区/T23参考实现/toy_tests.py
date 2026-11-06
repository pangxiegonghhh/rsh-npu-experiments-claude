#!/usr/bin/env python3
"""Hand-checked toy cases for porting (each expected value was worked out by hand from README §2–§5).
usage: python3 -B toy_tests.py      prints 'T23 toy tests: OK' and exits 0, or lists the failures and exits 1."""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t23_candidates as C

fails = []
def check(name, got, exp):
    if got != exp: fails.append((name, got, exp))

# P, W = 4. Generation order: [5,1,3,2] (complete), [7,6], [9], [4,8,0], [10], [11,12].
# Short groups sorted (size desc, min row asc): [0,4,8] [6,7] [11,12] [9] [10].
#  target [0,4,8]: scan (size asc, min row asc) [9] [10] [6,7] [11,12] -> takes [9] -> full [0,4,8,9]
#  target [6,7]:   scan [10] [11,12] -> takes [10] (3); [11,12] would give 5 > 4 -> stays short [6,7,10]
#  target [11,12]: nothing left -> stays short
# Output: [1,2,3,5] + [0,4,8,9] + short groups by (size desc, min row): [6,7,10], [11,12]; one group cut by windows.
flat, st = C.postprocess_P([[5, 1, 3, 2], [7, 6], [9], [4, 8, 0], [10], [11, 12]], W=4)
check('P order', flat, [1, 2, 3, 5, 0, 4, 8, 9, 6, 7, 10, 11, 12])
check('P stats', (st['P_merges'], st['P_new_full'], st['short_after'], st['groups_cut_by_windows']), (2, 1, 2, 1))

# C4 / C7 on a 6-point graph, W = 3, L = 128. Edges: 0-1 0-2 1-2 2-3 3-4 3-5 4-5.
# S: 0{1,2} 1{0,2} 2{0,1,3} 3{2,4,5} 4{3,5} 5{3,4}; sequence by (min col, id): 1(0) 2(0) 0(1) 3(2) 4(3) 5(3).
# C4-U group 1: seed 1, U={0,2}, z=2. Candidates: 2 -> z'=5, U'={0,1,2,3}=4 -> 5/4; 0 -> z'=4, U'={0,1,2}=3 -> 4/3 (best);
#   3 -> z'=5, U'={0,2,4,5}=4 -> 5/4; 4 -> 4/{0,2,3,5}=1; 5 -> 1. Take 0. Then U={0,1,2}, z=4: 2 -> 7/4; 3 -> 7/5; 4 -> 6/5;
#   5 -> 6/5. Take 2. Group [1,0,2]. Group 2: seed 3, then 4 (z'=5,U'={2,3,4,5}=4 -> 5/4) vs 5 (same 5/4, same length 2) -> id 4;
#   then 5. Order [1,0,2,3,4,5].
adj = [set() for _ in range(6)]
for a, b in [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4), (3, 5), (4, 5)]: adj[a].add(b); adj[b].add(a)
check('C4-U toy', C.c4(adj, 'U', W=3)[0], [1, 0, 2, 3, 4, 5])
# C7-I group 1: seed 1, U={0,2}. inter: 2 -> |{0,1,3}&{0,2}|=1; 0 -> |{1,2}&{0,2}|=1; 3 -> 1; 4 -> 0; 5 -> 0.
#   Ties at 1 -> longer row: 2 (len 3) and 3 (len 3) -> smaller id 2. U={0,1,2,3}: 0 -> 2; 3 -> 1; 4 -> 1; 5 -> 1 -> take 0.
#   Group [1,2,0]; group 2 [3,4,5] (4 and 5 tie, id 4 first). Order [1,2,0,3,4,5].
check('C7-I toy', C.c7_i(adj, W=3)[0], [1, 2, 0, 3, 4, 5])

# Empty points go last in original id order. Sequence by (min col, id): 2 (min col 1) before 1 (min col 2).
adj2 = [set(), {2}, {1}, set()]
check('empty last', C.c4(adj2, 'U', W=2)[0], [2, 1, 0, 3])

print('T23 toy tests:', 'OK' if not fails else 'FAILED')
for f in fails: print('  ', f)
sys.exit(1 if fails else 0)
