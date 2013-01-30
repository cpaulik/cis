"""
Custom CIS exceptions
"""

class CISError(Exception):
    pass

class InvalidPlotTypeError(CISError):
    pass

class InvalidDimensionError(CISError):
    pass

class InvalidVariableError(CISError):
    pass

class InconsistentDimensionsError(CISError):
    pass

class InvalidPlotFormatError(CISError):
    pass

class InvalidFileExtensionError(CISError):
    pass

class FileIOError(CISError):
    pass

class InvalidDataTypeError(CISError):
    pass

class InvalidColocationMethodError(CISError):
    pass

class InvalidLineStyleError(CISError):
    pass