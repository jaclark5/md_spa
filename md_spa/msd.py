""" Analyze mean-squared displacement trajectories for diffusivity, debye-waller parameters, and nongaussian parameter.

    Recommend loading with:
    ``import md_spa.msd as msd``

"""

import re
import numpy as np
import warnings
import os
import matplotlib.pyplot as plt
from scipy.stats import linregress
from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.ndimage import gaussian_filter1d

from md_spa.utils import data_manipulation as dm
from md_spa.utils import file_manipulation as fm
from md_spa import fit_data as fd

def keypoints2csv(filename, fileout="msd.csv", mode="a", delimiter=",", titles=None, additional_entries=None, additional_header=None, kwargs_find_diffusivity={}, kwargs_debye_waller={}, file_header_kwargs={}):
    """
    Given the path to a csv file containing msd data, extract key values and save them to a .csv file. The file of msd data should have a first column with distance values, followed by columns with radial distribution values. These data sets will be distinguished in the resulting csv file with the column headers

    Parameters
    ----------
    filename : str
        Input filename and path to lammps msd output file
    fileout : str, default="msd.csv"
        Filename of output .csv file
    mode : str, default="a"
        Mode used in writing the csv file, either "a" or "w".
    delimiter : str, default=","
        Delimiter between data in input file
    titles : list[str], default=None
        Titles for plots if that is specified in the ``kwargs_find_diffusivity`` or ``kwargs_debye_waller``
    additional_entries : list, default=None
        This iterable structure can contain additional information about this data to be added to the beginning of the row
    additional_header : list, default=None
        If the csv file does not exist, these values will be added to the beginning of the header row. This list must be equal to the `additional_entries` list.
    kwargs_find_diffusivity : dict, default={}
        Keywords for :func:`md_spa.msd.find_diffusivity` function
    kwargs_debye_waller : dict, default={}
        Keywords for :func:`md_spa.msd.debye_waller` function
    file_header_kwargs : dict, default={}
        Keywords for :func:`md_spa.utils.os_manipulation.file_header` function    

    Returns
    -------
    csv file
    
    """
    if not os.path.isfile(filename):
        raise ValueError("The given file could not be found: {}".format(filename))

    data = np.transpose(np.genfromtxt(filename, delimiter=delimiter))

    if titles == None:
        titles = [re.split(",|\[|\(", x)[0] for x in fm.find_header(filename, **file_header_kwargs)]
    if len(titles) != len(data):
        raise ValueError("The number of titles does not equal the number of columns")

    if np.all(additional_entries != None):
        flag_add_ent = True
        if not dm.isiterable(additional_entries):
            raise ValueError("The provided variable `additional_entries` must be iterable")
    else:
        flag_add_ent = False
        additional_entries = []
    if np.all(additional_header != None):
        flag_add_header = True
        if not dm.isiterable(additional_header):
            raise ValueError("The provided variable `additional_header` must be iterable")
    else:
        flag_add_header = False

    if flag_add_ent:
        if flag_add_header:
            if len(additional_entries) != len(additional_header):
                raise ValueError("The variables `additional_entries` and `additional_header` must be of equal length")
        else:
            additional_header = ["-" for x in additional_entries]
            flag_add_header = True

    t_tmp = data[0]
    tmp_data = []
    for i in range(1,len(data)):
        tmp_kwargs_diff = kwargs_find_diffusivity.copy()
        tmp_kwargs_dw = kwargs_debye_waller.copy()
        if "title" not in tmp_kwargs_diff:
            tmp_kwargs_diff["title"] = titles[i]
        if "title" not in tmp_kwargs_dw:
            tmp_kwargs_dw["title"] = titles[i]
        dw, tau = debye_waller(t_tmp, data[i], **tmp_kwargs_dw)
        if ("bounds" not in tmp_kwargs_diff or (tmp_kwargs_diff["bounds"][0] is not None or np.isnan(tmp_kwargs_diff["bounds"][0]))) and not np.isnan(tau):
            if "bounds" not in tmp_kwargs_diff:
                tmp_kwargs_diff["bounds"] = (10*tau, None)
            else:
                tmp_kwargs_diff["bounds"] = (10*tau, tmp_kwargs_diff["bounds"][1])
        best, longest = find_diffusivity(t_tmp, data[i], **tmp_kwargs_diff)
        tmp_data.append(list(additional_entries)+[titles[i]]+[dw, tau]+list(best)+list(longest))

    file_headers = ["Group", "DW [l-unit^2]", "tau [t-unit]", "Best D [l-unit^2 / t-unit]", "B D SE", "B t_bound1 [t-unit]", "B t_bound2 [t-unit]", "B Exponent", "B Intercept [l-unit^2]", "B Npts", "Longest D [l-unit^2/t-unit]", "L D SE", "L t_bound1 [t-unit]", "L t_bound2 [t-unit]", "L Exponent", "L Intercept [l-unit^2]", "L Npts"]
    if not os.path.isfile(fileout) or mode=="w":
        if flag_add_header:
            file_headers = list(additional_header) + file_headers
        fm.write_csv(fileout, tmp_data, mode=mode, header=file_headers)
    else:
        fm.write_csv(fileout, tmp_data, mode=mode)


