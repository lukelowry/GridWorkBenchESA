from numpy import array, zeros, frombuffer, stack, meshgrid, linspace, ndarray
from numpy import single, uint32, double, uint32, uint32

class B3D:

    def __init__(self, fname=None):

        # This function creates a default, tiny B3D object that can be set with data

        # Comment should be a single string which will be stored in the metadata of the B3D file
        self.comment = "Default 2x2 grid with 3 time points"
        self.time_0 = 0 
        self.time_units = 0

        # lat and lon should be a 1-dimensional np arrays of doubles
        # They must be the same length (n)
        # Only variable location point formats are supported here
        self.lat = array([30.5, 30.5, 31.0, 31.0])
        self.lon = array([-84.5, -85.0, -84.5, -85.0])

        # Optional parameter to describe how the lat and lon points are organized into a grid
        # If invalid, it will be updated to n-by-1
        self.grid_dim = [2, 2]
        
        # Time array should be a 1-dimensioal np array of integers. By default they are milliseconds
        # Only variable location point formats are supported here
        self.time = array([0, 1000, 2000], dtype=uint32) 

        # Data: Each of these should be 2-dimensional np arrays of singles
        # First dimension is the time point, with length nt
        # Second dimension is the location point, with length n
        self.ex = zeros([3, 4], dtype=single)
        self.ey = zeros([3, 4], dtype=single)

        if fname is not None:
            self.load_b3d_file(fname)

    @classmethod
    def from_mesh(cls, long, lat, ex: ndarray, ey: ndarray, times=None, comment="GWB Electric Field Data"):
        '''
        Convert mesh-grid style efield data to B3D
        Only Supporting Static Fields at the moment.
        longs: shape (n, )
        lats: shape (m, )
        ex: shape (n, m) Mesh array of X-Component Electric Field
        ey: shape (n, m) Mesh array of Y-Component Electric Field
        '''

        b3d = cls()
        b3d.comment = comment

        # n x m Geographic
        n = len(long) 
        m = len(lat)
        nt = n*m
        X, Y = meshgrid(long, lat)
        b3d.lon = X.reshape(nt, order='F')
        b3d.lat = Y.reshape(nt, order='F')
        b3d.grid_dim = [n, m]

        # Time Periods
        periods = 1
        b3d.time = linspace(0,10, periods, dtype=uint32)

        # Prepare Efield
        eshape = (1,nt)
        eorder = 'F'
        b3d.ex = ex.reshape(eshape, order=eorder).astype(single)
        b3d.ey = ey.reshape(eshape, order=eorder).astype(single)

        return b3d

    def write_b3d_file(self, fname):
        with open(fname, "wb") as f:
            n = self.lat.shape[0]
            nt = self.time.shape[0]
            if self.lon.shape[0] != n:
                raise Exception("Lat and lon must be same length!")
            if self.lat.dtype != double:
                raise Exception("Latitude must by np array of doubles")
            if self.lon.dtype != double:
                raise Exception("Latitude must by np array of doubles")
            if self.time.dtype != uint32:
                raise Exception("Time must by np array of uint32")
            if self.ex.dtype != single:
                raise Exception("Ex must by np array of singles")
            if self.ey.dtype != single:
                raise Exception("Ey must by np array of singles")
            if self.ex.shape[1] != n:
                raise Exception("Ex dimension 2 must be length of latitude")
            if self.ey.shape[1] != n:
                raise Exception("Ey dimension 2 must be length of latitude")
            if self.ex.shape[0] != nt:
                raise Exception("Ex dimension 1 must be length of time")
            if self.ey.shape[0] != nt:
                raise Exception("Ey dimension 1 must be length of time")
            f.write((34280).to_bytes(4, byteorder="little")) # Code
            f.write((4).to_bytes(4, byteorder="little")) # Version 4
            f.write((2).to_bytes(4, byteorder="little")) # Two metastrings
            meta = self.comment + "\0" + str(self.grid_dim) + "\0"
            f.write(meta.encode('ascii'))
            f.write((2).to_bytes(4, byteorder="little")) # 2 float channels
            f.write((0).to_bytes(4, byteorder="little")) # 0 byte channels
            f.write((1).to_bytes(4, byteorder="little")) # Variable locations
            f.write((n).to_bytes(4, byteorder="little")) # Number of lat/lons
            loc0 = zeros(n, dtype=double)
            loc_data = stack([self.lon, self.lat, loc0]).transpose().reshape(1,n*3).tobytes()
            f.write(loc_data)
            f.write((self.time_0).to_bytes(4, byteorder="little")) # Time 0
            f.write((self.time_units).to_bytes(4, byteorder="little")) # Time units code
            f.write((0).to_bytes(4, byteorder="little")) # Time offset not supported
            f.write((0).to_bytes(4, byteorder="little")) # Time step
            f.write((nt).to_bytes(4, byteorder="little")) # Number of time points
            f.write(self.time.tobytes())
            exd = self.ex.reshape(n*nt)
            eyd = self.ey.reshape(n*nt)
            f.write(stack([exd, eyd]).transpose().reshape(n*nt*2).tobytes())

    def load_b3d_file(self, fname):
        with open(fname, "rb") as f:
            b = f.read()

        code = int.from_bytes(b[0:4], "little")
        if code != 34280:
            raise Exception("Invalid B3D file")
        version = int.from_bytes(b[4:8], "little")
        if version == 4:
            nmeta = int.from_bytes(b[8:12], "little")
            self.grid_dim = [0, 0]
            x1 = x2 = 12
            meta_strings = []
            for _ in range(nmeta):
                while b[x2] != 0:
                    x2 += 1
                meta_strings.append(b[x1:x2].decode("ascii"))
                x2 += 1
                x1 = x2
            if nmeta <= 0:
                self.comment = "No comment"
            else:
                self.comment = meta_strings[0]
                if nmeta >= 2:
                    try:
                        dim_text = meta_strings[1].strip("[]")
                        if "," in dim_text:
                            self.grid_dim = [int(x) for x in dim_text.split(',')]
                        else:
                            self.grid_dim = [int(x) for x in dim_text.split()]
                        assert(len(self.grid_dim) == 2)
                    except:
                        self.grid_dim = [0,0]
            float_channels = int.from_bytes(b[x2:x2+4], "little")
            byte_channels = int.from_bytes(b[x2+4:x2+8], "little")
            loc_format = int.from_bytes(b[x2+8:x2+12], "little")
            if float_channels < 2:
                raise Exception("Only B3D files with at least 2 float channels"
                    + " are supported")
            if loc_format != 1:
                raise Exception("Only location format 1 is supported")
            n = int.from_bytes(b[x2+12:x2+16], "little")
            if self.grid_dim[0]*self.grid_dim[1] != n:
                self.grid_dim = [n, 1]
            x3 = x2 + 16 + 3*8*n
            loc_data = frombuffer(b[x2+16:x3],dtype=double).reshape([n, 3]).copy()
            self.lon = loc_data[:,0]
            self.lat = loc_data[:,1]
            self.time_0 = int.from_bytes(b[x3:x3+4], "little")
            self.time_units = int.from_bytes(b[x3+4:x3+8], "little")
            self.time_offset = int.from_bytes(b[x3+8:x3+12], "little")
            time_step = int.from_bytes(b[x3+12:x3+16], "little")
            nt = int.from_bytes(b[x3+16:x3+20], "little")
            if time_step != 0:
                raise Exception("Only B3D files with variable time points are supported")
            x4 = x3 + 20 + 4*nt
            self.time = frombuffer(b[x3+20:x4], dtype=uint32).copy()
            npts = n*nt
            if float_channels == 2 and byte_channels == 0:
                x5 = x4 + 4*2*n*nt
                raw_exy = frombuffer(b[x4:x5], dtype=single)
            else:
                bxy = bytearray(npts*8)
                for i in range(npts):
                    x5 = x4 + i*(float_channels*4+byte_channels)
                    bxy[i*8:(i+1)*8] = b[x5:x5+8]
                raw_exy = frombuffer(bxy, dtype=single)
            edata = raw_exy.reshape([nt, n, 2]).copy()
            self.ex = edata[:,:,0]
            self.ey = edata[:,:,1]
            
        else:
            raise Exception(f"Version {version} not supported")