"""Strict, offline parsing of explicit OpenStreetMap coordinate links."""
import math
import re
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

from ..models.common import Issue, Result, Status
from ..models.location import Point
from ..models.requests import RequestContext

_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
_MAP = re.compile(r"map=(?:\d{1,2})/([^/]+)/([^/]+)")


def _result(status, point=None, code=None):
    return Result[Point](status=status, data=point,
                         issues=(Issue(code=code, message_key=f"map_link.{code}"),) if code else (),
                         context=RequestContext(request_id=str(uuid4()), method_version="map-link-v1"))


def _coordinate(value, low, high):
    if not _NUMBER.fullmatch(value):
        raise ValueError("invalid_coordinate")
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError("invalid_coordinate")
    return number


def parse_map_link(url: str) -> Result[Point]:
    """Parse only OSM long-form map links; never resolve, fetch or infer a pin."""
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 or ord(c) > 126 for c in url):
        return _result(Status.invalid_input, code="invalid_url")
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.hostname not in {"www.openstreetmap.org", "openstreetmap.org"}
                or parts.username is not None or parts.password is not None or parts.port is not None or parts.path not in {"", "/"}):
            return _result(Status.unsupported, code="unsupported_link")
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
        if len(pairs) != len({k for k, _ in pairs}) or {k for k, _ in pairs} - {"mlat", "mlon"}:
            raise ValueError("ambiguous_parameters")
        params = dict(pairs)
        if set(params) != {"mlat", "mlon"}:
            return _result(Status.unsupported, code="explicit_marker_required")
        lat = _coordinate(params["mlat"], -90, 90)
        lon = _coordinate(params["mlon"], -180, 180)
        if parts.fragment:
            match = _MAP.fullmatch(parts.fragment)
            if match is None or _coordinate(match[1], -90, 90) != lat or _coordinate(match[2], -180, 180) != lon:
                raise ValueError("ambiguous_coordinates")
        return _result(Status.ok, Point(longitude=lon, latitude=lat))
    except (ValueError, OverflowError):
        return _result(Status.invalid_input, code="invalid_or_ambiguous_link")
