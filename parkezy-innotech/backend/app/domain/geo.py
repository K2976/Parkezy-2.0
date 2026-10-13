"""Geohash helpers for proximity search (System Design Interview, ch. 16).

Search results are cached per geohash *cell* instead of per exact coordinate, so nearby
users share cache entries. To keep results exact, the cell query covers the requested
radius plus the cell's half-diagonal, and each request then filters and re-measures the
cached candidates against its own position.
"""

import math
from dataclasses import dataclass

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
EARTH_RADIUS_M = 6_371_008.8


def encode(latitude: float, longitude: float, precision: int) -> str:
    lat_lo, lat_hi, lng_lo, lng_hi = -90.0, 90.0, -180.0, 180.0
    bits, bit_count, even, out = 0, 0, True, []
    while len(out) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            bits = (bits << 1) | (longitude >= mid)
            lng_lo, lng_hi = (mid, lng_hi) if longitude >= mid else (lng_lo, mid)
        else:
            mid = (lat_lo + lat_hi) / 2
            bits = (bits << 1) | (latitude >= mid)
            lat_lo, lat_hi = (mid, lat_hi) if latitude >= mid else (lat_lo, mid)
        even = not even
        bit_count += 1
        if bit_count == 5:
            out.append(_BASE32[bits])
            bits, bit_count = 0, 0
    return "".join(out)


@dataclass(frozen=True)
class Cell:
    geohash: str
    center_lat: float
    center_lng: float
    half_diagonal_m: float


def decode_cell(geohash: str) -> Cell:
    lat_lo, lat_hi, lng_lo, lng_hi = -90.0, 90.0, -180.0, 180.0
    even = True
    for ch in geohash:
        value = _BASE32.index(ch)
        for shift in range(4, -1, -1):
            bit = (value >> shift) & 1
            if even:
                mid = (lng_lo + lng_hi) / 2
                lng_lo, lng_hi = (mid, lng_hi) if bit else (lng_lo, mid)
            else:
                mid = (lat_lo + lat_hi) / 2
                lat_lo, lat_hi = (mid, lat_hi) if bit else (lat_lo, mid)
            even = not even
    center_lat, center_lng = (lat_lo + lat_hi) / 2, (lng_lo + lng_hi) / 2
    corner = haversine_m(center_lat, center_lng, lat_hi, lng_hi)
    return Cell(geohash, center_lat, center_lng, corner)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def cell_for_search(latitude: float, longitude: float, radius_m: float, max_error_ratio: float) -> Cell:
    """Coarsest cell whose half-diagonal is at most `max_error_ratio` of the radius
    (coarser cells = more cache sharing; the extra area is filtered out per request)."""
    for precision in range(1, 10):
        cell = decode_cell(encode(latitude, longitude, precision))
        if cell.half_diagonal_m <= radius_m * max_error_ratio:
            return cell
    return decode_cell(encode(latitude, longitude, 9))
