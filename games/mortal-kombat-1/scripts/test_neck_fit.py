import math
import unittest
from neck_fit import neck_point


class NeckTests(unittest.TestCase):
    def point(self, p, h=0, n=1, **kw):
        args = dict(neck_z=10., head_z=20., shift=4.5,
                    head_weight=h, neck_weight=n)
        args.update(kw)
        return neck_point(p, **args)

    def test_head_and_long_hair_rigid(self):
        for z in (-100., 0., 15., 20., 100.):
            self.assertEqual(self.point((2., 3., z), h=1, n=0), (2., 3., z-4.5))

    def test_protected_and_mixed_weights(self):
        p = (2., 3., 15.)
        self.assertEqual(self.point(p, h=0, n=0), p)
        self.assertEqual(self.point(p, h=.5, n=.5), (2., 3., 11.625))

    def test_neck_boundaries_and_derivative(self):
        self.assertEqual(self.point((0, 0, 10.))[2], 10.)
        self.assertEqual(self.point((0, 0, 20.))[2], 15.5)
        eps = 1e-4
        derivative = lambda z: (self.point((0, 0, z+eps))[2]
                                - self.point((0, 0, z-eps))[2])/(2*eps)
        self.assertAlmostEqual(derivative(10.), 1., places=4)
        self.assertAlmostEqual(derivative(20.), 1., places=4)
        self.assertAlmostEqual(derivative(15.), .325, places=6)
        self.assertTrue(all(derivative(10+i*.1)>0 for i in range(101)))

    def test_units(self):
        cm = self.point((2., 3., 15.))
        meters = neck_point((.02, .03, .15), neck_z=.1, head_z=.2,
                            shift=.045, head_weight=0, neck_weight=1)
        for a, b in zip(cm, meters):
            self.assertAlmostEqual(a*.01, b)

    def test_reject_invalid(self):
        for kw in [dict(head_z=10), dict(shift=-1), dict(shift=7),
                   dict(head_weight=.7, neck_weight=.7), dict(neck_weight=-.1),
                   dict(shift=math.nan), dict(neck_z=math.inf)]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.point((0, 0, 15), **kw)
        with self.assertRaises(ValueError):
            self.point((0, math.nan, 15))


if __name__ == '__main__':
    unittest.main()
