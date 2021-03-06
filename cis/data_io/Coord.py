import numpy
from cis.data_io.hyperpoint import HyperPoint
from cis.data_io.hyperpoint_view import UngriddedHyperPointView
from cis.data_io.ungridded_data import LazyData
from cis.utils import fix_longitude_range


class Coord(LazyData):
    @classmethod
    def from_many_coordinates(cls, coords):
        """
        Create a single coordinate object from the concatenation of all of the coordinate objects in the input list,
        updating the shape as appropriate

        :param coords: A list of coordinate objects to be combined
        :return: A single :class:`Coord` object
        """
        from cis.utils import concatenate
        data = concatenate([ug.data for ug in coords])
        metadata = coords[0].metadata  # Use the first file as a master for the metadata...
        metadata.shape = data.shape  # But update the shape
        return cls(data, metadata, coords[0].axis)

    def __init__(self, data, metadata, axis=''):
        """

        :param data:
        :param metadata:
        :param axis: A string label for the axis, e.g. 'X', 'Y', 'Z', or 'T'
        :return:
        """
        super(Coord, self).__init__(data, metadata)
        self.axis = axis.upper()
        # Fix an issue where IRIS cannot parse units 'deg' (should be degrees).
        if self.units == 'deg':
            self.units = 'degrees'

    @property
    def points(self):
        """Alias for :func:`self.data`, to match :func:`iris.coords.Coord.points` interface

        :return: Coordinate data values
        """
        return self.data

    def __eq__(self, other):
        return other.metadata.standard_name == self.metadata.standard_name and self.metadata.standard_name != ''

    def convert_julian_to_std_time(self, calender='standard'):
        from cis.time_util import convert_julian_date_to_std_time_array, cis_standard_time_unit
        # if not self.units.startswith("Julian Date"):
        #     raise ValueError("Time units must be Julian Date for conversion to an Object")
        self._data = convert_julian_date_to_std_time_array(self.data, calender)
        self.units = str(cis_standard_time_unit)
        self.metadata.calendar = cis_standard_time_unit.calendar

    def convert_TAI_time_to_std_time(self, ref):
        from cis.time_util import convert_sec_since_to_std_time_array, cis_standard_time_unit
        self._data = convert_sec_since_to_std_time_array(self.data, ref)
        self.units = str(cis_standard_time_unit)
        self.metadata.calendar = cis_standard_time_unit.calendar

    def convert_to_std_time(self, time_stamp_info=None):
        """
        Convert this coordinate to standard time. It will use either: the units of the coordinate if it is in the
        standard 'x since y' format; or
        the first word of the units, combined with the time stamp (if the timestamp is not given an error is thrown).

        :param time_stamp_info: the time stamp info from the file, None if it does not exist
        """
        from cis.time_util import convert_time_since_to_std_time, cis_standard_time_unit, \
            convert_time_using_time_stamp_info_to_std_time

        if "since" in self.units:
            self._data = convert_time_since_to_std_time(self.data, self.units)
        else:
            if time_stamp_info is None:
                raise ValueError("File must have time stamp info if converting without 'since' in units definition")
            self._data = convert_time_using_time_stamp_info_to_std_time(self.data, self.units, time_stamp_info)

        self.units = str(cis_standard_time_unit)
        self.metadata.calendar = cis_standard_time_unit.calendar

    def convert_datetime_to_standard_time(self):
        from cis.time_util import convert_obj_to_standard_date_array, cis_standard_time_unit
        self._data = convert_obj_to_standard_date_array(self.data)
        self.units = str(cis_standard_time_unit)
        self.metadata.calendar = cis_standard_time_unit.calendar

    def set_longitude_range(self, range_start):
        """
        Confine the coordinate longitude range to 360 degrees from the :attr:`range_start` value.

        :param float range_start: Start of the longitude range
        """
        self._data = fix_longitude_range(self._data, range_start)
        self._data_flattened = None

    def copy(self):
        """
        Create a copy of this Coord object with new data so that that they can be modified without held references
        being affected. This will call any lazy loading methods in the coordinate data

        :return: Copied :class:`Coord`
        """
        data = numpy.ma.copy(self.data)  # Will call lazy load method
        return Coord(data, self.metadata)