def nongaussian2csv(filename, fileout="nongaussian.csv", mode="a", delimiter=",", titles=None, additional_entries=None, additional_header=None, file_header_kwargs={}, kwargs_extrema={}):
    """
    Given the path to a csv file containing nongaussian data, extract key values and save them to a .csv file. The file of nongaussian data should have a first column with distance values, followed by columns with radial distribution values. These data sets will be distinguished in the resulting csv file with the column headers

    Parameters
    ----------
    filename : str
        Input filename and path to nongaussian output file created from :func:`md_spa.mdanalysis.calc_msds`
    fileout : str, default="msd.csv"
        Filename of output .csv file
    mode : str, default="a"
        Mode used in writing the csv file, either "a" or "w".
    delimiter : str, default=","
        Delimiter between data in input file
    titles : list[str], default=None
        Titles for plots if that is specified in the ``kwargs_extrema``
    additional_entries : list, default=None
        This iterable structure can contain additional information about this data to be added to the beginning of the row
    additional_header : list, default=None
        If the csv file does not exist, these values will be added to the beginning of the header row. This list must be equal to the ``additional_entries`` list.
    file_header_kwargs : dict, default={}
        Keywords for :func:`md_spa.utils.os_manipulation.file_header` function    
    kwargs_extrema : dict, default={}
        Keywords for :func:`md_spa.fit_data.pull_extrema`

    Returns
    -------
    csv file
    
    """

    if not os.path.isfile(filename):
        raise ValueError("The given file could not be found: {}".format(filename))

    data = np.transpose(np.genfromtxt(filename, delimiter=delimiter, comments="#"))

    if titles == None:
        titles = [re.split(",|\[|\(", x)[0] for x in fm.find_header(filename, **file_header_kwargs)]
    if len(titles) != len(data):
        raise ValueError("The number of titles does not equal the number of columns")

    if np.all(additional_entries != None):
        flag_add_ent = True
        if not dm.isiterable(additional_entries):
            raise ValueError("The provided variable `additional_entries` must be iterable")
    else:
        flag_add_ent = False
        additional_entries = []
    if np.all(additional_header != None):
        flag_add_header = True
        if not dm.isiterable(additional_header):
            raise ValueError("The provided variable `additional_header` must be iterable")
    else:
        flag_add_header = False

    if flag_add_ent:
        if flag_add_header:
            if len(additional_entries) != len(additional_header):
                raise ValueError("The variables `additional_entries` and `additional_header` must be of equal length")
        else:
            additional_header = ["-" for x in additional_entries]
            flag_add_header = True

    t_tmp = np.log10(data[0][1:])
    tmp_data = []
    for i in range(1,len(data)):
        kwargs_tmp = kwargs_extrema.copy()
        tmp = os.path.split(kwargs_tmp["plot_name"])
        kwargs_tmp["plot_name"] = os.path.join(tmp[0],titles[i].replace(" ", "")+"_"+tmp[1])
        _, maxima, _ = fd.pull_extrema(t_tmp, data[i][1:], **kwargs_tmp)
        ind_min = np.where(maxima[1]==np.max(maxima[1]))[0][0]
        tau, nongaussian = maxima[0][ind_min], maxima[1][ind_min]
        tau = 10**tau

        tmp_data.append(list(additional_entries)+[titles[i]]+[tau, nongaussian])

    file_headers = ["Group", "tau", "nongauss peak"]
    if not os.path.isfile(fileout) or mode=="w":
        if flag_add_header:
            file_headers = list(additional_header) + file_headers
        fm.write_csv(fileout, tmp_data, mode=mode, header=file_headers)
    else:
        fm.write_csv(fileout, tmp_data, mode=mode)


