
import numpy as np
import matplotlib.pyplot as plt

from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.ndimage import gaussian_filter1d

import misc_modules.custom_plotting as cplot
import md_spa.custom_fit as cfit

def extract_gaussians(xdata, ydata, n_gaussians=None, normalize=False, kwargs_peaks={}, kwargs_fit={}, show_plot=False, save_plot=False, plot_name="n_gaussians.png"):
    """
    Fit parameters to a set of gaussian curves using ``custom_fit.n_gaussians``. If the number to fit to is not provided, then the number of gaussians is set to the number of maxima in the data set.

    Parameters
    ----------
    xdata : numpy.ndarray
        Independent dataset
    ydata : numpy.ndarray
        Dependent dataset
    n_gaussians : int, Optional, default=None
        The number of gaussian functions to fit to. If None the number of peaks is extracted and used as an initial guess.
    normalize : bool, Optional, default=False
        If True, the prefactors are scaled by the integral of the set of Gaussian functions from negative infinity to infinity. 
    kwargs_peaks : dict, Optional, default={}
        Keyword arguments used in ``custom_plotting.pull_extrema``
    kwargs_fit : dict, Optional, default={}
        Keyword arguments for ``custom_fit.n_gaussians``
    show_plot : bool, Optional, default=False
        Show comparison plot of each rdf being analyzed. Note that is option will interrupt the process until the plot is closed.
    save_fit : bool, Optional, default=False
        Save comparison plot of each rdf being analyzed. With the name ``plot_name``
    plot_name : str, Optional, default="n_gaussians.png"
        If `save_fit` is true, the generated plot is saved

    Returns
    -------
    parameters : numpy.ndarray
        An array of the dimensions (n_gaussians, 3) containing the parameters to define the gaussian functions that describe the input data.
    parameters : numpy.ndarray
        An array of the dimensions (n_gaussians, 3) containing the standard error for parameters
    redchi : float
        Reduced Chi^2 from ``lmfit.MinimizerResult`` 

    """

    if n_gaussians == None:
        _, maxima, _ = cplot.pull_extrema(xdata, ydata, **kwargs_peaks)
        n_gaussians = len(maxima)
        min_height = np.min(maxima.T[1])
        max_height = np.max(maxima.T[1])
        for i,max_pt in enumerate(maxima):
            if "kwargs_parameters" not in kwargs_fit:
                kwargs_fit["kwargs_parameters"] = {}
            kwargs_fit["kwargs_parameters"]["b{}".format(i+1)] = {"value": max_pt[0], "max": np.max(xdata), "min": np.min(xdata), "vary": False}
            kwargs_fit["kwargs_parameters"]["a{}".format(i+1)] = {"value": max_pt[1], "max": max_height, "min": min_height}
            kwargs_fit["kwargs_parameters"]["c{}".format(i+1)] = {"value": max_pt[0]/10}
    else:
        maxima = None

    if n_gaussians == None:
        # Fit parameters to set peak locations
        parameters, uncertainty, redchi = cfit.n_gaussians(xdata, ydata, len(maxima), **kwargs_fit)
        parameters = np.reshape(parameters, (len(maxima), 3))
        # Fit parameters with all free peak locations
        for n, (a,b,c) in enumerate(parameters):
            del kwargs_fit["kwargs_parameters"]["a{}".format(i+1)]["vary"]
            kwargs_fit["kwargs_parameters"]["b{}".format(i+1)]["value"] = b
            kwargs_fit["kwargs_parameters"]["c{}".format(i+1)]["value"] = c

    n_gaussians = len(maxima)    
    parameters, uncertainty, redchi = cfit.n_gaussians(xdata, ydata, n_gaussians, **kwargs_fit)
    parameters = np.reshape(parameters, (n_gaussians, 3))
    uncertainties = np.reshape(uncertainty, (n_gaussians, 3))

    if normalize:
        integral = 0
        for n in range(n_gaussians):
            integral += parameters[n][0]*parameters[n][2]*np.sqrt(2*np.pi)
        tmp = np.transpose(parameters)
        tmp[0] /= integral
        parameters = np.transpose(tmp)
        tmp = np.transpose(uncertainties)
        tmp[0] /= integral
        uncertainties = np.transpose(tmp)
        ydata /= integral

    if show_plot or save_plot:
        plt.plot(xdata,ydata,"k",label="Data")
        xarray2 = np.linspace(xdata[0],xdata[-1],int(1e+4))
        params = {}
        for i, (a,b,c) in enumerate(parameters):
            params["a{}".format(i+1)] = a
            params["b{}".format(i+1)] = b
            params["c{}".format(i+1)] = c
        yarray2 = cfit._res_n_gaussians(params, xarray2, np.zeros(len(xarray2)), n_gaussians)
        plt.plot(xarray2,yarray2,"r",linewidth=0.5,label="Fit")
        if np.all(maxima != None):
            for i in range(len(maxima)):
                plt.plot([maxima[i][0],maxima[i][0]],[min(ydata),max(ydata)],"c",linewidth=0.5)
        plt.xlim(xdata[0],xdata[-1])
        plt.tight_layout()
        if save_plot:
            plt.savefig(plot_name.replace(" ","_"), dpi=300)
        if show_plot:
            plt.show()
        plt.close()

    return parameters, uncertainties, redchi

