import base64
import hashlib


class Geohash:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.latitude_interval = [-90.0, 90.0]
        self.longitude_interval = [-180.0, 180.0]
        self.base32 = "0123456789bcdefghjkmnpqrstuvwxyz"

    def encode_v1(self):
        lat_bit, lon_bit = 30, 30
        lat_interval, lon_interval = list(
            self.latitude_interval), list(self.longitude_interval)
        geohash = ""
        for bit in range(lat_bit + lon_bit):
            if bit % 2 == 0:
                mid = sum(lon_interval) / 2.0
                if self.longitude >= mid:
                    geohash += "1"
                    lon_interval[0] = mid
                else:
                    geohash += "0"
                    lon_interval[1] = mid
            else:
                mid = sum(lat_interval) / 2.0
                if self.latitude >= mid:
                    geohash += "1"
                    lat_interval[0] = mid
                else:
                    geohash += "0"
                    lat_interval[1] = mid
        hash_str = ""
        for i in range(0, lat_bit + lon_bit, 5):
            bits = geohash[i:i+5]
            hash_str += self.base32[int(bits, 2)]
        return hash_str
    def encode_v2(self):
        v1 = self.encode_v1()
        v1_as_bytes = v1.encode()
        v2 = base64.b64encode(v1_as_bytes).decode()
        return v2

    def encode_v3(self):
        v1 = self.encode_v1()
        v1_as_bytes = v1.encode()
        md5 = hashlib.md5(v1_as_bytes)
        md5_as_bytes = md5.digest()
        md5_reversed = md5_as_bytes[::-1]
        v3 = base64.b64encode(md5_reversed).decode()
        return v3