def debye_waller(time, msd, use_frac=1, show_plot=False, save_plot=False, title=None, plot_name="debye-waller.png", sigma_spline=None, verbose=False):
    """
    Analyzing the ballistic region of an MSD curve yields the debye-waller factor, which relates to the cage region that the atom experiences.
    DOI: 10.1073/pnas.1418654112

    Parameters
    ----------
    time : numpy.ndarray
        Time array of the same length at MSD
    msd : numpy.ndarray
        MSD array with one dimension
    use_frac : float, default=1
        Choose what fraction of the msd to use. This will cut down on computational time in spending time on regions with poor statistics.
    save_plot : bool, default=False
        choose to save a plot of the fit
    title : str, default=None
        The title used in the msd plot, note that this str is also added as a prefix to the ``plot_name``.
    show_plot : bool, default=False
        choose to show a plot of the fit
    plot_name : str, default="debye-waller.png"
        If ``save_plot==True`` the msd will be saved with the debye-waller factor marked. The ``title`` is added as a prefix to this str
    sigma_spline : float, default=None
        If the data should be smoothed, provide a value of sigma used in `scipy.ndimage.gaussian_filter1d <https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter1d.html>`_
    verbose : bool, default=False
        Will print intermediate values or not
    
    Returns
    -------
    debye-waller-parameter : float
        Instances where there is a minimum 
    tau : float
        Characteristic times associated with the Debye-Waller parameter values

    """

    if not dm.isiterable(time):
        raise ValueError("Given distances, time, should be iterable")
    else:
        time = np.array(time)
    if not dm.isiterable(msd):
        raise ValueError("Given radial distribution values, msd, should be iterable")
    else:
        msd = np.array(msd)
 
    if len(msd) != len(time):
        raise ValueError("Arrays for time and msd are not of equal length.")

    msd = msd[:int(len(time)*use_frac)]
    time = time[:int(len(time)*use_frac)]
    logtime = np.log10(time)
    logmsd = np.log10(msd)
    if np.isnan(logmsd[0]) or np.isinf(logtime[0]):
        logtime = logtime[1:]
        logmsd = logmsd[1:]
    if sigma_spline != None:
        logmsd = gaussian_filter1d(logmsd, sigma=sigma_spline)

    if np.all(np.isnan(logmsd)):
        raise ValueError("Spline could not be created with provided data:\n{}\n{}".format(time,msd))
    spline = InterpolatedUnivariateSpline( logtime, logmsd, k=5)
    dspline = spline.derivative()
    d2spline = dspline.derivative()
    extrema = d2spline.roots().tolist()
    extrema_concavity = dspline.derivative().derivative()
    
    n_min = 50
    dw = np.ones(n_min)*np.nan
    tau = np.ones(n_min)*np.nan
    min_value = np.ones(n_min)*np.inf
    i = 0
    for min_max in extrema:
        if extrema_concavity(min_max) > 0:
            tau[i] = 10**min_max
            dw[i] = 10**spline(min_max)
            min_value[i] = dspline(min_max)
            i += 1
        if i == n_min:
            break

    # Cut off minima after deepest
    ind_min = np.where(min_value==np.min(min_value))[0][0]
    min_value, dw, tau = min_value[ind_min], dw[ind_min], tau[ind_min]

    if np.isnan(dw):
        warnings.warn("This msd array does not contain a caged-region")
    elif verbose:
            print("Found debye waller factor to be {} at {}".format(dw, tau))

    if save_plot or show_plot:
        fig, axs = plt.subplots(1, 2, figsize=(6,4))
        axs[0].plot(time,msd,"k",label="Data", linewidth=0.5)
        if not np.isnan(dw):
            axs[0].plot([tau, tau],[0,np.max(msd)], linewidth=0.5)
            axs[0].set_xlim((time[0], 2*tau))
            ind = np.where(time < tau*2)[0][-1]
            axs[0].set_ylim((np.min(msd[:ind])*0.9, np.max(msd[:ind])))
        axs[0].set_xlabel("time")
        axs[0].set_ylabel("MSD")
        if title != None:
            axs[0].set_title(title)
        # log-log plot
        yarray = dspline(logtime)
        axs[1].plot(logtime, yarray,"k", linewidth=0.5)
        if not np.isnan(dw):
            axs[1].plot(np.log10([tau, tau]),[0,np.max(yarray)], linewidth=0.5)
            axs[1].set_xlim((logtime[0], np.log10(tau*2))) 
            ind = np.where(logtime < np.log10(tau*2))[0][-1]
            axs[1].set_ylim((np.min(yarray[:ind])*0.9, np.max(yarray[:ind])))
        axs[1].set_xlabel("log(t)")
        axs[1].set_ylabel("$d log(MSD) / d log(t)$")
        if title != None:
            axs[1].set_title(title)
        # save plot
        fig.tight_layout()
        if save_plot:
            if title is not None:
                tmp = os.path.split(plot_name)
                plot_name = os.path.join(tmp[0],title.replace(" ", "")+"_"+tmp[1])
            plt.savefig(plot_name,dpi=300)
        if show_plot:
            plt.show()
        plt.close("all")

    return dw, tau

