import unittest
import numpy as np
from scipy.sparse import csr_matrix
from rsh.planner import Matrix, reorder, partition, layout, execute_cpu


class PlannerTest(unittest.TestCase):
    def matrix(self, m, k=37):
        rng=np.random.default_rng(123+m)
        dense=rng.uniform(-1,1,(m,k)).astype(np.float16)
        dense[rng.uniform(size=dense.shape)>.12]=0
        dense[::7]=0
        a=csr_matrix(dense.astype(np.float32))
        return Matrix(a.indptr.astype(np.int32),a.indices.astype(np.int32),a.data.astype(np.float16),(m,k))

    def test_full_and_partial_output(self):
        for m in (1,7,16,17,31,32,33,65):
            a=self.matrix(m)
            order,stats=reorder(a)
            split=partition(a,order)
            for n in (16,33,64):
                b=np.random.default_rng(n).uniform(-1,1,(a.shape[1],n)).astype(np.float16)
                golden=csr_matrix((a.val.astype(np.float64),a.col,a.ptr),shape=a.shape)@b.astype(np.float64)
                for variant in ('V0','V1','V2','H-V','H-C','H-Skip','V0-R','V2-R'):
                    p=layout(a,order,split,variant)
                    actual=execute_cpu(a,p,b)
                    keep=p['valid'].astype(bool)
                    np.testing.assert_allclose(actual[keep],golden[keep],atol=1e-3,rtol=1e-3,err_msg=f'{m}/{n}/{variant}')

    def test_dynamic_tail_when_original_m_divisible(self):
        ptr=[0];cols=[]
        for r in range(32):
            cols.extend([0] if r==0 else [0,1,2,3,4]);ptr.append(len(cols))
        a=Matrix(np.asarray(ptr,np.int32),np.asarray(cols,np.int32),np.ones(len(cols),np.float16),(32,5))
        p=partition(a,np.arange(32,dtype=np.int32))
        self.assertEqual(p['residual'],[0])
        self.assertEqual(p['groups'],[list(range(1,17))])
        self.assertEqual(p['tail'],list(range(17,32)))

    def test_no_edges_and_empty_matrix(self):
        a=Matrix(np.zeros(34,np.int32),np.zeros(0,np.int32),np.zeros(0,np.float16),(33,19))
        order,_=reorder(a)
        np.testing.assert_array_equal(np.sort(order),np.arange(33))
        split=partition(a,order)
        for variant in ('H-V','H-C','H-Skip'):
            p=layout(a,order,split,variant)
            np.testing.assert_array_equal(execute_cpu(a,p,np.ones((19,16),np.float16)),0)


if __name__=='__main__':unittest.main()
