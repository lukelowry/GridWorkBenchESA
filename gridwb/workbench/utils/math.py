from numpy import diff

def divergence(u, v):
    '''Central Difference Based Finite Divergence'''

    divx = diff(u[:,:1],axis=0) + diff(u[:,:-1],axis=0) 
    divy = diff(v[1:],axis=1) + diff(v[:-1],axis=1) 
    
    return divx + divy

def curl(u, v):
    '''Central Difference Based Finite Curl'''
    
    a = diff(u,axis=0) #(dy)u
    b = (a[:,:-1] + a[:,1:])/2 # (mux)(dy)(u)

    c = diff(v,axis=1) #(dx)v
    d = (c[:-1] + c[1:])/2 #(muy)(dx)v

    return d-b