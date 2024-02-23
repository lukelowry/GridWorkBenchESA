
from ctypes import Structure, POINTER
from ctypes import c_double, c_int

class KLUSymbolic(Structure):
    ''' A (P,Q) is in upper block triangular form.  The kth block goes from
    row/col index R [k] to R [k+1]-1.  The estimated number of nonzeros
    in the L factor of the kth block is Lnz [k]. 
    '''

    _fields_ = [

        # only computed if the AMD ordering is chosen: */
        ("symmetry", c_double),   # symmetry of largest block */
        ("est_flops", c_double),  # est. factorization flop count */
        ("lnz", c_double),
        ("unz", c_double),  # estimated nz in L and U, including diagonals */
        ("Lnz", POINTER(c_double)),      # size n, but only Lnz [0..nblocks-1] is used */

        # computed for all orderings: */
        ("n", c_int),              # input matrix A is n-by-n */
        ("nz", c_int),             # # entries in input matrix */
        ("P", POINTER(c_int)),             # size n */
        ("Q", POINTER(c_int)),             # size n */
        ("R", POINTER(c_int)),             # size n+1, but only R [0..nblocks] is used */
        ("nzoff", c_int),          # nz in off-diagonal blocks */
        ("nblocks", c_int),        # number of blocks */
        ("maxblock", c_int),       # size of largest block */
        ("ordering", c_int),       # ordering used (AMD, COLAMD, or GIVEN) */
        ("do_btf", c_int),        # whether or not BTF preordering was requested */

        # only computed if BTF preordering requested */
        ("structural_rank", c_int),
    ]