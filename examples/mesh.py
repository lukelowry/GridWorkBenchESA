"""
Discrete geometry and linear algebra utilities.

This module provides tools for:
- Linear algebra: matrix decomposition, eigenvalue analysis, spectral methods
- Unstructured meshes: PLY file I/O, graph operations
- Structured 2D grids: finite difference operators

Both mesh types support computing incidence matrices, Laplacians, and
other discrete differential operators.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
from numpy import block, diag, real, imag
from numpy.typing import NDArray
import scipy.sparse as sp
from scipy.sparse import csc_matrix, csr_matrix
from scipy.sparse.linalg import eigsh
from scipy.linalg import schur

__all__ = [
    # Physical constants
    'MU0',
    # Graph Laplacians
    'pathlap',
    'pathincidence',
    # Matrix transformations
    'normlap',
    'hermitify',
    'sorteig',
    # Mesh utilities
    'Mesh',
    'extract_unique_edges',
    'Grid2D',
]


# =============================================================================
# Unstructured Mesh Utilities
# =============================================================================

def extract_unique_edges(faces: list[list[int]]) -> NDArray[np.int_]:
    """
    Extract unique edges from a list of mesh faces.

    Each face is a list of vertex indices forming a polygon. Edges are
    extracted by connecting consecutive vertices (including last to first).
    Duplicate edges are removed, and each edge is stored with the smaller
    vertex index first.

    Parameters
    ----------
    faces : list of list of int
        Mesh faces, where each face is a list of vertex indices.

    Returns
    -------
    np.ndarray
        An (M, 2) array of unique edges, sorted lexicographically.
        Column 0 contains the smaller vertex index for each edge.

    Examples
    --------
    >>> faces = [[0, 1, 2], [1, 2, 3]]
    >>> extract_unique_edges(faces)
    array([[0, 1],
           [0, 2],
           [1, 2],
           [1, 3],
           [2, 3]])
    """
    unique_edges = set()

    for face in faces:
        n = len(face)
        for i in range(n):
            u = face[i]
            v = face[(i + 1) % n]
            edge = (u, v) if u < v else (v, u)
            unique_edges.add(edge)

    return np.array(sorted(unique_edges), dtype=np.int_)


@dataclass
class Mesh:
    """
    A 3D mesh consisting of vertices and polygonal faces.

    This class represents an unstructured mesh and provides methods for
    loading from PLY files and computing graph-theoretic properties like
    incidence matrices and Laplacians.

    Attributes
    ----------
    vertices : list of tuple
        List of (x, y, z) vertex coordinates.
    faces : list of list of int
        List of faces, where each face is a list of vertex indices.

    Examples
    --------
    >>> mesh = Mesh.from_ply("model.ply")
    >>> L = mesh.to_laplacian()
    >>> xyz = mesh.get_xyz()
    """
    vertices: list[tuple[float, float, float]]
    faces: list[list[int]]

    @classmethod
    def from_ply(cls, filepath: str) -> Mesh:
        """
        Load a mesh from a PLY file.

        Supports both ASCII and binary_little_endian PLY formats.
        Extracts vertex positions (x, y, z) and face connectivity.

        Parameters
        ----------
        filepath : str
            Path to the PLY file.

        Returns
        -------
        Mesh
            The loaded mesh.

        Raises
        ------
        ValueError
            If the PLY format is not supported.

        Notes
        -----
        Supported vertex property types: char, uchar, short, ushort,
        int, uint, float, double.
        """
        import struct

        with open(filepath, 'rb') as f:
            # Parse header
            header_ended = False
            fmt = "ascii"
            vertex_count = 0
            face_count = 0
            vertex_props = []
            current_element = None

            while not header_ended:
                line = f.readline().strip()
                if not line:
                    break
                line_str = line.decode('ascii', errors='ignore')

                if line_str == "end_header":
                    header_ended = True
                    break

                parts = line_str.split()
                if not parts:
                    continue

                if parts[0] == "format":
                    fmt = parts[1]
                elif parts[0] == "element":
                    current_element = parts[1]
                    if current_element == "vertex":
                        vertex_count = int(parts[2])
                    elif current_element == "face":
                        face_count = int(parts[2])
                elif parts[0] == "property":
                    if current_element == "vertex":
                        vertex_props.append((parts[2], parts[1]))

            # Parse body
            vertices = []
            faces = []

            if fmt == "ascii":
                lines = f.readlines()
                for i in range(vertex_count):
                    parts = lines[i].strip().split()
                    v = (float(parts[0]), float(parts[1]), float(parts[2]))
                    vertices.append(v)

                for i in range(face_count):
                    parts = lines[vertex_count + i].strip().split()
                    vertex_indices = [int(x) for x in parts[1:]]
                    faces.append(vertex_indices)

            elif fmt == "binary_little_endian":
                np_type_map = {
                    'char': 'i1', 'uchar': 'u1', 'short': 'i2', 'ushort': 'u2',
                    'int': 'i4', 'uint': 'u4', 'float': 'f4', 'double': 'f8'
                }
                dtype_fields = [
                    (name, np_type_map.get(type_str, 'f4'))
                    for name, type_str in vertex_props
                ]
                vertex_dtype = np.dtype(dtype_fields)

                vertex_data = f.read(vertex_count * vertex_dtype.itemsize)
                v_arr = np.frombuffer(vertex_data, dtype=vertex_dtype)

                if all(n in v_arr.dtype.names for n in ('x', 'y', 'z')):
                    vertices = list(zip(v_arr['x'], v_arr['y'], v_arr['z']))
                else:
                    names = v_arr.dtype.names
                    vertices = list(zip(
                        v_arr[names[0]], v_arr[names[1]], v_arr[names[2]]
                    ))

                for _ in range(face_count):
                    n = struct.unpack('<B', f.read(1))[0]
                    indices = list(struct.unpack(f'<{n}i', f.read(n * 4)))
                    faces.append(indices)
            else:
                raise ValueError(f"Unsupported PLY format: {fmt}")

        return cls(vertices=vertices, faces=faces)

    def get_incidence_matrix(self) -> csc_matrix:
        """
        Construct the oriented incidence matrix for the mesh graph.

        The incidence matrix B has shape (|V|, |E|) where each column
        represents an edge with +1 at the source vertex and -1 at the
        target vertex.

        Returns
        -------
        scipy.sparse.csc_matrix
            The incidence matrix B.

        Notes
        -----
        The edge orientation is determined by vertex index ordering
        (smaller index is source, larger is target).
        """
        edges = extract_unique_edges(self.faces)
        num_verts = len(self.vertices)
        num_edges = len(edges)

        row = edges.ravel()
        col = np.repeat(np.arange(num_edges), 2)
        data = np.tile([1.0, -1.0], num_edges)

        return csc_matrix((data, (row, col)), shape=(num_verts, num_edges))

    def get_xyz(self) -> NDArray[np.float64]:
        """
        Get vertex coordinates as a numpy array.

        Returns
        -------
        np.ndarray
            An (N, 3) array of vertex coordinates.
        """
        return np.array(self.vertices, dtype=np.float64)

    def to_laplacian(self) -> csc_matrix:
        """
        Compute the graph Laplacian matrix.

        The Laplacian is computed as L = B @ B.T where B is the
        incidence matrix. This produces the combinatorial Laplacian
        with diagonal entries equal to vertex degrees.

        Returns
        -------
        scipy.sparse.csc_matrix
            The graph Laplacian matrix L.
        """
        B = self.get_incidence_matrix()
        return B @ B.T


# =============================================================================
# Structured Grid Utilities
# =============================================================================

class Grid2D:
    """
    Graph-based discrete operator generator for regular 2D grids.

    Constructs an oriented incidence matrix for the 2D grid graph and
    derives all discrete operators (gradient, divergence, curl, Laplacian)
    from it. The Laplacian is computed as L = A^T diag(w) A where A is
    the incidence matrix and w are edge weights.

    Also provides boolean masks for boundary and interior region selection,
    useful for applying boundary conditions in finite difference schemes.

    Parameters
    ----------
    shape : tuple of int
        Grid dimensions (nx, ny).

    Attributes
    ----------
    nx : int
        Number of grid points in x direction.
    ny : int
        Number of grid points in y direction.
    size : int
        Total number of grid points (nx * ny).
    n_edges_x : int
        Number of horizontal edges: (nx - 1) * ny.
    n_edges_y : int
        Number of vertical edges: nx * (ny - 1).
    n_edges : int
        Total number of edges.

    Examples
    --------
    >>> grid = Grid2D((10, 10))
    >>> A = grid.incidence()          # Oriented incidence matrix
    >>> L = grid.laplacian()          # L = A^T A (unit weights)
    >>> Dx, Dy = grid.gradient()      # Extracted from A
    >>> u[grid.boundary] = 0          # Apply Dirichlet BC

    Notes
    -----
    Grid points are indexed in Fortran order (column-major), so point
    (x, y) maps to flat index y * nx + x. This matches numpy's 'F' order.

    Edges are ordered with all horizontal edges first, then vertical edges.
    Each edge is oriented from the lower-index node to the higher-index node
    (left-to-right for horizontal, bottom-to-top for vertical).
    """

    def __init__(self, shape: tuple[int, int]) -> None:
        self.nx, self.ny = shape
        self.size = self.nx * self.ny
        self.n_edges_x = (self.nx - 1) * self.ny
        self.n_edges_y = self.nx * (self.ny - 1)
        self.n_edges = self.n_edges_x + self.n_edges_y

        # Build and cache the incidence matrix and region masks
        self._A = self._build_incidence()
        self._build_masks()

    @property
    def shape(self) -> tuple[int, int]:
        """Grid dimensions (nx, ny)."""
        return (self.nx, self.ny)

    # -----------------------------------------------------------------
    # Region masks (formerly GridSelector)
    # -----------------------------------------------------------------

    def _build_masks(self) -> None:
        """Compute boolean masks for boundary and interior regions."""
        idx = np.arange(self.size)
        x = idx % self.nx
        y = idx // self.nx

        self._left = (x == 0)
        self._right = (x == self.nx - 1)
        self._bottom = (y == 0)
        self._top = (y == self.ny - 1)
        self._corners = (self._left | self._right) & (self._bottom | self._top)
        self._boundary = self._left | self._right | self._bottom | self._top
        self._interior = ~self._boundary

    @property
    def left(self) -> NDArray[np.bool_]:
        """Boolean mask for left boundary (x = 0)."""
        return self._left

    @property
    def right(self) -> NDArray[np.bool_]:
        """Boolean mask for right boundary (x = nx-1)."""
        return self._right

    @property
    def bottom(self) -> NDArray[np.bool_]:
        """Boolean mask for bottom boundary (y = 0)."""
        return self._bottom

    @property
    def top(self) -> NDArray[np.bool_]:
        """Boolean mask for top boundary (y = ny-1)."""
        return self._top

    @property
    def corners(self) -> NDArray[np.bool_]:
        """Boolean mask for corner points."""
        return self._corners

    @property
    def boundary(self) -> NDArray[np.bool_]:
        """Boolean mask for all boundary points."""
        return self._boundary

    @property
    def interior(self) -> NDArray[np.bool_]:
        """Boolean mask for interior (non-boundary) points."""
        return self._interior

    # -----------------------------------------------------------------
    # Indexing
    # -----------------------------------------------------------------

    def flat_index(self, x: int, y: int) -> int:
        """
        Convert 2D coordinates to flat index.

        Parameters
        ----------
        x : int
            X coordinate (0 to nx-1).
        y : int
            Y coordinate (0 to ny-1).

        Returns
        -------
        int
            Flat index in column-major order.
        """
        return y * self.nx + x

    def grid_coords(self, idx: int) -> tuple[int, int]:
        """
        Convert flat index to 2D coordinates.

        Parameters
        ----------
        idx : int
            Flat index.

        Returns
        -------
        tuple of int
            (x, y) coordinates.
        """
        return idx % self.nx, idx // self.nx

    def iter_points(self) -> Iterator[tuple[int, int, int]]:
        """
        Iterate over all grid points.

        Yields
        ------
        tuple of int
            (x, y, flat_index) for each grid point in column-major order.
        """
        for y in range(self.ny):
            for x in range(self.nx):
                yield x, y, self.flat_index(x, y)

    # -----------------------------------------------------------------
    # Incidence matrix (core data structure)
    # -----------------------------------------------------------------

    def _build_incidence(self) -> csr_matrix:
        """
        Build the oriented incidence matrix of the 2D grid graph.

        The matrix A has shape (n_edges, n_nodes). Each row has exactly
        two nonzeros: -1 at the source node and +1 at the target node.
        Horizontal edges are listed first, then vertical edges.

        Returns
        -------
        scipy.sparse.csr_matrix
            Incidence matrix A of shape (n_edges, n_nodes).
        """
        n = self.size
        nx, ny = self.nx, self.ny

        # --- Horizontal edges: (x, y) → (x+1, y) ---
        # For each row y, there are (nx-1) horizontal edges
        ex = self.n_edges_x
        if ex > 0:
            # Source nodes for horizontal edges
            all_nodes = np.arange(n).reshape(ny, nx)
            src_x = all_nodes[:, :-1].ravel()   # left endpoints
            tgt_x = all_nodes[:, 1:].ravel()     # right endpoints
            edge_idx_x = np.arange(ex)
        else:
            src_x = np.array([], dtype=int)
            tgt_x = np.array([], dtype=int)
            edge_idx_x = np.array([], dtype=int)

        # --- Vertical edges: (x, y) → (x, y+1) ---
        ey = self.n_edges_y
        if ey > 0:
            all_nodes = np.arange(n).reshape(ny, nx)
            src_y = all_nodes[:-1, :].ravel()    # bottom endpoints
            tgt_y = all_nodes[1:, :].ravel()      # top endpoints
            edge_idx_y = np.arange(ex, ex + ey)
        else:
            src_y = np.array([], dtype=int)
            tgt_y = np.array([], dtype=int)
            edge_idx_y = np.array([], dtype=int)

        # Assemble COO data
        rows = np.concatenate([edge_idx_x, edge_idx_x, edge_idx_y, edge_idx_y])
        cols = np.concatenate([src_x, tgt_x, src_y, tgt_y])
        data = np.concatenate([
            -np.ones(ex), np.ones(ex),
            -np.ones(ey), np.ones(ey),
        ])

        return csr_matrix((data, (rows, cols)), shape=(self.n_edges, n))

    def incidence(self) -> csr_matrix:
        """
        Return the oriented incidence matrix of the 2D grid graph.

        The matrix A has shape (n_edges, n_nodes). Rows 0..n_edges_x-1
        correspond to horizontal edges, and rows n_edges_x..n_edges-1
        correspond to vertical edges. Each row has -1 at the source
        node and +1 at the target node.

        Returns
        -------
        scipy.sparse.csr_matrix
            Incidence matrix A.
        """
        return self._A

    # -----------------------------------------------------------------
    # Discrete operators derived from the incidence matrix
    # -----------------------------------------------------------------

    def gradient(self) -> tuple[csr_matrix, csr_matrix]:
        """
        Build gradient operators for a scalar field.

        The gradient operators Dx, Dy are extracted directly from the
        incidence matrix A: Dx consists of the horizontal-edge rows,
        and Dy consists of the vertical-edge rows.

        Returns
        -------
        Dx : scipy.sparse.csr_matrix
            X-direction gradient, shape (n_edges_x, n_nodes).
        Dy : scipy.sparse.csr_matrix
            Y-direction gradient, shape (n_edges_y, n_nodes).

        Notes
        -----
        For a scalar field u (length n_nodes), the gradient components
        are Dx @ u and Dy @ u.
        """
        Dx = self._A[:self.n_edges_x, :]
        Dy = self._A[self.n_edges_x:, :]
        return Dx, Dy

    def divergence(self) -> csr_matrix:
        """
        Build divergence operator for a vector field.

        The divergence is the negative adjoint of the gradient:
        div = -A^T, applied to an edge-based vector field.

        Returns
        -------
        scipy.sparse.csr_matrix
            Divergence operator of shape (n_nodes, n_edges).

        Notes
        -----
        For an edge-based vector field f (length n_edges),
        the divergence is -A^T @ f.
        """
        return -self._A.T.tocsr()

    def curl(self) -> csr_matrix:
        """
        Build 2D curl operator for a vector field.

        Returns
        -------
        scipy.sparse.csr_matrix
            Curl operator of shape (n_faces, n_edges), where n_faces
            is the number of grid cells (nx-1) * (ny-1).

        Notes
        -----
        The discrete curl maps an edge field to a face field. For each
        rectangular cell, the curl sums the edge values around the cell
        boundary (with orientation signs).

        For a grid cell with corners (x,y), (x+1,y), (x+1,y+1), (x,y+1):
        curl = bottom + right - top - left
        """
        nx, ny = self.nx, self.ny
        n_faces = (nx - 1) * (ny - 1)
        if n_faces == 0:
            return csr_matrix((0, self.n_edges))

        # Edge indices within the incidence matrix
        # Horizontal edges: row y, column x → index y*(nx-1) + x
        # Vertical edges:   row y, column x → n_edges_x + y*nx + x
        face_idx = np.arange(n_faces)
        fx = face_idx % (nx - 1)
        fy = face_idx // (nx - 1)

        bottom = fy * (nx - 1) + fx                          # horizontal, row y
        top = (fy + 1) * (nx - 1) + fx                       # horizontal, row y+1
        left = self.n_edges_x + fy * nx + fx                 # vertical, col x
        right = self.n_edges_x + fy * nx + (fx + 1)          # vertical, col x+1

        rows = np.tile(face_idx, 4)
        cols = np.concatenate([bottom, right, top, left])
        data = np.concatenate([
            np.ones(n_faces),      # bottom: +1
            np.ones(n_faces),      # right:  +1
            -np.ones(n_faces),     # top:    -1
            -np.ones(n_faces),     # left:   -1
        ])

        return csr_matrix((data, (rows, cols)), shape=(n_faces, self.n_edges))

    def laplacian(self, weights: NDArray[np.floating] | None = None) -> csr_matrix:
        """
        Build the discrete Laplacian operator.

        Computed as L = A^T diag(w) A where A is the incidence matrix
        and w are per-edge weights.

        Parameters
        ----------
        weights : np.ndarray, optional
            Per-edge weight vector of length n_edges. If None, unit
            weights are used (standard combinatorial Laplacian).

        Returns
        -------
        scipy.sparse.csr_matrix
            Laplacian operator of shape (n_nodes, n_nodes).

        Notes
        -----
        With unit weights, this produces the standard 5-point stencil
        for interior nodes: L[i,i] = degree(i), L[i,j] = -1 for
        adjacent nodes j.
        """
        A = self._A
        if weights is None:
            return (A.T @ A).tocsr()
        else:
            W = sp.diags(weights)
            return (A.T @ W @ A).tocsr()

    def hodge_star(self) -> csr_matrix:
        """
        Build the 2D Hodge star operator on node-based vector fields.

        The Hodge star rotates vectors by 90 degrees, equivalent to
        multiplication by the imaginary unit in the complex plane.

        Returns
        -------
        scipy.sparse.csr_matrix
            Hodge star operator of shape (2n, 2n).

        Notes
        -----
        For a node-based vector field [u; v] of length 2n,
        returns [-v; u].
        """
        n = self.size
        I = sp.eye(n, format='csr')
        Z = csr_matrix((n, n))
        return sp.bmat([[Z, -I], [I, Z]], format='csr')


# =============================================================================
# Physical Constants
# =============================================================================

MU0: float = 1.256637e-6
"""Permeability of free space (H/m)."""

def pathlap(N: int, periodic: bool = False) -> NDArray:
    """
    Create the graph Laplacian for a path or cycle graph.

    Parameters
    ----------
    N : int
        Number of nodes.
    periodic : bool, default False
        If True, creates a cycle graph (first and last nodes connected).
        If False, creates a path graph.

    Returns
    -------
    np.ndarray
        The Laplacian matrix of shape (N, N).

    Notes
    -----
    - For a path graph: L[i,i] = 2 for interior nodes, 1 for endpoints.
    - For a cycle graph: L[i,i] = 2 for all nodes.
    - Off-diagonal entries are -1 for adjacent nodes.
    """
    O = np.ones(N)
    L = sp.diags(
        [2 * O, -O[:1], -O[:1]],
        offsets=[0, 1, -1],
        shape=(N, N)
    ).toarray()

    if periodic:
        L[0, -1] = -1
        L[-1, 0] = -1
    else:
        L[0, 0] = 1
        L[-1, -1] = 1

    return L


def pathincidence(N: int, periodic: bool = False) -> NDArray:
    """
    Create the incidence matrix for a path or cycle graph.

    Parameters
    ----------
    N : int
        Number of nodes.
    periodic : bool, default False
        If True, creates a cycle graph incidence matrix.
        If False, creates a path graph incidence matrix.

    Returns
    -------
    np.ndarray
        The incidence matrix.

    Notes
    -----
    For a path graph: shape is (N, N-1) with N-1 edges.
    For a cycle graph: shape is (N, N) with N edges.
    Each column has +1 at source node and -1 at target node.
    """
    O = np.ones(N)
    B = sp.diags(
        [O, -O[:1]],
        offsets=[0, 1],
        shape=(N, N)
    ).toarray()

    if periodic:
        B[-1, 0] = -1

    return B


def normlap(
    L: NDArray | sp.spmatrix,
    return_scaling: bool = False
) -> NDArray | tuple[NDArray, sp.dia_matrix, sp.dia_matrix]:
    """
    Compute the normalized Laplacian of a matrix.

    The normalized Laplacian is defined as:
        L_norm = D^{-1/2} @ L @ D^{-1/2}

    where D is the diagonal matrix of L's diagonal entries.

    Parameters
    ----------
    L : np.ndarray or scipy.sparse matrix
        Input Laplacian matrix.
    return_scaling : bool, default False
        If True, also return the scaling matrices.

    Returns
    -------
    L_norm : np.ndarray
        The normalized Laplacian.
    D : scipy.sparse.dia_matrix, optional
        Diagonal scaling matrix (sqrt of original diagonal).
        Only returned if return_scaling=True.
    D_inv : scipy.sparse.dia_matrix, optional
        Inverse diagonal scaling matrix.
        Only returned if return_scaling=True.

    Notes
    -----
    The normalized Laplacian has eigenvalues in [0, 2] for
    undirected graphs and is useful for spectral clustering.
    """
    Yd = np.sqrt(L.diagonal())
    Di = sp.diags(1 / Yd)

    if return_scaling:
        D = sp.diags(Yd)
        return Di @ L @ Di, D, Di
    else:
        return Di @ L @ Di


def hermitify(A: NDArray | sp.spmatrix) -> NDArray:
    """
    Convert a complex symmetric matrix to Hermitian form.

    For a complex symmetric matrix (A = A^T), this function produces
    a Hermitian matrix by pairing the upper triangle's conjugate with
    the lower triangle.

    Parameters
    ----------
    A : np.ndarray or scipy.sparse matrix
        Input complex symmetric matrix.

    Returns
    -------
    np.ndarray
        The Hermitian form of the matrix.

    Notes
    -----
    Useful for converting admittance matrices to a form suitable
    for eigenvalue algorithms that require Hermitian input.
    """
    dense = A if isinstance(A, np.ndarray) else A.toarray()
    return (np.triu(dense).conjugate() + np.tril(dense)) / 2


def sorteig(vals: NDArray, vecs: NDArray) -> tuple[NDArray, NDArray]:
    """
    Sort an eigendecomposition by ascending eigenvalue.

    Eigensolvers such as :func:`scipy.sparse.linalg.eigsh` do not
    guarantee ordering; this reorders both the eigenvalues and the
    corresponding eigenvector columns.

    Parameters
    ----------
    vals : np.ndarray
        Eigenvalues, shape ``(k,)``.
    vecs : np.ndarray
        Eigenvectors as columns, shape ``(n, k)``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(vals, vecs)`` sorted by ascending eigenvalue.
    """
    order = np.argsort(vals)
    return vals[order], vecs[:, order]

