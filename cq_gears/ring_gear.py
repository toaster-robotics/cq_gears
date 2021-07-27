#! /usr/bin/python3

import numpy as np
import cadquery as cq

from .utils import (circle3d_by3points, rotation_matrix, make_spline_approx,
                    make_shell)

from .spur_gear import SpurGear



class RingGear(SpurGear):

    def __init__(self, module, teeth_number, width, rim_width,
                 pressure_angle=20.0, helix_angle=0.0, clearance=0.0,
                 backlash=0.0, curve_points=20, surface_splines=5):
        self.m = m = module
        self.z = z = teeth_number
        self.a0 = a0 = np.radians(pressure_angle)
        self.clearance = clearance
        self.backlash = backlash
        self.curve_points = curve_points
        self.helix_angle = np.radians(helix_angle)
        self.width = width
        self.rim_width = rim_width

        d0 = m * z         # pitch diameter
        adn = 1.0 / (z / d0)  # addendum
        ddn = 1.25 / (z / d0) # dedendum
        da = d0 - 2.0 * adn # addendum circle diameter
        dd = d0 + 2.0 * ddn + 2.0 * clearance # dedendum circle diameter
        s0 = m * (np.pi / 2.0 + backlash * np.tan(a0)) # tooth thickness on
                                                       # the pitch circle
        inv_a0 = np.tan(a0) - a0

        self.r0 = r0 = d0 / 2.0 # pitch radius
        self.ra = ra = da / 2.0 # addendum radius
        self.rd = rd = dd / 2.0 # dedendum radius
        self.rb = rb = np.cos(a0) * d0 / 2.0 # base circle radius
        self.rr = rr = max(rb, rd) # tooth root radius
        self.tau = tau = np.pi * 2.0 / z # pitch angle

        if helix_angle != 0.0:
            self.surface_splines = surface_splines
            self.twist_angle = width / \
                                (r0 * np.tan(np.pi / 2.0 - self.helix_angle))
        else:
            self.surface_splines = 2
            self.twist_angle = 0.0

        self.rim_r = rd + rim_width

        # Calculate involute curve points for the left side of the tooth
        r = np.linspace(ra, rr, curve_points)
        cos_a = r0 / r * np.cos(a0)
        a = np.arccos(np.clip(cos_a, -1.0, 1.0))
        inv_a = np.tan(a) - a
        s = r * (s0 / d0 + inv_a0 - inv_a)
        phi = s / r
        self.tsidel_x = np.cos(phi) * r
        self.tsidel_y = np.sin(phi) * r


        # Calculate tooth tip points - an arc lying on the addendum circle
        b = np.linspace(phi[-1], -phi[-1], curve_points)
        self.ttip_x = np.cos(b) * rd
        self.ttip_y = np.sin(b) * rd


        # Get right side involute curve points by mirroring the left side
        self.tsider_x = (np.cos(-phi) * r)[::-1]
        self.tsider_y = (np.sin(-phi) * r)[::-1]


        # Calculate tooth root points - an arc starting at the right side of
        # the tooth and goes to the left side of the next tooth. The mid-point
        # of that arc lies on the dedendum circle.
        rho = tau - phi[0] * 2.0
        # Get the three points defining the arc
        p1 = np.array((self.tsider_x[-1], self.tsider_y[-1], 0.0))
        p2 = np.array((np.cos(-phi[0] - rho / 2.0) * ra,
              np.sin(-phi[0] - rho / 2.0) * ra, 0.0))
        p3 = np.array((np.cos(-phi[0] - rho) * ra,
              np.sin(-phi[0] - rho) * ra, 0.0))

        # Calculate arc's center and radius
        bcr, bcxy = circle3d_by3points(p1, p2, p3)
        # Calculate start and end angles
        t1 = np.arctan2(p1[1] - bcxy[1], p1[0] - bcxy[0])
        t2 = np.arctan2(p3[1] - bcxy[1], p3[0] - bcxy[0])
        if t1 < 0.0:
            t1 += np.pi * 2.0
        if t2 < 0.0:
            t2 += np.pi * 2.0
        t1, t2 = min(t1, t2), max(t1, t2)
        t = np.linspace(t2 + np.pi * 2.0, t1 + np.pi * 2.0, curve_points)
        
        self.troot_x = bcxy[0] + bcr * np.cos(t)
        self.troot_y = bcxy[1] + bcr * np.sin(t)