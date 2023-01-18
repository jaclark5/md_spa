
import numpy as np

import md_spa_utils.data_manipulation as dm

def random_points(npts, ranges):
    """
    Random points for Monte Carlo use.

    Using ``numpy.random.uniform``, ``npts`` vectors are generated of length ``len(ranges)``.
    The iterable, ranges contains iterables of length 2 with the minimum and maximum of that point.

    An example of this might be ``npts=1e+3`` with a 3x4x2 box, ``ranges=[[0,3],[0,4],[0,2]]``

    Parameters
    ----------
    npts : int
        Number of vector "points" to produce
    ranges : list[list]
        Iterable of min and max values for each dimension of the vectors

    Returns
    -------
    output : numpy.ndarray
        Returns a matrix of random points that is ``npts`` long and ``len(ranges)`` deep. 

    """

    np.random.seed()
    output = np.zeros((int(npts),len(ranges)))
    for i,(xmin, xmax) in enumerate(ranges):
        output[:,i] = np.random.uniform( xmin, xmax, int(npts))
    return output

def overlapping_spheres(rcut, ref_pts, npts=1e+4, repeats=3):
    """
    Monte Carlo code to determine the volume of several overlapping spheres

    Parameters
    ----------
    rcut : float/numpy.ndarray
        Radius of the circles, or an array of different radii for each circle.
    ref_pts : numpy.ndarray
        Array of reference points for centers of circles    
    npts : int, Optional, default=1e+4
        Number of vector "points" to produce. 
    repeats : int, Optional, default=3
        Number of times this MC calculation is performed to obtain the standard deviation

    Returns
    -------
    region_volume : float
        Volume of region consisting of overlapping spheres in cubic units of the scale used in the reference coordinates 
    volume_std : float
        The standard deviation based on the number of times this calculation was repeated

    """

    if not dm.isiterable(rcut):
        rcut = rcut*np.ones(len(ref_pts))
    elif len(ref_pts) != len(rcut):
        raise ValueError("Length of rcut (circle radii) and number of reference points (circle centers) must be equal")

    ref_pts = np.array(ref_pts)
    ref_pts -= np.mean(ref_pts, axis=0)
    ranges = [[np.min(x)-rcut[i], np.max(x)+rcut[i]] for i,x in enumerate(ref_pts.T)]

    volume = np.prod(np.array([xmax-xmin for (xmin,xmax) in ranges]))
    if npts == None:
        npts = int(volume)*10

    region_volumes = np.zeros(repeats)
    for k in range(repeats):
        test_pts = random_points(npts, ranges)
        in_vol = np.empty(int(npts), dtype=bool)
        for i, x in enumerate(test_pts):
            in_vol[i] = np.any([np.sum((ref_pts[j]-x)**2)<=rcut[j]**2 for j in range(len(rcut))])

        #in_vol = np.array([np.any(np.array([np.sum((ref_pts[i]-x)**2)<=rcut[i]**2 for i in range(len(rcut))])) for x in test_pts], dtype=bool)
        region_volumes[k] = volume*len(np.where(in_vol==True)[0])/npts
    final_stats = dm.basic_stats(region_volumes, error_descriptor="sample")

    return final_stats[0], final_stats[1]


