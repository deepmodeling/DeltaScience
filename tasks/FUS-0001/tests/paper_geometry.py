"""Verbatim diagnostic functions from UKAEA DOI10.14468/26m5-ey02.
CC-BY-NC-SA4.0. Pentland et al. Source: create_MASTU_pickles.py.
No baseline generation or nonlinear equilibrium solving occurs here.
"""
import numpy as np
import scipy as sp
import scipy.spatial.distance
from freegs4e import critical
from numpy import pi, abs, clip, linspace, argmax

def Separatrix(R, Z, psi, ntheta, psival=1.0, theta_grid=None, input_opoint=None):
    """Find the R, Z coordinates of the separatrix for equilbrium
    eq. Returns a tuple of (R, Z, R_X, Z_X), where R_X, Z_X are the
    coordinates of the X-point on the separatrix. Points are equally
    spaced in geometric poloidal angle.

    If opoint, xpoint or psi are not given, they are calculated from eq

    eq - Equilibrium object
    opoint - List of O-point tuples of (R, Z, psi)
    xpoint - List of X-point tuples of (R, Z, psi)
    ntheta - Number of points to find
    psi - Grid of psi on (R, Z)
    axis - A matplotlib axis object to plot points on
    input_opoint - a user-chosen magnetic axis from which to find separatrix
    """

    opoint, xpoint = critical.find_critical(R, Z, psi)

    psinorm = (psi - opoint[0][2]) / (xpoint[0][2] - opoint[0][2])

    psifunc = sp.interpolate.RectBivariateSpline(R[:, 0], Z[0, :], psinorm)

    if input_opoint is None:
        r0, z0 = opoint[0][0:2]
    else:
        r0, z0 = input_opoint

    if theta_grid is None:
        theta_grid = np.linspace(0, 2 * pi, ntheta, endpoint=False)
    dtheta = theta_grid[1] - theta_grid[0]

    # Avoid putting theta grid points exactly on the X-points
    xpoint_theta = np.arctan2(xpoint[0][0] - r0, xpoint[0][1] - z0)
    xpoint_theta = xpoint_theta * (xpoint_theta >= 0) + (xpoint_theta + 2 * pi) * (
        xpoint_theta < 0
    )  # let's make it between 0 and 2*pi
    # How close in theta to allow theta grid points to the X-point
    TOLERANCE = 2.0e-4
    if any(abs(theta_grid - xpoint_theta) < TOLERANCE):
        # warn("Theta grid too close to X-point, shifting by half-step")
        # print('Im shifting the grid!')
        theta_grid += dtheta / 2 * np.ones(ntheta) * (abs(theta_grid - xpoint_theta) < TOLERANCE)

    isoflux = []
    for theta in theta_grid:
        r, z = find_psisurface(
            psifunc,
            R,
            Z,
            r0,
            z0,
            r0 + 10.0 * np.sin(theta),
            z0 + 10.0 * np.cos(theta),
            psival=psival,
            n=1000,
        )
        isoflux.append((r, z))

    threshold = 0.1 # exlude points this far away from other nearest point
    points = np.array(isoflux)
    distances = sp.spatial.distance.cdist(points, points)
    min_distances = np.min(np.where(distances == 0, np.inf, distances), axis=1)  # Exclude distances to itself
    far_points = np.where(min_distances > threshold)[0]
    points[far_points] = None
    
    return points, theta_grid

def find_psisurface(psifunc, R, Z, r0, z0, r1, z1, psival=1.0, n=100):
    """
    eq      - Equilibrium object
    (r0,z0) - Start location inside separatrix
    (r1,z1) - Location outside separatrix

    n - Number of starting points to use
    """
    # Clip (r1,z1) to be inside domain
    # Shorten the line so that the direction is unchanged
    if abs(r1 - r0) > 1e-6:
        rclip = clip(r1, np.min(R), np.max(R))
        z1 = z0 + (z1 - z0) * abs((rclip - r0) / (r1 - r0))
        r1 = rclip

    if abs(z1 - z0) > 1e-6:
        zclip = clip(z1, np.min(Z), np.max(Z))
        r1 = r0 + (r1 - r0) * abs((zclip - z0) / (z1 - z0))
        z1 = zclip

    r = linspace(r0, r1, n)
    z = linspace(z0, z1, n)

    pnorm = psifunc(r, z, grid=False)

    if hasattr(psival, "__len__"):
        pass

    else:
        # Only one value
        ind = argmax(pnorm > psival)

        # Edited by Bhavin 31/07/18
        # Changed 1.0 to psival in f
        # make f gradient to psival surface
        f = (pnorm[ind] - psival) / (pnorm[ind] - pnorm[ind - 1])

        r = (1.0 - f) * r[ind] + f * r[ind - 1]
        z = (1.0 - f) * z[ind] + f * z[ind - 1]

    return r, z

def max_euclidean_distance(points1, points2):
    """
    Calculate the maximum Euclidean distance between corresponding points in two sets.
    Exclude points with 'None' values.
    """
    valid_indices = np.logical_not(np.any(np.isnan(points1), axis=1) | np.any(np.isnan(points2), axis=1))
    points1_valid = points1[valid_indices]
    points2_valid = points2[valid_indices]
    if len(points1_valid) == 0 or len(points2_valid) == 0:
        return np.nan
    return np.max(np.sqrt(np.sum((points1_valid - points2_valid)**2, axis=1)))
