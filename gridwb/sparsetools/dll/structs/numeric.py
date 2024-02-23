
from ctypes import Structure, POINTER
from ctypes import c_double, c_int, c_void_p, c_size_t

class KLUNumeric(Structure):
    '''LU factors of each block, the pivot row permutation, and the
    entries in the off-diagonal blocks '''

    _fields_= [

        ("n", c_int),             # A is n-by-n */
        ("nblocks", c_int),      # number of diagonal blocks */
        ("lnz", c_int),         # actual nz in L, including diagonal */
        ("unz", c_int),          # actual nz in U, including diagonal */
        ("max_lnz_block", c_int),# max actual nz in L in any one block, incl. diag */
        ("max_unz_block", c_int),# max actual nz in U in any one block, incl. diag */
        ("Pnum", POINTER(c_int)),        # size n. final pivot permutation */
        ("Pinv", POINTER(c_int)),         # size n. inverse of final pivot permutation */

        # LU factors of each block */
        ("Lip", POINTER(c_int)),          # size n. pointers into LUbx[block] for L */
        ("Uip", POINTER(c_int)),         # size n. pointers into LUbx[block] for U */
        ("Llen", POINTER(c_int)),        # size n. Llen [k] = # of entries in kth column of L */
        ("Ulen", POINTER(c_int)),         # size n. Ulen [k] = # of entries in kth column of U */
        ("LUbx", POINTER(c_void_p)),  #void type?     # L and U indices and entries (excl. diagonal of U) */
        ("LUsize" , POINTER(c_size_t)),    # size of each LUbx [block], in sizeof (Unit) */
        ("Udiag", c_void_p),       # diagonal of U */

        # scale factors; can be NULL if no scaling */
        ("Rs" , POINTER(c_double)),        # size n. Rs [i] is scale factor for row i */

        # permanent workspace for factorization and solve */
        ("worksize" , c_size_t),   # size (in bytes) of Work */
        ("Work", c_void_p),        # workspace */
        ("Xwork", c_void_p),       # alias into Numeric->Work */
        ("Iwork", POINTER(c_int)),        # alias into Numeric->Work */

        # off-diagonal entries in a conventional compressed-column sparse matrix */
        ("Offp", POINTER(c_int)),         # size n+1, column pointers */
        ("Offi", POINTER(c_int)),         # size nzoff, row indices */
        ("Offx", c_void_p),        # size nzoff, numerical values */
        ("nzoff", c_int),
    ]
