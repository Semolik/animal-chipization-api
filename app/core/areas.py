import math
from typing import List

from app.schemas.locations import LocationBase


class AreaValidator:
    def __init__(self, points: List[LocationBase]):
        self.points = points

    def validate(self):
        # Check if the polygon contains at least three points
        if len(self.points) < 3:
            return False

        # Check if all points lie on the same line
        x_coords = [point.longitude for point in self.points]
        y_coords = [point.latitude for point in self.points]
        if len(set(x_coords)) == 1 or len(set(y_coords)) == 1:
            return False

        # Check if the polygon self-intersects
        for i in range(len(self.points)):
            for j in range(i + 1, len(self.points)):
                if i == 0 and j == len(self.points) - 1:
                    continue
                elif i == j - 1:
                    continue
                elif j == i - 1:
                    continue
                elif j == len(self.points) - 1 and i == 0:
                    continue

                if self.line_intersects(self.points[i], self.points[(i + 1) % len(self.points)],
                                        self.points[j], self.points[(j + 1) % len(self.points)]):
                    return False

        # Check if the polygon has duplicate points
        points = [(point.latitude, point.longitude) for point in self.points]
        if len(set(points)) != len(points):
            return False

        return True

    def line_intersects(self, p1, q1, p2, q2):
        def orientation(p, q, r):
            val = (q.latitude - p.latitude) * (r.longitude - q.longitude) - \
                  (q.longitude - p.longitude) * (r.latitude - q.latitude)
            if val == 0:
                return 0
            elif val > 0:
                return 1
            else:
                return 2

        o1 = orientation(p1, q1, p2)
        o2 = orientation(p1, q1, q2)
        o3 = orientation(p2, q2, p1)
        o4 = orientation(p2, q2, q1)

        if (o1 != o2 and o3 != o4):
            return True

        if (o1 == 0 and self.on_segment(p1, p2, q1)):
            return True

        if (o2 == 0 and self.on_segment(p1, q2, q1)):
            return True

        if (o3 == 0 and self.on_segment(p2, p1, q2)):
            return True

        if (o4 == 0 and self.on_segment(p2, q1, q2)):
            return True

        return False

    def on_segment(self, p, q, r):
        if (q.longitude <= max(p.longitude, r.longitude) and q.longitude >= min(p.longitude, r.longitude) and
                q.latitude <= max(p.latitude, r.latitude) and q.latitude >= min(p.latitude, r.latitude)):
            return True
        return False