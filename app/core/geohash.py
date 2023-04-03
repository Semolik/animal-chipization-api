import math


class Geohash:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.latitude_interval = [-90.0, 90.0]
        self.longitude_interval = [-180.0, 180.0]



    def _encode_v1(self, bit_length=30):
        # Define the base32 encoding scheme
        base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
        # Define the bit lengths for latitude and longitude
        lat_bit, lon_bit = bit_length, bit_length
        # Define the intervals for latitude and longitude
        lat_interval, lon_interval = list(
            self.latitude_interval), list(self.longitude_interval)
        # Define the initial geohash
        geohash = ""
        # Iterate through the total number of bits (lat_bit + lon_bit)
        for bit in range(lat_bit + lon_bit):
            # Check whether the current bit should be assigned to the latitude or longitude
            if bit % 2 == 0:
                # Calculate the midpoint of the longitude interval
                mid = sum(lon_interval) / 2.0
                # If the longitude is greater than or equal to the midpoint, set the bit to 1 and update the longitude interval
                if self.longitude >= mid:
                    geohash += "1"
                    lon_interval[0] = mid
                # Otherwise, set the bit to 0 and update the longitude interval
                else:
                    geohash += "0"
                    lon_interval[1] = mid
            else:
                # Calculate the midpoint of the latitude interval
                mid = sum(lat_interval) / 2.0
                # If the latitude is greater than or equal to the midpoint, set the bit to 1 and update the latitude interval
                if self.latitude >= mid:
                    geohash += "1"
                    lat_interval[0] = mid
                # Otherwise, set the bit to 0 and update the latitude interval
                else:
                    geohash += "0"
                    lat_interval[1] = mid
        # Convert the binary geohash to base32 encoding
        hash_str = ""
        for i in range(0, lat_bit + lon_bit, 5):
            bits = geohash[i:i+5]
            hash_str += base32[int(bits, 2)]
        return hash_str

    def _encode_v2(self, bit_length=30):
        # Define the base32 encoding scheme
        base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
        # Define the bit lengths for latitude and longitude
        lat_bit, lon_bit = bit_length, bit_length
        # Define the intervals for latitude and longitude
        lat_interval, lon_interval = list(
            self.latitude_interval), list(self.longitude_interval)
        # Define the initial geohash
        geohash = ""
        # Iterate through the total number of bits (lat_bit + lon_bit)
        for bit in range(lat_bit + lon_bit):
            # Check whether the current bit should be assigned to the latitude or longitude
            if bit % 2 == 0:
                # Calculate the midpoint of the longitude interval
                mid = sum(lon_interval) / 2.0
                # If the longitude is greater than or equal to the midpoint, set the bit to 1 and update the longitude interval
                if self.longitude >= mid:
                    geohash += "1"
                    lon_interval[0] = mid
                # Otherwise, set the bit to 0 and update the longitude interval
                else:
                    geohash += "0"
                    lon_interval[1] = mid
            else:
                # Calculate the midpoint of the latitude interval
                mid = sum(lat_interval) / 2.0
                # If the latitude is greater than or equal to the midpoint, set the bit to 1 and update the latitude interval
                if self.latitude >= mid:
                    geohash += "1"
                    lat_interval[0] = mid
                # Otherwise, set the bit to 0 and update the latitude interval
                else:
                    geohash += "0"
                    lat_interval[1] = mid
        # Convert the binary geohash to base32 encoding
        hash_str = ""
        for i in range(0, lat_bit + lon_bit, 5):
            bits = geohash[i:i+5]
            hash_str += base32[int(bits, 2)]
        return hash_str