def find_diffusivity(time, msd, min_exp=0.991, min_Npts=10, skip=1, show_plot=False, title=None, save_plot=False, plot_name="diffusivity.png", verbose=False, dim=3, use_frac=1, min_R2=0.97, bounds=(None,None)):
    """
    Analyzing the long-time msd, to extract the diffusivity.

    Parameters
    ----------
    time : numpy.ndarray
        Time array of the same length at MSD .
    msd : numpy.ndarray
        MSD array with one dimension.
    min_exp : float, default=0.991
        Minimum exponent value used to determine the longest acceptably linear region.
    min_Npts : int, default=10
        Minimum number of points in the "best" region outputted.
    skip : int, default=1
        Number of points to skip over in scanning different regions. A value of 1 will be most thorough, but a larger value will decrease computation time.
    min_R2 : float, default=0.97
        Minimum allowed coefficient of determination to consider proposed exponent. This prevents linearity from skipping over curves.
    save_plot : bool, default=False
        choose to save a plot of the fit
    title : str, default=None
        The title used in the msd plot, note that this str is also added as a prefix to the ``plot_name``.
    show_plot : bool, default=False
        choose to show a plot of the fit
    plot_name : str, default="diffusivity.png"
        If ``save_plot==True`` the msd will be saved with the debye-waller factor marked, The ``title`` is added as a prefix to this str
    dim : int, default=3
        Dimensions of the system, usually 3
    verbose : bool, default=False
        Will print intermediate values or not
    use_frac : float, default=1
        Choose what fraction of the msd to use. This will cut down on computational time in spending time on regions with poor statistics.
    bounds : tuple, default=(None,None)
        Values of time to act as the minimum or maximum of searching. It is recommended that the lower bound be ten times the timescale for the debye-waller parameter, see :func:`md_spa.msd.debye_waller`. This is applied after ``use_frac``
    
    Returns
    -------
    best : np.array
        Array containing the the following results that represent a region that most closely represents a slope of unity. This region must contain at least the minimum number of points, ``min_Npts``.

        - diffusivity (slope/2/dim)
        - standard error of diffusivity
        - time interval used to evaluate this slope
        - exponent of region (should be close to unity)
        - intercept
        - number of points in calculation

    longest : np.ndarray
        The results from the longest region that fits a linear model with an exponent of at least ``min_exp``. This array includes:

        - diffusivity
        - standard error of diffusivity
        - time interval used to evaluate this slope
        - exponent of region (should be close to unity)
        - intercept
        - number of points in calculation

    """

    if not dm.isiterable(time):
        raise ValueError("Given distances, time, should be iterable")
    else:
        time = np.array(time)
    if not dm.isiterable(msd):
        raise ValueError("Given radial distribution values, msd, should be iterable")
    else:
        msd = np.array(msd)

    if len(msd) != len(time):
        raise ValueError("Arrays for time and msd are not of equal length.")

    msd = msd[:int(len(time)*use_frac)]
    time = time[:int(len(time)*use_frac)]
    if bounds[0] is not None and not np.isnan(bounds[0]):
        inds = np.where(time > bounds[0])[0]
        if len(inds) > 0:
            ind = inds[0]
            msd = msd[ind:]
            time = time[ind:]
        else:
            raise ValueError("Provided minimum in time is greater that the time interval provided")
    if bounds[1] is not None and not np.isnan(bounds[1]):
        inds = np.where(time < bounds[1])[0]
        if len(inds) > 0:
            ind = inds[0]
            msd = msd[:ind]
            time = time[:ind]
        else:
            raise ValueError("Provided maximum in time is greater that the time interval provided")

    if min_Npts > len(time):
        warnings.warn("Resetting minimum number of points, {}, to be within length of provided data * use_frac, {}".format(min_Npts,len(time)))
        min_Npts = len(time)-1

    best = np.array([np.nan for x in range(7)])
    longest = np.array([np.nan for x in range(7)])
    for npts in range(min_Npts,len(time),skip):
        for i in range(0,len(time)-npts,skip):
            t_tmp = time[i:(i+npts)]
            msd_tmp = msd[i:(i+npts)]
            d_tmp, stder_tmp, exp_tmp, intercept, r2_tmp = diffusivity(t_tmp, msd_tmp, verbose=verbose, dim=dim)

            if r2_tmp > min_R2:
                if np.abs(exp_tmp-1.0) < np.abs(best[4]-1.0) or np.isnan(best[4]):
                    best = np.array([d_tmp, stder_tmp, t_tmp[0], t_tmp[-1], exp_tmp, intercept, npts])

                if (exp_tmp >=  min_exp and longest[-1] <= npts) or np.isnan(longest[4]):
                    if (longest[-1] < npts or np.abs(longest[4]-1.0) > np.abs(exp_tmp-1.0)) or np.isnan(longest[4]):
                        longest = np.array([d_tmp, stder_tmp, t_tmp[0], t_tmp[-1], exp_tmp, intercept, npts])

                if verbose:
                    print("Region Diffusivity: {} +- {}, from Time: {} to {}, with and exponent of {} using {} points, Exp Rsquared: {}".format(d_tmp, stder_tmp, t_tmp[0], t_tmp[-1], exp_tmp, npts, r2_tmp))

    if save_plot or show_plot:
        plt.plot(time,msd,"k",label="Data", linewidth=0.5)
        tmp_time = np.array([time[0],time[-1]])
        tmp_best = tmp_time*best[0]*2*dim+best[5]
        plt.plot(tmp_time,tmp_best, "g", label="Best", linewidth=0.5)
        tmp_longest = tmp_time*longest[0]*2*dim+longest[5]
        plt.plot(tmp_time,tmp_longest, "b", label="Longest", linewidth=0.5)
        plt.xlabel("time")
        plt.ylabel("MSD")
        if title != None:
            plt.title(title)
        plt.tight_layout()
        if save_plot:
            if title is not  None:
                tmp = os.path.split(plot_name)
                plot_name = os.path.join(tmp[0],title.replace(" ", "")+"_"+tmp[1])
            plt.savefig(plot_name,dpi=300)
        if show_plot:
            plt.show()
        plt.close("all")

    if verbose:
        print("Best Region Diffusivity: {} +- {}, from Time: {} to {}, with and exponent of {} using {} points".format(*best[:5],best[-1]))
        print("Longest Region Diffusivity: {} +- {}, from Time: {} to {}, with and exponent of {} using {} points".format(*best[:5],best[-1]))

    return best, longest