class CoordList(list):
    """All the functionality of a standard :class:`list` with added :class:`Coord` context."""

    def __init__(self, *args):
        """ Given many :class:`Coord`s, return a :class:`CoordList` instance. """
        list.__init__(self, *args)

        # Check that all items in the incoming list are coords. Note that this checking
        # does not guarantee that a CoordList instance *always* has just coords in its list as
        # the append & __getitem__ methods have not been overridden.
        if not all([isinstance(coord, Coord) for coord in self]):
            raise ValueError('All items in list_of_coords must be Coord instances.')

    def append(self, other):
        """
        Safely add a new coordinate object to the list, this checks for a unique :attr:`axis` and :attr:`standard_name`.

        :param :class:`Coord` other: Other coord to add
        :raises DuplicateCoordinateError: If the coordinate is not unique in the list
        """
        from cis.exceptions import DuplicateCoordinateError
        if any([other == item for item in self]):
            raise DuplicateCoordinateError()
        super(CoordList, self).append(other)

    def get_coords(self, name=None, standard_name=None, long_name=None, attributes=None, axis=None):
        """
        Return a list of coordinates in this :class:`CoordList` fitting the given criteria. This is deliberately very
        similar to :func:`Cube.coords()` to maintain a similar interface and because the functionality is similar. There
        is no distinction between dimension coordinates and auxiliary coordinates here though.

        :param name:  The standard name or long name or default name of the desired coordinate.
         If None, does not check for name. Also see, :attr:`Cube.name`.
        :type name: string or None
        :param standard_name: The CF standard name of the desired coordinate. If None, does not check for standard name.
        :type standard_name: string or None
        :param long_name: An unconstrained description of the coordinate. If None, does not check for long_name.
        :type long_name: string or None
        :param attributes: A dictionary of attributes desired on the coordinates. If None, does not check for attributes
        :type attributes: dict or None
        :param axis: The desired coordinate axis, see :func:`iris.util.guess_coord_axis`. If None, does not check for
         axis. Accepts the values 'X', 'Y', 'Z' and 'T' (case-insensitive).
        :type axis: string or None

        :return: A :class:`CoordList` of coordinates fitting the given criteria
        """
        from collections import Mapping
        coords = self

        if name is not None:
            coords = filter(lambda coord_: coord_.name() == name, coords)

        if standard_name is not None:
            coords = filter(lambda coord_: coord_.standard_name == standard_name, coords)

        if long_name is not None:
            coords = filter(lambda coord_: coord_.long_name == long_name, coords)

        if axis is not None:
            axis = axis.upper()
            coords = filter(lambda coord_: coord_.axis == axis, coords)

        if attributes is not None:
            if not isinstance(attributes, Mapping):
                raise ValueError(
                    'The attributes keyword was expecting a dictionary type, but got a %s instead.' % type(attributes))
            coords = filter(lambda coord_: all(
                            k in coord_.attributes and coord_.attributes[k] == v for k, v in attributes.iteritems()),
                            coords)

        return coords

    def get_coord(self, name=None, standard_name=None, long_name=None, attributes=None, axis=None):
        """
        Return a single coord fitting the given criteria. This is deliberately very
        similar to :func:`Cube.coord()` method to maintain a similar interface and because the functionality is similar.
        There is no distinction between dimension coordinates and auxilliary coordinates here though.

        :param name:  The standard name or long name or default name of the desired coordinate.
         If None, does not check for name. Also see, :attr:`Cube.name`.
        :type name: string or None
        :param standard_name: The CF standard name of the desired coordinate. If None, does not check for standard name.
        :type standard_name: string or None
        :param long_name: An unconstrained description of the coordinate. If None, does not check for long_name.
        :type long_name: string or None
        :param attributes: A dictionary of attributes desired on the coordinates. If None, does not check for attributes
        :type attributes: dict or None
        :param axis: The desired coordinate axis, see :func:`iris.util.guess_coord_axis`. If None, does not check for
         axis. Accepts the values 'X', 'Y', 'Z' and 'T' (case-insensitive).
        :type axis: string or None

        :raises CoordinateNotFoundError: If the arguments given do not result in precisely
         1 coordinate being matched.
        :return: A single :class:`Coord`.

        """
        from cis.exceptions import CoordinateNotFoundError
        coords = self.get_coords(name=name, standard_name=standard_name, long_name=long_name, attributes=attributes,
                                 axis=axis)
        if len(coords) == 0:  # If we found none by name, try with standard name only
            coords = self.get_coords(standard_name=name)

        if len(coords) > 1:
            msg = 'Expected to find exactly 1 coordinate, but found %s. They were: %s.' \
                  % (len(coords), ', '.join(coord.name() for coord in coords))
            raise CoordinateNotFoundError(msg)
        elif len(coords) == 0:
            bad_name = name or standard_name or long_name or axis or ''
            msg = 'Expected to find exactly 1 %s coordinate, but found none.' % bad_name
            raise CoordinateNotFoundError(msg)

        return coords[0]

    def get_coordinates_points(self):
        all_coords = self.find_standard_coords()
        flattened_coords = [(c.data_flattened if c is not None else None) for c in all_coords]
        return UngriddedHyperPointView(flattened_coords, None)

    def get_standard_coords(self, data_len):
        """Constructs a list of the standard coordinate values.
        The standard coordinates are latitude, longitude, altitude, time and air_pressure; they occur in the return
        list in this order. If a standard coordinate has not been found it's values are returned as a list of length
        :attr:`data_len`.

        :param int data_len: Expected length of coordinate data
        :return: :class:`list` of indexed sequences of coordinate values
        """
        from cis.exceptions import CoordinateNotFoundError

        empty_data = [None for i in xrange(data_len)]
        ret_list = []

        for name in HyperPoint.standard_names:
            try:
                coord = self.get_coord(standard_name=name).data.flatten()
            except CoordinateNotFoundError:
                coord = empty_data
            ret_list.append(coord)

        return ret_list

    def find_standard_coords(self):
        """Constructs a list of the standard coordinates.
        The standard coordinates are latitude, longitude, altitude, air_pressure and time; they occur in the return
        list in this order.

        :return: :class:`list` of coordinates or None if coordinate not present
        """
        from cis.exceptions import CoordinateNotFoundError

        ret_list = []

        for name in HyperPoint.standard_names:
            try:
                coord = self.get_coord(standard_name=name)
            except CoordinateNotFoundError:
                coord = None
            ret_list.append(coord)

        return ret_list

    def copy(self):
        """
        Create a copy of this CoordList object with new data so that that they can
        be modified without held references being affected. This will call any lazy loading methods in the coordinate
        data

        :return: Copied :class:`CoordList`
        """
        copied = CoordList()
        for coord in self:
            copied.append(coord.copy())
        return copied
