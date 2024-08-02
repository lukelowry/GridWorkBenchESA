from numpy import diff

def divergence(u, v):
    '''Central Difference Based Finite Divergence'''

    # Selects inner region
    r = slice(1,-1)

    # Compute Component Wise
    divx = diff(u[r,1:],axis=1) + diff(u[r,:-1],axis=1) 
    divy = diff(v[1:, r],axis=0) + diff(v[:-1, r],axis=0) 
    
    return divx + divy

def curl(u, v):
    '''Central Difference Based Finite Curl'''
    
    a = diff(u,axis=0) #(dy)u
    b = (a[:,:-1] + a[:,1:])/2 # (mux)(dy)(u)

    c = diff(v,axis=1) #(dx)v
    d = (c[:-1] + c[1:])/2 #(muy)(dx)v

    return d-b