def msd(coords):
    """
    Calculate the MSD averaged over the number of particles and dimensions using FFT method described in DOI: 10.1051/sfn/201112010 

    Parameters
    ----------
    coords : numpy.ndarray
        (Nparticles, Ntime, Ndims) Matrix of coordinate values
    
    Returns
    -------
    msd : numpy.ndarray
        msd averaged over all particles and coordinates
    stderror : numpy.ndarray
        standard error calculated over particles

    """


    if len(np.shape(np.array(coords))) == 1:
        raise ValueError("An MSD cannot be calculated with a 1D array.")
    if len(np.shape(np.array(coords))) == 2:
        coords = np.array([coords])
    nparticles, npts, dims = np.shape(np.array(coords))

    for i in range(nparticles):
        coords[i] = coords[i]-coords[i][0]

    particle_msd = np.zeros((nparticles,npts, dims))
    DSQ = np.sum(np.square(coords), axis=2) # 2D (nparticles, npts)
    DSQ = np.concatenate((DSQ, np.zeros((nparticles,1))), axis=1)
    SUMSQ = 2*np.sum(DSQ, axis=1) # 1D (nparticles)

    particle_msd = np.zeros((nparticles,npts))
    for i,particle in enumerate(coords):
        Sab = np.zeros(npts)
        for dim in range(dims):
            Sab += dm.autocorrelation(particle[:,dim])

        for t in range(npts):
            SUMSQ[i] -= (DSQ[i,t-1] + DSQ[i,npts-t])
            particle_msd[i,t] = SUMSQ[i] / (npts - t) - 2*Sab[t]

    msd = np.mean(particle_msd, axis=0)
    if nparticles > 1:
        stderror = np.mean(msd, axis=0)/np.sqrt(nparticles)
    else:
        stderror = np.nan*np.ones(npts)

    return msd, stderror

