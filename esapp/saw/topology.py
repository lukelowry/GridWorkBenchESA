import os
from pathlib import Path
from typing import Union
import pandas as pd

from ._enums import (
    YesNo, format_filter,
    BranchDistanceMeasure as _BranchDistanceMeasure,
    BranchFilterMode, FileFormat,
)
from ._helpers import format_list, get_temp_filepath


class TopologyMixin:

    def DeterminePathDistance(
        self,
        start: str,
        BranchDistMeas: Union[_BranchDistanceMeasure, str] = _BranchDistanceMeasure.REACTANCE,
        BranchFilter: Union[BranchFilterMode, str] = BranchFilterMode.ALL,
        BusField="CustomFloat:1",
    ) -> pd.DataFrame:
        """
        Calculate a distance measure at each bus from a starting location.

        Computes how far each bus is from the specified starting group using
        the chosen distance measure (impedance, length, or nodes). Results
        are stored in a bus field. Buses in the start group have distance 0,
        unreachable buses have distance -1.

        This is a wrapper for the ``DeterminePathDistance`` script command.

        Parameters
        ----------
        start : str
            The starting location. Can be a Bus, Area, Zone, SuperArea,
            Substation, or Injection Group. Examples: '[BUS 1]',
            '[Area "East"]', '[InjectionGroup "Source"]'.
        BranchDistMeas : str, optional
            Distance measure to use. Options: "X" (series reactance),
            "Z" (impedance magnitude sqrt(R^2+X^2)), "Length", "Nodes"
            (count branches), "FixedNumBus", "SuperBus", or any branch
            field variable name. Defaults to "X".
        BranchFilter : str, optional
            Filter for branches that can be traversed. Options: "ALL",
            "SELECTED", "CLOSED", or a filter name. Defaults to "ALL".
        BusField : str, optional
            Bus field to store the distance results. Defaults to "CustomFloat:1".

        Returns
        -------
        pd.DataFrame
            DataFrame containing BusNum and the calculated distance.
        """
        self._run_script("DeterminePathDistance", start, BranchDistMeas, BranchFilter, BusField)

    def DetermineBranchesThatCreateIslands(
        self, Filter: Union[BranchFilterMode, str] = BranchFilterMode.ALL, StoreBuses: bool = True, SetSelectedOnLines: bool = False
    ) -> pd.DataFrame:
        """
        Determine which branches, if opened, would create electrical islands.

        Evaluates each branch to check if its removal causes part of the
        system to become electrically isolated. Useful for identifying
        critical transmission lines.

        This is a wrapper for the ``DetermineBranchesThatCreateIslands`` script command.

        Parameters
        ----------
        Filter : str, optional
            Which branches to check. Options: "ALL", "SELECTED", "AREAZONE",
            or a filter name. Defaults to "ALL".
        StoreBuses : bool, optional
            If True, stores the buses in each island to the output.
            Defaults to True.
        SetSelectedOnLines : bool, optional
            If True, sets the Selected field to YES for branches that
            create islands. Note: this overwrites existing Selected values.
            Defaults to False.

        Returns
        -------
        pd.DataFrame
            DataFrame with branch/bus pairs showing which buses would be
            islanded by each critical branch.

        Raises
        ------
        PowerWorldError
            If the command fails to execute.
        """
        filename = get_temp_filepath(".csv")

        sb = YesNo.from_bool(StoreBuses)
        ssl = YesNo.from_bool(SetSelectedOnLines)
        try:
            self._run_script("DetermineBranchesThatCreateIslands", Filter, sb, f'"{filename}"', ssl, FileFormat.CSV)
            return pd.read_csv(filename, header=0)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def DetermineShortestPath(
        self, start: str, end: str, BranchDistanceMeasure: Union[_BranchDistanceMeasure, str] = _BranchDistanceMeasure.REACTANCE, BranchFilter: Union[BranchFilterMode, str] = BranchFilterMode.ALL
    ) -> pd.DataFrame:
        """
        Calculate the shortest path between two network locations.

        Computes the lowest-impedance (or other measure) path between a
        starting location and an ending location. Returns the buses along
        the path with cumulative distance from the end to the start.

        This is a wrapper for the ``DetermineShortestPath`` script command.

        Parameters
        ----------
        start : str
            The starting location. Same format as DeterminePathDistance:
            '[BUS 1]', '[Area "East"]', etc.
        end : str
            The ending location. Same format as start.
        BranchDistanceMeasure : str, optional
            Distance measure to use. Options: "X", "Z", "Length", "Nodes",
            or any branch field variable name. Defaults to "X".
        BranchFilter : str, optional
            Filter for branches that can be traversed. Options: "ALL",
            "SELECTED", "CLOSED", or a filter name. Defaults to "ALL".

        Returns
        -------
        pd.DataFrame
            DataFrame with columns [BusNum, distance_measure, BusName]
            listing the path from end to start with cumulative distances.

        Raises
        ------
        PowerWorldError
            If the command fails or no path exists.
        """
        filename = get_temp_filepath(".txt")

        try:
            self._run_script("DetermineShortestPath", start, end, BranchDistanceMeasure, BranchFilter, f'"{filename}"')
            df = pd.read_csv(
                filename, header=None, sep=r'\s+', names=["BusNum", BranchDistanceMeasure, "BusName"]
            )
            df["BusNum"] = df["BusNum"].astype(int)
            return df
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def DoFacilityAnalysis(self, filename: str, set_selected: bool = False):
        """
        Find the minimum cut to isolate a Facility from an External region.

        Identifies the minimum number of branches that need to be opened to
        isolate the Facility (power system device) from the External region.
        The Facility and External regions must be defined beforehand using
        the Select Bus Dialog or other automation means.

        This is a wrapper for the ``DoFacilityAnalysis`` script command.

        Parameters
        ----------
        filename : str
            Auxiliary file path to write the results. Output includes
            buses forming each isolating path and the branches in the
            minimum cut.
        set_selected : bool, optional
            If True, sets the Selected field to YES for branches in the
            minimum cut. Defaults to False.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        yn = YesNo.from_bool(set_selected)
        return self._run_script("DoFacilityAnalysis", f'"{filename}"', yn)

    def FindRadialBusPaths(
        self,
        ignore_status: bool = False,
        treat_parallel_as_not_radial: bool = False,
        bus_or_superbus: str = "BUS",
    ):
        """
        Identify radial (dead-end) bus paths in the network.

        Scans the network for series of buses that end in a dead-end (radial
        path) and populates the following fields for involved buses and
        branches: Radial Path End Number, Radial Path Index, Radial Path Length.

        This is a wrapper for the ``FindRadialBusPaths`` script command.

        Parameters
        ----------
        ignore_status : bool, optional
            If True, ignores element status when traversing branches.
            Defaults to False.
        treat_parallel_as_not_radial : bool, optional
            If True, treats parallel branches as not radial when traversing.
            Defaults to False.
        bus_or_superbus : str, optional
            Grouping level for traversal. "BUS" or "SUPERBUS". When using
            "SUPERBUS", branches within the same superbus have blank results.
            Defaults to "BUS".

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        ign = YesNo.from_bool(ignore_status)
        treat = YesNo.from_bool(treat_parallel_as_not_radial)
        return self._run_script("FindRadialBusPaths", ign, treat, bus_or_superbus)

    def SetBusFieldFromClosest(self, variable_name: str, bus_filter_set_to: str, bus_filter_from_these: str, branch_filter_traverse: str, branch_dist_meas: str):
        """
        Copy a bus field value from the electrically closest bus.

        For buses matching bus_filter_set_to, sets their field value equal
        to the value from the closest bus that matches bus_filter_from_these,
        where "closest" is determined by traversing branches according to
        the specified distance measure.

        This is a wrapper for the ``SetBusFieldFromClosest`` script command.

        Parameters
        ----------
        variable_name : str
            The bus field to set (and copy from the closest bus).
        bus_filter_set_to : str
            Filter specifying which buses should have their field overwritten.
        bus_filter_from_these : str
            Filter specifying which buses can be used as sources.
        branch_filter_traverse : str
            Filter for branches that can be traversed. Options: "ALL",
            "SELECTED", "CLOSED", or a filter name.
        branch_dist_meas : str
            Distance measure: "X", "Z", "Length", "Nodes", "FixedNumBus",
            "SuperBus", or a branch field variable name.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("SetBusFieldFromClosest", f'"{variable_name}"', f'"{bus_filter_set_to}"', f'"{bus_filter_from_these}"', branch_filter_traverse, branch_dist_meas)

    def SetSelectedFromNetworkCut(
        self,
        set_how: bool,
        bus_on_cut_side: str,
        branch_filter: str = "",
        interface_filter: str = "",
        dc_line_filter: str = "",
        energized: bool = True,
        num_tiers: int = 0,
        initialize_selected: bool = True,
        objects_to_select: list = None,
        use_area_zone: bool = False,
        use_kv: bool = False,
        min_kv: float = 0.0,
        max_kv: float = 9999.0,
        lower_min_kv: float = 0.0,
        lower_max_kv: float = 9999.0,
    ):
        """
        Set the Selected field of specified object types if they are on the specified side of a network cut.

        Parameters
        ----------
        set_how : bool
            How to set the field (True for YES, False for NO).
        bus_on_cut_side : str
            Identifier for a bus on the desired side.
        branch_filter : str, optional
            Filter for branches defining the cut.
        interface_filter : str, optional
            Filter for interfaces defining the cut.
        dc_line_filter : str, optional
            Filter for DC lines defining the cut.
        energized : bool, optional
            If True, only considers energized elements. Defaults to True.
        num_tiers : int, optional
            Number of tiers to traverse. Defaults to 0.
        initialize_selected : bool, optional
            If True, initializes Selected field before setting. Defaults to True.
        objects_to_select : list, optional
            List of object types to select.
        use_area_zone : bool, optional
            If True, uses Area/Zone filters. Defaults to False.
        use_kv : bool, optional
            If True, uses kV limits. Defaults to False.
        min_kv : float, optional
            Minimum kV. Defaults to 0.0.
        max_kv : float, optional
            Maximum kV. Defaults to 9999.0.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        sh = YesNo.from_bool(set_how)
        en = YesNo.from_bool(energized)
        init = YesNo.from_bool(initialize_selected)
        uaz = YesNo.from_bool(use_area_zone)
        ukv = YesNo.from_bool(use_kv)

        objs = format_list(objects_to_select) if objects_to_select else ""

        bf = format_filter(branch_filter)
        inf = format_filter(interface_filter)
        dcf = format_filter(dc_line_filter)

        return self._run_script("SetSelectedFromNetworkCut", sh, bus_on_cut_side, bf, inf, dcf, en, num_tiers, init, objs, uaz, ukv, min_kv, max_kv, lower_min_kv, lower_max_kv)

    def CreateNewAreasFromIslands(self):
        """
        Create permanent areas matching the temporary islands from power flow.

        Creates permanent area definitions that match the areas Simulator
        creates temporarily while solving the power flow. New areas are
        created if an area is on AGC, spans multiple viable islands, and
        only one of those islands has more than one area in it.

        This is a wrapper for the ``CreateNewAreasFromIslands`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        return self._run_script("CreateNewAreasFromIslands")

    def ExpandAllBusTopology(self):
        """
        Expand the topology model around all buses.

        Expands the topology representation for all buses in the model,
        showing breaker-level detail where available.

        This is a wrapper for the ``ExpandAllBusTopology`` script command.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        See Also
        --------
        ExpandBusTopology : Expand topology for a specific bus.
        """
        return self._run_script("ExpandAllBusTopology")

    def ExpandBusTopology(self, bus_identifier: str, topology_type: str):
        """
        Expand the topology model around a specific bus.

        Expands the topology representation for a specific bus to show
        breaker-level detail according to the specified topology type.

        This is a wrapper for the ``ExpandBusTopology`` script command.

        Parameters
        ----------
        bus_identifier : str
            The bus to expand, e.g., "BUS 1" or a bus number.
        topology_type : str
            The type of topology expansion (e.g., "BREAKERANDAHALF").

        Returns
        -------
        str
            The response from the PowerWorld script command.

        See Also
        --------
        ExpandAllBusTopology : Expand topology for all buses.
        """
        return self._run_script("ExpandBusTopology", bus_identifier, topology_type)

    def SaveConsolidatedCase(self, filename: str, filetype: Union[FileFormat, str] = FileFormat.PWB, bus_format: str = "Number", truncate_ctg_labels: bool = False, add_comments: bool = False):
        """
        Save the full topology model as a consolidated case file.

        Exports the complete topology model (including breaker-level detail)
        into a single consolidated case file.

        This is a wrapper for the ``SaveConsolidatedCase`` script command.

        Parameters
        ----------
        filename : str
            The file path to save the consolidated case.
        filetype : str, optional
            Output file format: "PWB" or "AUX". Defaults to "PWB".
        bus_format : str, optional
            How to identify buses: "Number" or "Name". Defaults to "Number".
        truncate_ctg_labels : bool, optional
            If True, truncates contingency labels. Defaults to False.
        add_comments : bool, optional
            If True, adds comments for object labels. Defaults to False.

        Returns
        -------
        str
            The response from the PowerWorld script command.
        """
        tcl = YesNo.from_bool(truncate_ctg_labels)
        ac = YesNo.from_bool(add_comments)
        return self._run_script("SaveConsolidatedCase", f'"{filename}"', filetype, f'[{bus_format}, {tcl}, {ac}]')

    def CloseWithBreakers(self, object_type: str, filter_val: str, only_specified: bool = False, switching_types: list = None, close_normally_closed: bool = False):
        """
        Energize objects by closing associated breakers.

        Closes the breakers (or other switching devices) required to energize
        the specified objects. This is used when working with breaker-level
        topology models.

        This is a wrapper for the ``CloseWithBreakers`` script command.

        Parameters
        ----------
        object_type : str
            The type of object to energize (e.g., "GEN", "BRANCH", "LOAD").
        filter_val : str
            Filter name or object identifier (e.g., "[1 1]" for Gen at bus 1).
        only_specified : bool, optional
            If True, only closes breakers directly associated with the
            specified object, not all breakers needed for energization.
            Defaults to False.
        switching_types : list, optional
            List of switching device types to close, e.g.,
            ["Breaker", "Load Break Disconnect"]. Defaults to ["Breaker"].
        close_normally_closed : bool, optional
            If True, also closes normally-closed disconnects.
            Defaults to False.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        See Also
        --------
        OpenWithBreakers : Disconnect objects by opening breakers.
        """
        only = YesNo.from_bool(only_specified)
        cnc = YesNo.from_bool(close_normally_closed)
        sw_types = format_list(switching_types, quote_items=True) if switching_types else '["Breaker"]'

        # This command has a unique syntax where the object type is the first argument
        # and the second argument is an identifier with keys *only*, not the full object string.
        # This block handles cases where a full object string (e.g., from create_object_string)
        # is passed as filter_val.
        processed_val = filter_val
        prefix_to_check = f"[{object_type.upper()} "
        if filter_val.strip().upper().startswith(prefix_to_check):
            # It's a full object string, extract just the keys part.
            keys_part = filter_val.strip()[len(prefix_to_check):-1].strip()
            processed_val = f"[{keys_part}]"

        return self._run_script("CloseWithBreakers", object_type, processed_val, only, sw_types, cnc)

    def OpenWithBreakers(self, object_type: str, filter_val: str, switching_types: list = None, open_normally_open: bool = False):
        """
        Disconnect objects by opening associated breakers.

        Opens the breakers (or other switching devices) to disconnect the
        specified objects from the network. This is used when working with
        breaker-level topology models.

        This is a wrapper for the ``OpenWithBreakers`` script command.

        Parameters
        ----------
        object_type : str
            The type of object to disconnect (e.g., "GEN", "BRANCH", "LOAD").
        filter_val : str
            Filter name or object identifier (e.g., "[1 2 1]" for Branch).
        switching_types : list, optional
            List of switching device types to open, e.g., ["Breaker"].
            Defaults to ["Breaker"].
        open_normally_open : bool, optional
            If True, also opens normally-open disconnects.
            Defaults to False.

        Returns
        -------
        str
            The response from the PowerWorld script command.

        See Also
        --------
        CloseWithBreakers : Energize objects by closing breakers.
        """
        ono = YesNo.from_bool(open_normally_open)
        sw_types = format_list(switching_types, quote_items=True) if switching_types else '["Breaker"]'

        # This command has a unique syntax where the object type is the first argument
        # and the second argument is an identifier with keys *only*, not the full object string.
        # This block handles cases where a full object string (e.g., from create_object_string)
        # is passed as filter_val.
        processed_val = filter_val
        prefix_to_check = f"[{object_type.upper()} "
        if filter_val.strip().upper().startswith(prefix_to_check):
            keys_part = filter_val.strip()[len(prefix_to_check):-1].strip()
            processed_val = f"[{keys_part}]"

        return self._run_script("OpenWithBreakers", object_type, processed_val, sw_types, ono)
