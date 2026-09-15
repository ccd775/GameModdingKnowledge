"""Synthetic regression fixtures for errors repeated across MK1 projects."""
import math
import unittest
from retarget_math import fit_segment, fit_terminal, transform, pelvis_point, pelvis_weight, atlas_pixel_rect


class RetargetRegressionTests(unittest.TestCase):
    def near(self, a, b):
        for x,y in zip(a,b):self.assertAlmostEqual(x,y,places=7)

    def test_long_spine_must_not_expand_transverse_body(self):
        m=fit_segment((0,0,0),(0,1,0),(10,20,30),(10,23,30),1.5)
        self.near(transform(m,(0,1,0)),(10,23,30))
        self.near(transform(m,(1,0,0)),(11.5,20,30))
        self.near(transform(m,(0,0,1)),(10,20,31.5))

    def test_axis_rotation_and_antiparallel(self):
        m=fit_segment((1,2,3),(1,3,3),(4,5,6),(6,5,6),1.5)
        self.near(transform(m,(1,3,3)),(6,5,6))
        m=fit_segment((0,0,0),(0,1,0),(0,0,0),(0,-2,0),1.5)
        self.near(transform(m,(0,1,0)),(0,-2,0))
        with self.assertRaises(ValueError):fit_segment((0,0,0),(0,0,0),(0,0,0),(0,1,0),1)

    def test_head_scale_is_explicit(self):
        m=fit_terminal((0,1,0),(0,3,0),1.5)
        self.near(transform(m,(1,1,0)),(1.5,3,0))
        with self.assertRaises(TypeError):fit_terminal((0,1,0),(0,3,0))
        with self.assertRaises(ValueError):fit_terminal((0,1,0),(0,3,0),float('nan'))
        with self.assertRaises(ValueError):fit_terminal((0,float('nan'),0),(0,3,0),1.5)

    def test_shared_pelvis_preserves_garment_height_and_socket_alignment(self):
        # Hips-based and leg-based maps would disagree; shared midpoint is fixed.
        f=lambda p:pelvis_point(p,(0,0,10),(0,0,30),2,4,1.5,1.5)
        self.near(f((2,0,10)),(4,0,30))
        self.near(f((-2,0,10)),(-4,0,30))
        self.assertAlmostEqual(f((1,0,12))[2]-f((1,0,10))[2],3)
        self.assertAlmostEqual(f((1,0,11))[2],31.5)
        with self.assertRaises(ValueError):pelvis_point((0,0,0),(0,0,0),(0,0,0),2,.1,1.5,1.5)

    def test_transition_is_bounded_and_flat_at_boundaries(self):
        bounds=(0,2,4,6)
        self.assertEqual([pelvis_weight(x,bounds) for x in (-1,0,2,3,4,6,7)],[0,0,1,1,1,0,0])
        h=1e-5
        for x in bounds:self.assertLess(abs((pelvis_weight(x+h,bounds)-pelvis_weight(x-h,bounds))/(2*h)),1e-4)
        with self.assertRaises(ValueError):pelvis_weight(2,(0,0,4,6))
        with self.assertRaises(ValueError):pelvis_weight(float('nan'),bounds)

    def test_small_atlas_pages_use_their_height_in_png_flip(self):
        self.assertEqual(atlas_pixel_rect((.5,.5,.25,.25),8192),(4096,2048,2048,2048))
        self.assertEqual(atlas_pixel_rect((.75,.5,.25,.25),8192),(6144,2048,2048,2048))
        self.assertEqual(atlas_pixel_rect((0,.5,.5,.5),8192),(0,0,4096,4096))
        with self.assertRaises(ValueError):atlas_pixel_rect((.9,0,.2,.2),8192)
        with self.assertRaises(ValueError):atlas_pixel_rect((0,0,1/3,1/3),8192)


if __name__=='__main__':unittest.main()
