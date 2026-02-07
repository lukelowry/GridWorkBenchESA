import os
import re
from pathlib import Path
from typing import Union

import numpy as np
from scipy.sparse import csr_matrix

from ._enums import YesNo, JacobianForm
from ._helpers import get_temp_filepath


class MatrixMixin:

    def get_ybus(self, full: bool = False, file: Union[str, None] = None) -> Union[np.ndarray, csr_matrix]:
        """Obtain the YBus matrix from PowerWorld.

        This method calls the `SaveYbusInMatlabFormat` script command to write
        the YBus matrix to a temporary file, then parses that file to construct
        the matrix in Python.

        Parameters
        ----------
        full : bool, optional
            If True, returns a dense NumPy array. If False (default), returns a
            SciPy CSR sparse matrix.
        file : Union[str, None], optional
            Optional path to a pre-existing `.mat` file containing the YBus matrix.
            If provided, the file will be parsed directly instead of calling SimAuto
            to generate a new one. Defaults to None.

        Returns
        -------
        Union[numpy.ndarray, scipy.sparse.csr_matrix]
            The YBus matrix as either a dense NumPy array or a SciPy CSR sparse matrix.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails or the generated file cannot be parsed.
        """
        if file:
            _tempfile_path = file
            _cleanup = False
        else:
            _tempfile_path = get_temp_filepath(".mat")
            self._run_script("SaveYbusInMatlabFormat", f'"{_tempfile_path}"', YesNo.NO)
            _cleanup = True
        try:
            with open(_tempfile_path, "r") as f:
                f.readline()
                mat_str = f.read()
            mat_str = re.sub(r"\s", "", mat_str)
            lines = re.split(";", mat_str)
            ie = r"[0-9]+"
            fe = r"-*[0-9]+\.[0-9]+"
            dr = re.compile(r"(?:Ybus)=(?:sparse\()({ie})".format(ie=ie))
            exp = re.compile(r"(?:Ybus\()({ie}),({ie})(?:\)=)({fe})(?:\+j\*)(?:\()({fe})".format(ie=ie, fe=fe))
            dim = dr.match(lines[0])[1]
            n = int(dim)
            row, col, data = [], [], []
            for line in lines[1:]:
                match = exp.match(line)
                if match is None:
                    continue
                idx1, idx2, real, imag = match.groups()
                admittance = float(real) + 1j * float(imag)
                row.append(int(idx1))
                col.append(int(idx2))
                data.append(admittance)

            sparse_matrix = csr_matrix(
                (data, (np.asarray(row) - 1, np.asarray(col) - 1)),
                shape=(n, n),
                dtype=complex,
            )
            return sparse_matrix.toarray() if full else sparse_matrix
        finally:
            if _cleanup:
                os.unlink(_tempfile_path)

    def get_gmatrix(self, full: bool = False) -> Union[np.ndarray, csr_matrix]:
        """Get the GIC conductance matrix (G).

        This method calls the `GICSaveGMatrix` script command to write the G-matrix
        to a temporary file, then parses that file to construct the matrix in Python.
        The G-matrix relates GIC currents to earth potentials.

        Parameters
        ----------
        full : bool, optional
            If True, returns a dense NumPy array. If False (default), returns a
            SciPy CSR sparse matrix.

        Returns
        -------
        Union[numpy.ndarray, scipy.sparse.csr_matrix]
            The G-matrix as either a dense NumPy array or a SciPy CSR sparse matrix.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails or the generated file cannot be parsed.
        FileNotFoundError
            If the temporary matrix file is not created.
        """
        g_matrix_path, id_file_path = self._make_temp_matrix_files()
        try:
            # Double call is intentional — PW sometimes requires it for GMatrix.
            self._run_script("GICSaveGMatrix", f'"{g_matrix_path}"', f'"{id_file_path}"')
            self._run_script("GICSaveGMatrix", f'"{g_matrix_path}"', f'"{id_file_path}"')
            with open(g_matrix_path, "r") as f:
                mat_str = f.read()
            sparse_matrix = self._parse_real_matrix(mat_str, "GMatrix")
            return sparse_matrix.toarray() if full else sparse_matrix
        finally:
            os.unlink(g_matrix_path)
            os.unlink(id_file_path)

    def get_gmatrix_with_ids(self, full: bool = False):
        """Get the GIC conductance matrix (G) along with the node ID mapping.

        This method returns both the G-matrix and a list of node identifiers
        that describe what each row/column represents (substations and buses).

        Parameters
        ----------
        full : bool, optional
            If True, returns a dense NumPy array. If False (default), returns a
            SciPy CSR sparse matrix.

        Returns
        -------
        tuple
            A tuple of (G_matrix, node_ids) where:
            - G_matrix: The G-matrix as either dense array or sparse CSR matrix
            - node_ids: List of strings describing each node (e.g., "Sub 1", "Bus 101")
        """
        g_matrix_path, id_file_path = self._make_temp_matrix_files()
        try:
            # Double call is intentional — PW sometimes requires it for GMatrix.
            self._run_script("GICSaveGMatrix", f'"{g_matrix_path}"', f'"{id_file_path}"')
            self._run_script("GICSaveGMatrix", f'"{g_matrix_path}"', f'"{id_file_path}"')

            with open(g_matrix_path, "r") as f:
                mat_str = f.read()
            sparse_matrix = self._parse_real_matrix(mat_str, "GMatrix")

            with open(id_file_path, "r") as f:
                id_content = f.read()

            # Parse the ID file - format: "ObjectType, Number, Row/Col, Name"
            # First line is header, skip it
            node_ids = []
            lines = id_content.strip().split('\n')
            for line in lines[1:]:  # Skip header line
                line = line.strip()
                if not line:
                    continue
                # Split by comma
                parts = [p.strip() for p in line.split(',')]
                # Format: ObjectType, Number, Row/Col, Name - Name is 4th field (index 3)
                if len(parts) >= 4:
                    node_ids.append(parts[3])  # Name is 4th field
                elif len(parts) >= 3:
                    node_ids.append(parts[2])  # Fallback to 3rd field
                elif len(parts) >= 2:
                    node_ids.append(parts[1])  # Fallback to 2nd field
                else:
                    node_ids.append(line)

            matrix = sparse_matrix.toarray() if full else sparse_matrix
            return matrix, node_ids
        finally:
            os.unlink(g_matrix_path)
            os.unlink(id_file_path)

    def get_jacobian(self, full: bool = False, form: Union[JacobianForm, str] = JacobianForm.RECTANGULAR) -> Union[np.ndarray, csr_matrix]:
        """Get the power flow Jacobian matrix.

        This method calls the `SaveJacobian` script command to write the Jacobian
        matrix to a temporary file, then parses that file to construct the matrix
        in Python. The Jacobian is crucial for Newton-Raphson power flow solutions
        and sensitivity analysis.

        Parameters
        ----------
        full : bool, optional
            If True, returns a dense NumPy array. If False (default), returns a
            SciPy CSR sparse matrix.
        form : Union[JacobianForm, str], optional
            Jacobian coordinate form. Defaults to JacobianForm.RECTANGULAR.

        Returns
        -------
        Union[numpy.ndarray, scipy.sparse.csr_matrix]
            The Jacobian matrix as either a dense NumPy array or a SciPy CSR sparse matrix.

        Raises
        ------
        PowerWorldError
            If the SimAuto call fails or the generated file cannot be parsed.
        FileNotFoundError
            If the temporary matrix file is not created.
        """
        f = form.value if isinstance(form, JacobianForm) else form
        jac_file_path, id_file_path = self._make_temp_matrix_files()
        try:
            self._run_script("SaveJacobian", f'"{jac_file_path}"', f'"{id_file_path}"', "M", f)
            with open(jac_file_path, "r") as f:
                mat_str = f.read()
            sparse_matrix = self._parse_real_matrix(mat_str, "Jac")
            return sparse_matrix.toarray() if full else sparse_matrix
        finally:
            os.unlink(jac_file_path)
            os.unlink(id_file_path)

    def get_jacobian_with_ids(self, full: bool = False, form: Union[JacobianForm, str] = JacobianForm.RECTANGULAR):
        """Get the power flow Jacobian matrix along with row/column ID mapping.

        Returns both the Jacobian matrix and a list of identifiers describing
        what each row/column represents (equation type and bus number,
        e.g. ``'dP 101'``, ``'dQ 102'``).

        Parameters
        ----------
        full : bool, optional
            If True, returns a dense NumPy array. If False (default), returns a
            SciPy CSR sparse matrix.
        form : Union[JacobianForm, str], optional
            Jacobian coordinate form. Defaults to JacobianForm.RECTANGULAR.

        Returns
        -------
        tuple
            A tuple of (jacobian_matrix, row_ids) where:
            - jacobian_matrix: The Jacobian as either dense array or sparse CSR matrix
            - row_ids: List of strings describing each row/column
        """
        f = form.value if isinstance(form, JacobianForm) else form
        jac_file_path, id_file_path = self._make_temp_matrix_files()
        try:
            self._run_script("SaveJacobian", f'"{jac_file_path}"', f'"{id_file_path}"', "M", f)

            with open(jac_file_path, "r") as f:
                mat_str = f.read()
            sparse_matrix = self._parse_real_matrix(mat_str, "Jac")

            with open(id_file_path, "r") as f:
                id_content = f.read()

            # Jacobian ID file: one label per line, no header.
            # Each line is an equation label like "dP 101" or "'dP 101'".
            row_ids = []
            for line in id_content.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                row_ids.append(line)

            matrix = sparse_matrix.toarray() if full else sparse_matrix
            return matrix, row_ids
        finally:
            os.unlink(jac_file_path)
            os.unlink(id_file_path)

    def _make_temp_matrix_files(self):
        """Internal helper to create temporary files for matrix export.

        These files are used by SimAuto to write matrix data, which is then
        read back into Python.

        Returns
        -------
        Tuple[str, str]
            A tuple containing the paths to the temporary matrix file and ID file.
        """
        mat_file_path = get_temp_filepath(".m")
        id_file_path = get_temp_filepath(".txt")
        return mat_file_path, id_file_path

    def _parse_real_matrix(self, mat_str, matrix_name="Jac"):
        """Internal helper to parse a real-valued sparse matrix from PowerWorld's '.m' output format.

        This function extracts matrix dimensions and non-zero elements from the
        MATLAB-like string output by SimAuto's matrix export functions.

        Parameters
        ----------
        mat_str : str
            The string content of the `.m` file containing the sparse matrix definition.
        matrix_name : str, optional
            The name of the matrix variable in the `.m` file (e.g., "Jac", "GMatrix").
            Defaults to "Jac".

        Returns
        -------
        scipy.sparse.csr_matrix
            The parsed sparse matrix in CSR format.
        """
        mat_str = re.sub(r"\s", "", mat_str)
        lines = re.split(";", mat_str)
        ie = r"[0-9]+"
        fe = r"-*[0-9]+\.[0-9]+"
        dr = re.compile(r"(?:{matrix_name})=(?:sparse\()({ie})".format(ie=ie, matrix_name=matrix_name))
        exp = re.compile(r"(?:{matrix_name}\()({ie}),({ie})(?:\)=)({fe})".format(ie=ie, fe=fe, matrix_name=matrix_name))
        dim = dr.match(lines[0])[1]
        n = int(dim)
        row, col, data = [], [], []
        for line in lines[1:]:
            match = exp.match(line)
            if match is None:
                continue
            idx1, idx2, real = match.groups()
            row.append(int(idx1))
            col.append(int(idx2))
            data.append(float(real))
        return csr_matrix((data, (np.asarray(row) - 1, np.asarray(col) - 1)), shape=(n, n))

    def SaveJacobian(self, jac_filename: str, jid_filename: str, file_type: str = "M", jac_form: Union[JacobianForm, str] = JacobianForm.RECTANGULAR):
        """Saves the Jacobian Matrix to a text file or a file formatted for use with Matlab.

        Parameters
        ----------
        jac_filename : str
            File in which to save the Jacobian.
        jid_filename : str
            File to save a description of what each row and column of the Jacobian represents.
        file_type : str, optional
            "M" for Matlab form, "TXT" for text file, "EXPM" for Matlab exponential form. Defaults to "M".
        jac_form : Union[JacobianForm, str], optional
            Jacobian coordinate form. Defaults to JacobianForm.RECTANGULAR.
        """
        f = jac_form.value if isinstance(jac_form, JacobianForm) else jac_form
        return self._run_script("SaveJacobian", f'"{jac_filename}"', f'"{jid_filename}"', file_type, f)

    def SaveYbusInMatlabFormat(self, filename: str, include_voltages: bool = False):
        """Saves the YBus to a file formatted for use with Matlab."""
        iv = YesNo.from_bool(include_voltages)
        return self._run_script("SaveYbusInMatlabFormat", f'"{filename}"', iv)
