# 工作空间公式（估算，不是实测 RSS）

8 GiB = 8589934592 bytes。LS 在分配前使用固定安全估算：
n*ceil(K/64)*8 + K*NB*2 + K*ceil(n/64)*16 + NB*ceil(K/64)*16 + nnz(A0)*48 + K*1024。
K=ceil((n-residual_rows)/W), NB=ceil(n/W)，本表W=16。残余集合按A0度<=τ固定，A1残余非零=A0残余非零+残余行数。
residual-workspace.csv具体数值来自保存的degrees.npy和原公式；没有启动LS或评价器。

v7 co-chain flat table上界 bound=min(枚举点对数, P*(P-1)/2,100000001)。
capacity为满足 capacity*7>=bound*10 的最小2次幂。
估算=上下文及工作向量的实际capacity字节 + capacity*(8+4) + bound*sizeof(tuple<int,int,int>) + 1073741824。
只有估算<=8GiB才走flat表，否则回退到原map；map独特点对>100000000触发带8GiB估算文字的错误。
原进程的向量capacity/点对枚举未完整记录，因此不补造每个co-chain条件的字节值，具体数值标缺失。
inter候选数>200000000也有工作空间保护。上述门槛均不能替代峰值RSS实测。
原始公式与哈希见formula-sources/，无新算布局/LS/D。