def diffusivity(time, msd, verbose=False, dim=3):
    """
    Analyzing the long-time msd, to extract the diffusivity. This entire region is used and so should be linear.

    Parameters
    ----------
    time : numpy.ndarray
        Time array of the same length at MSD in picoseconds.
    msd : numpy.ndarray
        MSD array with one dimension in angstroms.
    verbose : bool, default=False
        Will print intermediate values or not
    dim : int, default=3
        Dimensions of the system, usually 3
    
    Returns
    -------
    diffusivity : float
        Diffusivity in meters squared per picosecond
    sterror : float
        Standard error of diffusivity
    exponent : float
        Exponent of fit data, should be close to unity
    intercept : float
        Intercept of time versus msd for plotting purposes
    r_squared : float
        Coefficient of determination for the linear fitted log-log plot, from which the exponent is derived.

    """

    if not dm.isiterable(time):
        raise ValueError("Given distances, time, should be iterable")
    else:
        time = np.array(time)
    if not dm.isiterable(msd):
        raise ValueError("Given radial distribution values, msd, should be iterable")
    else:
        msd = np.array(msd)

    if len(msd) != len(time):
        raise ValueError("Arrays for time and msd are not of equal length.")

    # Find Exponent
    t_log = np.log(time[1:]-time[0])
    msd_log = np.log(msd[1:]-msd[0])
    result = linregress(t_log,msd_log)
    exponent = result.slope
    r_squared = result.rvalue**2

    result = linregress(time,msd)
    diffusivity = result.slope/2/dim
    sterror = result.stderr/2/dim
    intercept = result.intercept

    return diffusivity, sterror, exponent, intercept, r_squared

    
