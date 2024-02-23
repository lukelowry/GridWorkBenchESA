
from ctypes import Structure, POINTER, CFUNCTYPE
from ctypes import c_double, c_int, c_void_p, c_size_t

class KLUCommon(Structure):
    _fields_ = [
        ("tol", c_double),                # double tol
        ("memgrow", c_double),            # double memgrow
        ("initmem_amd", c_double),        # double initmem_amd
        ("initmem", c_double),            # double initmem
        ("maxwork", c_double),            # double maxwork
        ("btf", c_int),                   # int btf
        ("ordering", c_int),              # int ordering
        ("scale", c_int),                 # int scale
        ("user_order", CFUNCTYPE(c_int, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER('KLUCommon'))), # int (*user_order)(int, int *, int *, int *, struct klu_common_struct *)
        ("user_data", c_void_p),          # void *user_data
        ("halt_if_singular", c_int),      # int halt_if_singular
        ("status", c_int),                # int status
        ("nrealloc", c_int),              # int nrealloc
        ("structural_rank", c_int),       # int structural_rank
        ("numerical_rank", c_int),        # int numerical_rank
        ("singular_col", c_int),          # int singular_col
        ("noffdiag", c_int),              # int noffdiag
        ("flops", c_double),              # double flops
        ("rcond", c_double),              # double rcond
        ("condest", c_double),            # double condest
        ("rgrowth", c_double),            # double rgrowth
        ("work", c_double),               # double work
        ("memusage", c_size_t),           # size_t memusage
        ("mempeak", c_size_t),            # size_t mempeak
    ]
