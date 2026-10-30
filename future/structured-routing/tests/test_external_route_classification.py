from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
SCRIPT = EXPERIMENT / "scripts" / "classify_external_route.py"
INDEX = EXPERIMENT / "external-routing-stop-index.json"

SPEC = importlib.util.spec_from_file_location("classify_external_route", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def encode_polyline(points: list[tuple[float, float]], precision: int = 6) -> str:
    factor = 10 ** precision
    previous_lat = 0
    previous_lon = 0
    output = []
    for lat, lon in points:
        values = [round(lat * factor) - previous_lat, round(lon * factor) - previous_lon]
        previous_lat += values[0]
        previous_lon += values[1]
        for value in values:
            encoded = ~(value << 1) if value < 0 else value << 1
            while encoded >= 0x20:
                output.append(chr((0x20 | (encoded & 0x1F)) + 63))
                encoded >>= 5
            output.append(chr(encoded + 63))
    return "".join(output)


class ExternalRouteClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads(INDEX.read_text())

    def test_unknown_ferry_before_known_boarding_is_ignored(self) -> None:
        shape = encode_polyline([
            (60.4660, 26.9458),  # deliberately outside the maintained archipelago stops
            (60.186778, 21.438519),  # Kittuis boarding coordinate from Valhalla
        ])
        response = {
            "trip": {
                "summary": {"has_ferry": True},
                "legs": [{
                    "shape": shape,
                    "maneuvers": [
                        {"type": 28, "begin_shape_index": 0, "street_names": ["unknown"]},
                        {"type": 28, "begin_shape_index": 1, "street_names": ["Kittuis-Galtby"]},
                    ],
                }],
            },
        }

        result = MODULE.classify(response, self.index)

        self.assertEqual(result["status"], "known_road_area_found")
        self.assertEqual(result["unknownBoardingsBeforeFirstKnown"], 1)
        self.assertEqual(result["firstKnownBoarding"]["boardingSequence"], 2)
        self.assertEqual(result["firstKnownBoarding"]["stop"]["id"], "Kittuis")
        self.assertEqual(result["firstKnownBoarding"]["roadAreaId"], "houtskar")

    def test_nearest_stop_must_be_within_500_metres(self) -> None:
        kittuis = next(stop for stop in self.index["stops"] if stop["id"] == "Kittuis")
        near = MODULE.nearest_known_stop(
            {"lat": 60.186778, "lon": 21.438519}, self.index["stops"], 500
        )
        far = MODULE.nearest_known_stop(
            {"lat": 60.4660, "lon": 26.9458}, self.index["stops"], 500
        )
        self.assertEqual(near["id"], kittuis["id"])
        self.assertEqual(near["roadAreaId"], "houtskar")
        self.assertIsNone(far)

    def test_problematic_terminals_have_landside_routing_coordinates(self) -> None:
        stops = {stop["id"]: stop for stop in self.index["stops"]}
        self.assertEqual(
            stops["Naantali"]["routingCoordinates"],
            {"lon": 22.038798, "lat": 60.4591564},
        )
        self.assertEqual(
            stops["Lillmälö"]["routingCoordinates"],
            {"lon": 22.1126618, "lat": 60.2354954},
        )

    def test_valhalla_response_must_include_maneuvers(self) -> None:
        response = {
            "trip": {
                "summary": {"has_ferry": True},
                "legs": [{"shape": "", "summary": {"has_ferry": True}}],
            },
        }
        result = MODULE.classify(response, self.index)
        self.assertEqual(result["status"], "maneuvers_required")

    def test_no_ferry_means_same_area_as_known_anchor(self) -> None:
        response = {
            "trip": {
                "summary": {"has_ferry": False},
                "legs": [{"shape": encode_polyline([(61.5, 23.75), (60.45, 22.27)]), "maneuvers": []}],
            },
        }
        result = MODULE.classify(
            response, self.index, anchor_road_area_id="mainland_finland"
        )
        self.assertEqual(result["status"], "known_road_area_found")
        self.assertEqual(result["roadArea"], {
            "id": "mainland_finland",
            "inference": "no_ferry_to_known_anchor",
        })


if __name__ == "__main__":
    unittest.main()
