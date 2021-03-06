# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""dateutil and datetime with portable timezone support.

This module supports round-trip conversions between strings, datetime objects
and timestamps:

         => ParseDateTime =>           => GetTimeSTampFromDateTime =>
  string                      datetime                                timestamp
         <= FormatDateTime <=          <= GetDateTimeFromTimeStamp <=

GetTimeZone(str) returns the tzinfo object for a timezone name. It handles
abbreviations, IANA timezone names, and on Windows translates timezone names to
the closest Windows TimeZone registry equivalent.

LocalizeDateTime(datetime, tzinfo) returns a datetime object relative to the
timezone tzinfo.

The datetime and/or dateutil modules should have covered all of this.
"""

import datetime
import re

from dateutil import parser
from dateutil import tz

from googlecloudsdk.core.util import times_data

try:
  from dateutil import tzwin  # pylint: disable=g-import-not-at-top, Windows
except ImportError:
  tzwin = None


LOCAL = tz.tzlocal()  # The local timezone.
UTC = tz.tzutc()  # The UTC timezone.


def GetTimeZone(name):
  """Returns a datetime.tzinfo object for name.

  Args:
    name: A timezone name string, None for the local timezone.

  Returns:
    A datetime.tzinfo object for name, local timezone if name is unknown.
  """
  if name in ('UTC', 'Z'):
    return UTC
  if name in ('LOCAL', 'L'):
    return LOCAL
  name = times_data.ABBREVIATION_TO_IANA.get(name, name)
  tzinfo = tz.gettz(name)
  if not tzinfo and tzwin:
    name = times_data.IANA_TO_WINDOWS.get(name, name)
    try:
      tzinfo = tzwin.tzwin(name)
    except WindowsError:  # pylint: disable=undefined-variable
      pass
  return tzinfo


def FormatDateTime(dt, fmt=None, tzinfo=None):
  """Returns a string of a datetime object formatted by an extended strftime().

  fmt handles these modifier extensions to the standard formatting chars:

    %Nf   Limit the fractional seconds to N digits. The default is N=6.
    %Ez   Format +/-HHMM offsets as ISO RFC 3339 Z for +0000 otherwise +/-HH:MM.
    %Oz   Format +/-HHMM offsets as ISO RFC 3339 +/-HH:MM.

  Args:
    dt: The datetime object to be formatted.
    fmt: The strftime(3) format string, None for the RFC 3339 format in the dt
      timezone ('%Y-%m-%dT%H:%M:%S.%3f%Ez').
    tzinfo: Format dt relative to this timezone.

  Returns:
    A string of a datetime object formatted by an extended strftime().
  """
  if tzinfo:
    dt = LocalizeDateTime(dt, tzinfo)
  if not fmt:
    fmt = '%Y-%m-%dT%H:%M:%S.%3f%Ez'
  extension = re.compile('%[1-9]?[EO]?[fz]')
  m = extension.search(fmt)
  if not m:
    return dt.strftime(fmt)

  # Split the format into standard and extension parts.
  parts = []
  start = 0
  while m:
    match = start + m.start()
    if start < match:
      # Format the preceeding standard part.
      parts.append(dt.strftime(fmt[start:match]))

    # Format the standard variant of the exetended spec. The extensions only
    # have one modifier char.
    match += 1
    if fmt[match].isdigit():
      n = int(fmt[match])
      match += 1
    else:
      n = None
    if fmt[match] in ('E', 'O'):
      alternate = fmt[match]
      match += 1
    else:
      alternate = None
    spec = fmt[match]
    std_fmt = '%' + spec
    val = dt.strftime(std_fmt)

    if spec == 'f':
      # Limit the fractional part to n digits.
      if n and n < len(val):
        val = val[:n]
    elif spec == 'z':
      # Convert the time zone offset to RFC 3339 format.
      if alternate:
        if alternate == 'E' and val == '+0000':
          val = 'Z'
        elif len(val) == 5:
          val = val[:3] + ':' + val[3:]
    if val:
      parts.append(val)

    start += m.end()
    m = extension.search(fmt[start:])

  # Format the trailing part if any.
  if start < len(fmt):
    parts.append(dt.strftime(fmt[start:]))

  # Combine the parts.
  return ''.join(parts)


class _TzInfoOrOffsetGetter(object):
  """A helper class for dateutil.parser.parse().

  Attributes:
    _timezone_was_specified: True if the parsed date/time string contained
      an explicit timezone name or offset.
  """

  def __init__(self):
    self._timezone_was_specified = False

  def Get(self, name, offset):
    """Returns the tzinfo for name or offset.

    Used by dateutil.parser.parser() to convert timezone names and offsets.

    Args:
      name: A timezone name or None to use offset. If offset is also None then
        the local tzinfo is returned.
      offset: A signed UTC timezone offset in seconds.

    Returns:
      The tzinfo for name or offset or the local tzinfo if both are None.
    """
    if name or offset:
      self._timezone_was_specified = True
    if not name and offset is not None:
      return offset
    return GetTimeZone(name)

  @property
  def timezone_was_specified(self):
    """True if the parsed date/time string contained an explicit timezone."""
    return self._timezone_was_specified


def ParseDateTime(string, tzinfo=None):
  """Parses a date/time string and returns a datetime.datetime object.

  Args:
    string: The date/time string to be parsed.
    tzinfo: A default timezone tzinfo object to use if string has no timezone.

  Returns:
    A datetime.datetime object for the given date/time string.
  """
  # Use tzgetter to determine if string contains an explicit timezone name or
  # offset.
  tzgetter = _TzInfoOrOffsetGetter()
  dt = parser.parse(string, tzinfos=tzgetter.Get)
  if tzinfo and not tzgetter.timezone_was_specified:
    # The string had no timezone name or offset => localize dt to tzinfo.
    dt = parser.parse(string, tzinfos=None)
    dt = dt.replace(tzinfo=tzinfo)
  return dt


def GetDateTimeFromTimeStamp(timestamp, tzinfo=None):
  """Returns the datetime object for a UNIX timestamp.

  Args:
    timestamp: A UNIX timestamp in int or float seconds since the epoch
      (1970-01-01T00:00:00.000000Z).
    tzinfo: A tzinfo object for the timestamp timezone or None for the local
      timezone.

  Returns:
    The datetime object for a UNIX timestamp.
  """
  return datetime.datetime.fromtimestamp(timestamp, tzinfo)


def GetTimeStampFromDateTime(dt):
  """Returns the float UNIX timestamp (with microseconds) for dt.

  Args:
    dt: The datetime object to convert from.

  Returns:
    The float UNIX timestamp (with microseconds) for dt.
  """
  tzinfo = UTC if dt.tzinfo else None
  delta = dt - datetime.datetime.fromtimestamp(0, tzinfo)
  if not hasattr(delta, 'total_seconds'):
    # Python <= 2.6.
    return (delta.microseconds + 0.0 +
            (delta.seconds + delta.days * 24 * 3600) * 10 ** 6) / 10 ** 6
  return delta.total_seconds()


def LocalizeDateTime(dt, tzinfo=None):
  """Returns a datetime object localized to the timezone tzinfo.

  Args:
    dt: The datetime object to localize. It can be timezone naive or aware.
    tzinfo: The timezone of the localized dt. If None then the result is naive,
      otherwise it is aware.

  Returns:
    A datetime object localized to the timezone tzinfo.
  """
  ts = GetTimeStampFromDateTime(dt)
  return GetDateTimeFromTimeStamp(ts, tzinfo=tzinfo)


def Now(tzinfo=None):
  """Returns a timezone aware datetime object for the current time.

  Args:
    tzinfo: The timezone of the localized dt. If None then the result is naive,
      otherwise it is aware.

  Returns:
    A datetime object localized to the timezone tzinfo.
  """
  return datetime.datetime.now(tzinfo)
