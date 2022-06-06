
import numpy as np
import scipy.stats
import warnings

def basic_stats(data, confidence=0.95, error_type="standard_error"):
    """
    Given a set of data, calculate the mean and standard error

    Valued of NaN are removed from the data set.

    Parameters
    ----------
    data : numpy.ndarray
        1D list or array of data
    confidence : float, Optional, default=0.95
        Confidence Interval certainty, used when ``error_type = "confidence"``
    error_type : str, Optional, default="standard_error"
        Type of error to be output, can be "standard_error" or "confidence", or "standard_dev"

    Returns
    -------
    mean : float
        Average value
    std_error : float
        Standard error of the data
    interval : float
        When added and subtracted from the mean, forms the confidence interval
        
    """

    if not isiterable(data):
        raise ValueError("Input data is not iterable")
 
    if len(data) != 0 and len(data) != np.isnan(data).sum():
        data = np.array(data,np.float)
        lx = len(data) - np.isnan(data).sum()
        se = np.nanstd(data)/np.sqrt(lx)
        if error_type == "standard_error":
            std = se
        elif error_type == "confidence":
            std = se * scipy.stats.t.ppf((1 + confidence) / 2., lx-1)
        elif error_type == "standard_dev":
            std = np.nanstd(data)
        else:
            raise ValueError("error_type, {}, is not supported".format(error_type))
        mean = np.nanmean(data)
        if lx > 8:
            tmp = scipy.stats.normaltest(data).pvalue
            if tmp < 0.05:
                warning.warn("This dataset is not normal according to scipy.normaltest() with a pvalue={}".format(tmp))
    else:
        mean = np.nan
        std = np.nan

    return mean, std

def skewness(data, kwargs={}):
    """
    Given a set of data, calculate the skewness and its standard error. If skewness/SE is greater than 1.96 then the distribution is not in the 95% confidence interval of normality. By default the adjusted Fisher-Pearson standardized moment coefficient to correct for sample bias with the default kwargs.

    Valued of NaN are removed from the data set.

    Parameters
    ----------
    data : numpy.ndarray
        1D list or array of data
    kwargs : dict, Optional, default={"bias": False, "nan_policy": "omit"}
        Keyword arguments for ``scipy.stats.skew``

    Returns
    -------
    skewness : float
        By default the adjusted Fisher-Pearson skewness is calculated with ``scipy.stats.shew``
    skew_se : float
        Standard error of the skewness that is meaningful for the adjusted Fisher-Pearson skewness and is the square root of 6*n*(n-1)/((n-2)*(n+1)*(n+3)).
        
    """

    tmp_kwargs = {"bias": False, "nan_policy": "omit"}
    tmp_kwargs.update(kwargs)

    if not isiterable(data):
        raise ValueError("Input data is not iterable")
 
    if len(data) != 0 or len(data) != np.isnan(data).sum():
        data = np.array(data,np.float)
        lx = len(data) - np.isnan(data).sum()
        skewness = scipy.stats.skew(data, **tmp_kwargs)
        skew_se = np.sqrt(6.*lx*(lx-1.)/((lx-2.)*(lx+1.)*(lx+3.)))

    else:
        skewness = np.nan
        skew_se = np.nan

    return skewness, skew_se

def isiterable(array):
    """
    Check if variable is an iterable type with a length (e.g. np.array or list)

    Note that this could be test is ``isinstance(array, Iterable)``, however ``array=np.array(1.0)`` would pass that test and then fail in ``len(array)``.

    Taken from github.com/jaclark5/despasito

    Parameters
    ----------
    array
        Variable of some type, that should be iterable

    Returns
    -------
    isiterable : bool
        Will be True if indexing is possible and False is not

    """

    array_tmp = np.array(array, dtype=object)
    tmp = np.shape(array_tmp)

    if tmp:
        isiterable = True
    else:
        isiterable = False

    return isiterable

def isfloat(string):
    """
    Check if string variable is actually a float. This function allows exponential notation.

    Parameters
    ----------
    string
        String that may or may not be a float

    Returns
    -------
    isfloat : bool
        Will be True if the string can be converted into a float

    """

    try:
        float(string)
        flag = True
    except:
        flag = False

    return flag

def array2dict(array, keys):
    """
    Array to dict will group values into a dictionary

    Parameters
    ----------
    array : list
        List of lists of equal length. The first index is used as a key in the resulting dictionary
    keys : list[str]
        Strings representing each entry after the key, so ``len(array[i])`` should be one plus the length of ``keys``
   
    Returns
    -------
    dictionary : dict
        Dictionary of values
    """

    dictionary = {}
    for line in array:
       if line[0] not in dictionary:
           dictionary[line[0]] = {key: [] for key in keys}
       if len(keys) != len(line[1:]):
           raise ValueError("The number of keys must equal the number of entries len(array[i][1:])")
       for i in range(1,len(line)):
           dictionary[line[0]][keys[i-1]].append(line[i])

    return dictionary

def autocorrelation(x, mode="fft"):
    """
    Calculate the Autocorrelation function using FFT and multiple time origins.

    Parameters
    ----------
    x : numpy.ndarray
        Input function for which to calculate the autocorrelation function
    mode : str, Optional, default="fft"
        Method of calculating the autocorrelation function. FFT is two orders of magnitude faster than the ``loop`` method, and twice as fast as the numpy.correlate.
       
        - fft: Using Fourier transform to calculate the autocorrelation funct
        - numpy: Use np.correlate with multiple start times
        - loop: Hard coded loop taken from methematical definition

    Returns
    -------
    Cx : numpy.ndarray
        Autocorrelation function
    """

    lx = len(x)
    norm = (lx-np.arange(0,lx))

    if mode == "fft":
        Cx = np.fft.ifft( np.abs(np.fft.fft(x, n=2*lx))**2)[:lx].real
    elif mode == "numpy":
        Cx = np.correlate(x, x, mode='full')[lx-1:]
    elif mode == "loop":
        Cx = np.zeros(lx)
        for j in range(lx):
            Cx[:lx-j] += x[j]*x[j:]
    else:
        raise ValueError("The autocorrelation method, {}, is not supported".format(mode))

    return Cx/norm

def remove_duplicate_pairs(array):
    """
    Given an iterable list return entries with unique values for the first two indices

    Parameters
    ----------
    array : list
        Iterable strucure with a second dimension of at least two

    Returns
    -------
    new_array : list
        Iterable strucure without repeating entries

        
    """

    if not isiterable(array):
        raise ValueError("Provided array should be iterable")
    if array and (not isiterable(array[0]) or len(array[0]) < 2):
        raise ValueError("Each element in the second dimension must be iterable and at least of length two.")

    new_array = []
    for tmp_set in array:
        if tmp_set[0] not in [tmp[0] for tmp in new_array]:
            new_array.append(tmp_set)
        elif tmp_set[1] not in [tmp for tmp in [tmp2[1] for tmp2 in new_array if tmp2[0]==tmp_set[0]]]:
            new_array.append(tmp_set)

    return new_array
