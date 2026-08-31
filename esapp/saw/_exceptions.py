"""Custom exception classes for the SAW wrapper."""


# COM Error Hex Codes indicating RPC failures (SimAuto crash/unresponsive)
RPC_S_UNKNOWN_IF = 0x800706b5  # The interface is unknown
RPC_S_CALL_FAILED = 0x800706be # The remote procedure call failed

class Error(Exception):
    """
    Base class for exceptions in this module.
    
    All custom exceptions in the ESA++ library inherit from this class, allowing
    users to catch a single base exception type for all library-specific errors.
    """

    pass


class PowerWorldError(Error):
    """
    Raised when PowerWorld reports an error following a SimAuto call.
    This class can parse the error message to provide more context.

    This is the generic error class for SimAuto failures. If the error message
    indicates a specific known issue (like a missing prerequisite or a feature
    limitation), the `from_message` factory will return a more specific subclass.

    Attributes
    ----------
    message : str
        The descriptive error message from PowerWorld.
    source : str
        The source of the error (e.g., the specific SimAuto function called), if available.
    raw_message : str
        The original, unparsed error string.
    """

    def __init__(self, message: str):
        self.raw_message = message
        self.source = None
        self.message = message

        parts = message.split(":", 1)
        if len(parts) == 2:
            self.source = parts[0].strip()
            self.message = parts[1].strip()

        super().__init__(message)

    @staticmethod
    def from_message(message: str):
        """Factory method to create a specific PowerWorldError subclass."""
        lower_msg = message.lower()
        if "cannot be retrieved through simauto" in lower_msg:
            return SimAutoFeatureError(message)
        
        # Common prerequisite errors (missing data, setup, or invalid state)
        if (
            "no active" in lower_msg 
            or "not found" in lower_msg 
            or "could not be found" in lower_msg
            or "requires setup" in lower_msg
            or "is not online" in lower_msg
            or "at least one" in lower_msg
            or "no directions set" in lower_msg
            or "out-of-range" in lower_msg
            or "no available participation points" in lower_msg
        ):
            return PowerWorldPrerequisiteError(message)
            
        if "not registered" in lower_msg:
            return PowerWorldAddonError(message)
        # Add more specific error checks here as they are identified.
        return PowerWorldError(message)


class SimAutoFeatureError(PowerWorldError):
    """
    Raised when a specific SimAuto feature is not supported for the given
    object or in the current context (e.g., trying to read an object type
    that SimAuto doesn't allow reading).

    Nuance:
    Some PowerWorld objects (like `PWRegionSubGroupAux`) exist in the case but
    do not support retrieval via the `GetParameters` or `GetParamsRectTyped`
    SimAuto functions. This error distinguishes "data not found" from "data
    cannot be retrieved via this API."
    """
    pass


class PowerWorldPrerequisiteError(PowerWorldError):
    """
    Raised when a command fails because some prerequisite condition or
    data is not met in the case (e.g., no active contingencies for a
    contingency-related command).

    Nuance:
    Many PowerWorld script commands (as defined in the Auxiliary File Format)
    require specific data structures to be populated before execution. For example,
    `CTGSolve` requires defined contingencies, and `ATCDetermine` requires defined
    transfer directions. This error indicates a setup issue rather than a
    fundamental system failure.
    """
    pass


class PowerWorldAddonError(PowerWorldError):
    """
    Raised when a command fails because a required PowerWorld add-on
    (like TransLineCalc) is not registered or licensed.

    Nuance:
    Certain script commands (e.g., `CalculateRXBGFromLengthConfigCondType`,
    `Distributed Computing` commands) depend on optional add-ons. This error
    helps distinguish between a malformed command and a missing license feature.
    """
    pass


class COMError(Error):
    """
    Raised when attempting to call a SimAuto function results in an
    error.

    Nuance:
    This indicates a failure in the COM communication layer itself (e.g., the
    SimAuto server crashed, is unresponsive, or the function name is invalid),
    rather than a logical error returned by PowerWorld.
    """

    pass


# =============================================================================
# Application-level exceptions (consolidated from utils/exceptions.py)
# =============================================================================


class GridObjDNE(Error):
    """
    Raised when a grid object data query fails.

    This indicates the requested object does not exist in the case.
    """
    pass


class FieldDataException(Error):
    """Raised when there is an issue with field data retrieval or parsing."""
    pass


class AuxParseException(Error):
    """Raised when parsing an auxiliary file fails."""
    pass


class ContainerDeletedException(Error):
    """Raised when attempting to access a container that has been deleted."""
    pass


class PowerFlowException(Error):
    """
    Raised when a power flow solution error occurs.

    This is the base class for power flow related errors.
    """
    pass


class BifurcationException(PowerFlowException):
    """Raised when voltage bifurcation is suspected during power flow."""
    pass


class DivergenceException(PowerFlowException):
    """Raised when the power flow solution diverges."""
    pass


class GeneratorLimitException(PowerFlowException):
    """Raised when a generator has exceeded a limit during power flow."""
    pass


class GICException(Error):
    """Raised when a GIC (Geomagnetically Induced Current) analysis error occurs."""
    pass