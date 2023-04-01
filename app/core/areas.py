from typing import List

from app.schemas.locations import LocationBase


class AreaValidator:
    def __init__(self, points: List[LocationBase]):
        self.points = points

    def validate(self) -> bool:
        if len(self.points) < 4:
            return False
        if self.points[0] != self.points[-1]:
            return False
        for i in range(1, len(self.points) - 1):
            for j in range(i + 1, len(self.points) - 1):
                if self.do_segments_intersect(self.points[i - 1], self.points[i], self.points[j - 1], self.points[j]):
                    return False
        return True

    def do_segments_intersect(self, p1: LocationBase, q1: LocationBase, p2: LocationBase, q2: LocationBase):
        o1 = self.orientation(p1, q1, p2)
        o2 = self.orientation(p1, q1, q2)
        o3 = self.orientation(p2, q2, p1)
        o4 = self.orientation(p2, q2, q1)
        if o1 != o2 and o3 != o4:
            return True

        if o1 == 0 and self.on_segment(p1, q1, p2):
            return True

        if o2 == 0 and self.on_segment(p1, q1, q2):
            return True

        if o3 == 0 and self.on_segment(p2, q2, p1):
            return True

        if o4 == 0 and self.on_segment(p2, q2, q1):
            return True

        return False

    def orientation(self, p: LocationBase, q: LocationBase, r: LocationBase):
        val = (q.latitude - p.latitude) * (r.longitude - q.longitude) - (
                q.longitude - p.longitude) * (r.latitude - q.latitude)
        if val == 0:
            return 0
        return 1 if val > 0 else 2

    def on_segment(self, p: LocationBase, q: LocationBase, r: LocationBase):
        if max(p.longitude, q.longitude) >= r.longitude >= min(p.longitude, q.longitude) \
                and max(p.latitude, q.latitude) >= r.latitude >= min(p.latitude, q.latitude):
            return True
        return False
