import unittest
from software.comunicacion.protocolo import frame, mix


class ProtocolTests(unittest.TestCase):
    def test_invalid_values_cannot_be_serialized(self):
        for values in [(1, 1, 100, 2, 201, 0), (1, 1, 100, 1, 1, 0),
                       (1, -1, 100, 0, 0, 0), (1, 1, 100, 2, float("nan"), 0)]:
            with self.assertRaises(ValueError):
                frame(*values)

    def test_mix_preserves_curve_when_limited(self):
        left, right = mix(1, 2, 0.5, 1)
        self.assertEqual(right, 200)
        self.assertAlmostEqual(left / right, 1/3, delta=0.01)
        self.assertEqual(mix(0, 1, 0.5, 1), (-200, 200))

    def test_mix_rejects_missing_geometry_and_nonfinite(self):
        for args in [(0, 0, 0, 1), (0, 0, 1, 0), (float("inf"), 0, 1, 1)]:
            with self.assertRaises(ValueError):
                mix(*args)


if __name__ == "__main__":
    unittest.main()