def pull_extrema( xarray, yarray, smooth_sigma=None, error_length=25, extrema_cutoff=0.0, show_plot=False, save_plot=False, plot_name="extrema.png"):
    """
    Pull minima, maxima, and inflection points from x-y data.

    Parameters
    ----------
    xdata : numpy.ndarray
        independent data
    ydata : numpy.ndarray
        dependent data
    smooth_sigma : float, Optional, default=None
        If the data should be smoothed, provide a value of sigma used in ``scipy gaussian_filter1d``
    error_length : int, Optional, default=25
        The number of extrema found to trigger an error. This indicates the data is noisy and should be smoothed. 
    extrema_cutoff : float, Optional, default=0.0
        All peaks with an absolute value of gr that is less than this value are ignored. If values that are expects are not returned, try adding a small value of `smooth_sigma` as minute fluculations in a noninteresting beginning part of the array may be at fault.
    show_plot : bool, Optional, default=False
        Show comparison plot of each rdf being analyzed. Note that is option will interrupt the process until the plot is closed.
    save_fit : bool, Optional, default=False
        Save comparison plot of each rdf being analyzed. With the name ``plot_name``
    plot_name : str, Optional, default="extrema.png"
        If `save_fit` is true, the generated plot is saved
        
    Returns
    -------
    minima : numpy.ndarray
        All minima in an array of size 2 by Nminima. Where ``minima[0]`` is the x value corresponding to the minima and ``minima[1]`` is the y value
    maxima : numpy.ndarray
        All maxima in an array of size 2 by Nmaxima. Where ``maxima[0]`` is the x value corresponding to the maxima and ``maxima[1]`` is the y value
    inflections : numpy.ndarray
        All inflection points in an array of size 2 by Ninflections. Where ``inflections[0]`` is the x value corresponding to the inflection point and ``inflection[1]`` is the y value

    """
    #######
    #if smooth_sigma == None: # Trying to automate choosing a smoothing value
    #    Npts_avg = 20
    #    stderror = 1e-5
    #    sigma_min = 1.1
    #    window_len = (np.std(yarray[-Npts_avg:])/stderror)**2
    #    smooth_sigma = (window_len-1)/6.0
    #    print(smooth_sigma, window_len, np.std(yarray[-Npts_avg:]))
    #    if smooth_sigma < sigma_min:
    #        smooth_sigma = sigma_min 
    #print(smooth_sigma)
    #yarray = gaussian_filter1d(yarray, sigma=smooth_sigma)
    #######
    if smooth_sigma != None:
        yarray = gaussian_filter1d(yarray, sigma=smooth_sigma)
    ######

    spline = InterpolatedUnivariateSpline(xarray,yarray, k=4)
    extrema = spline.derivative().roots().tolist()
    extrema = [x for x in extrema if np.abs(spline(x))>extrema_cutoff]

    if len(extrema) > error_length:
        if show_plot:
            plt.plot(xarray,yarray,"k",label="Data")
            plt.plot([xarray[0],xarray[-1]],[1,1],"k",linewidth=0.5)
            plt.plot([xarray[0],xarray[-1]],[0,0],"k",linewidth=0.5)
            r2 = np.linspace(xarray[0],xarray[-1],int(1e+4))
            gr2 = spline(r2)
            for tmp in extrema:
                plt.plot([tmp,tmp],[0,np.max(yarray)],"c",linewidth=0.5)
            plt.plot(r2,gr2,"r",label="Spline",linewidth=0.5)
            plt.show()
        raise ValueError("Found {} extrema, consider smoothing the data with `smooth_sigma` option.".format(len(extrema)))
    tmp_spline = spline.derivative().derivative()
    concavity = tmp_spline(extrema)

    maxima = []
    minima = []
    for i,rtmp in enumerate(extrema):
        if concavity[i] > 0:
            minima.append([rtmp, spline(rtmp)])
        else:
            maxima.append([rtmp, spline(rtmp)])

    inflections = []
    tmp_inflections = InterpolatedUnivariateSpline(xarray,yarray, k=5).derivative().derivative().roots().tolist()
    tmp_inflections = [x for x in tmp_inflections if np.abs(spline(x))>extrema_cutoff]
    for rtmp in tmp_inflections:
        inflections.append([rtmp, spline(rtmp)])

    if show_plot or save_plot:
        plt.plot(xarray,yarray,"k",label="Data")
        xarray2 = np.linspace(xarray[0],xarray[-1],int(1e+4))
        yarray2 = spline(xarray2)
        plt.plot(xarray2,yarray2,"r",linewidth=0.5,label="Spline")
        for i in range(len(maxima)):
            plt.plot([maxima[i][0],maxima[i][0]],[min(yarray),max(yarray)],"c",linewidth=0.5)
        for i in range(len(minima)):
            plt.plot([minima[i][0],minima[i][0]],[min(yarray),max(yarray)],"b",linewidth=0.5)
        for i in range(len(inflections)):
            plt.plot([inflections[i][0],inflections[i][0]],[min(yarray),max(yarray)],"r",linewidth=0.5)
        plt.xlim(xarray[0],xarray[-1])
        plt.tight_layout()
        if save_plot:
            plt.savefig(plot_name, dpi=300)
        if show_plot:
            plt.show()
        plt.close()

    return np.array(minima).T, np.array(maxima).T, np.array(inflections).T

