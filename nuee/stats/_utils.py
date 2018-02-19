import numpy as np
import scipy as sp
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy.stats import f as ssf



def corr(x, y=None):
    """Computes correlation between columns of `x`, or `x` and `y`.
    Correlation is covariance of (columnwise) standardized matrices,
    so each matrix is first centered and scaled to have variance one,
    and then their covariance is computed.
    Parameters
    ----------
    x : 2D array_like
        Matrix of shape (n, p). Correlation between its columns will
        be computed.
    y : 2D array_like, optional
        Matrix of shape (n, q). If provided, the correlation is
        computed between the columns of `x` and the columns of
        `y`. Else, it's computed between the columns of `x`.
    Returns
    -------
    correlation
        Matrix of computed correlations. Has shape (p, p) if `y` is
        not provided, else has shape (p, q).
    """
    x = np.asarray(x)
    if y is not None:
        y = np.asarray(y)
        if y.shape[0] != x.shape[0]:
            raise ValueError("Both matrices must have the same number of rows")
        x, y = scale(x), scale(y)
    else:
        x = scale(x)
        y = x
    # Notice that scaling was performed with ddof=0 (dividing by n,
    # the default), so now we need to remove it by also using ddof=0
    # (dividing by n)
    return x.T.dot(y) / x.shape[0]


def scale(a, weights=None, with_mean=True, with_std=True, ddof=0, copy=True):
    """Scale array by columns to have weighted average 0 and standard
    deviation 1.
    Parameters
    ----------
    a : array_like
        2D array whose columns are standardized according to the
        weights.
    weights : array_like, optional
        Array of weights associated with the columns of `a`. By
        default, the scaling is unweighted.
    with_mean : bool, optional, defaults to True
        Center columns to have 0 weighted mean.
    with_std : bool, optional, defaults to True
        Scale columns to have unit weighted std.
    ddof : int, optional, defaults to 0
        If with_std is True, variance is calculated by dividing by `n
        - ddof` (where `n` is the number of elements). By default it
        computes the maximum likelyhood stimator.
    copy : bool, optional, defaults to True
        Whether to perform the standardization in place, or return a
        new copy of `a`.
    Returns
    -------
    2D ndarray
        Scaled array.
    Notes
    -----
    Wherever std equals 0, it is replaced by 1 in order to avoid
    division by zero.
    """
    if copy:
        a = a.copy()
    a = np.asarray(a, dtype=np.float64)
    avg, std = mean_and_std(a, axis=0, weights=weights, with_mean=with_mean,
                            with_std=with_std, ddof=ddof)
    if with_mean:
        a -= avg
    if with_std:
        std[std == 0] = 1.0
        a /= std
    return a


def mean_and_std(a, axis=None, weights=None, with_mean=True, with_std=True,
                 ddof=0):
    """Compute the weighted average and standard deviation along the
    specified axis.
    Parameters
    ----------
    a : array_like
        Calculate average and standard deviation of these values.
    axis : int, optional
        Axis along which the statistics are computed. The default is
        to compute them on the flattened array.
    weights : array_like, optional
        An array of weights associated with the values in `a`. Each
        value in `a` contributes to the average according to its
        associated weight. The weights array can either be 1-D (in
        which case its length must be the size of `a` along the given
        axis) or of the same shape as `a`. If `weights=None`, then all
        data in `a` are assumed to have a weight equal to one.
    with_mean : bool, optional, defaults to True
        Compute average if True.
    with_std : bool, optional, defaults to True
        Compute standard deviation if True.
    ddof : int, optional, defaults to 0
        It means delta degrees of freedom. Variance is calculated by
        dividing by `n - ddof` (where `n` is the number of
        elements). By default it computes the maximum likelyhood
        estimator.
    Returns
    -------
    average, std
        Return the average and standard deviation along the specified
        axis. If any of them was not required, returns `None` instead
    """
    if not (with_mean or with_std):
        raise ValueError("Either the mean or standard deviation need to be"
                         " computed.")
    a = np.asarray(a)
    if weights is None:
        avg = a.mean(axis=axis) if with_mean else None
        std = a.std(axis=axis, ddof=ddof) if with_std else None
    else:
        avg = np.average(a, axis=axis, weights=weights)
        if with_std:
            if axis is None:
                variance = np.average((a - avg)**2, weights=weights)
            else:
                # Make sure that the subtraction to compute variance works for
                # multidimensional arrays
                a_rolled = np.rollaxis(a, axis)
                # Numpy doesn't have a weighted std implementation, but this is
                # stable and fast
                variance = np.average((a_rolled - avg)**2, axis=0,
                                      weights=weights)
            if ddof != 0:  # Don't waste time if variance doesn't need scaling
                if axis is None:
                    variance *= a.size / (a.size - ddof)
                else:
                    variance *= a.shape[axis] / (a.shape[axis] - ddof)
            std = np.sqrt(variance)
        else:
            std = None
        avg = avg if with_mean else None
    return avg, std

def ellipse(X, level=0.95, method='deviation', npoints=100):
    """
    X: data, 2D numpy array with 2 columns
    level: confidence level
    method: either 'deviation' (swarning data) or 'error (swarning the mean)'
    npoints: number of points describing the ellipse
    """
    cov_mat = np.cov(X.T)
    dfd = X.shape[0]-1
    dfn = 2
    center = np.apply_along_axis(np.mean, arr=X, axis=0) # np.mean(X, axis=0)
    if method == 'deviation':
        radius = np.sqrt(2 * ssf.ppf(q=level, dfn=dfn, dfd=dfd))
    elif method == 'error':
        radius = np.sqrt(2 * ssf.ppf(q=level, dfn=dfn, dfd=dfd)) / np.sqrt(X.shape[0])
    else:
        raise ValueError("Method should be either 'deviation' or 'error'.")
    angles = (np.arange(0,npoints+1)) * 2 * np.pi/npoints
    circle = np.vstack((np.cos(angles), np.sin(angles))).T
    ellipse = center + (radius * np.dot(circle, np.linalg.cholesky(cov_mat).T).T).T
    return ellipse


def mardia_test(data, cov=True):
    if not isinstance(data, np.ndarray):
        raise ValueError('data must be a numpy array')
    if data.shape[1] < 2:
        raise ValueError("number of variables must be equal or greater than 2")

    n = data.shape[0]
    p = data.shape[1]

    data_c = np.apply_along_axis(func1d=lambda x: x-np.mean(x), axis=0, arr=data)

    if cov:
        S = ((n - 1)/n) * np.cov(data.T)
    else:
        S = np.cov(data.T)

    D = data_c.dot(np.linalg.inv(S).dot(data_c.T))
    g1p = np.sum(D**3)/n**2
    g2p = np.sum(np.diag((D**2)))/n
    df = p * (p + 1) * (p + 2)/6
    k = (p + 1) * (n + 1) * (n + 3)/(n * ((n + 1) * (p + 1) - 6))

    small_skew = n * k * g1p/6
    skew = n * g1p/6
    kurt = (g2p - p * (p + 2)) * np.sqrt(n/(8 * p * (p + 2)))
    p_skew = sp.stats.chi2.sf(x=skew, df=df)
    p_small = sp.stats.chi2.sf(x=small_skew, df=df)
    p_kurt = 2 * sp.stats.norm.sf(np.abs(kurt))

    return {'g1p': g1p, 'chi_skew': skew, 'P-value skew': p_skew, 'Chi small skew': small_skew, 'P-value small': p_small, 'g2p': g2p, 'Z kurtosis': kurt, 'P-value kurtosis': p_kurt}

def box_mtest(data, groups):
    """
    data: a float numpy array
    """
    import scipy as sp
    import numpy as np

    if not isinstance(data, np.ndarray):
        raise ValueError('data must be a numpy array')
    if data.dtype != 'float64':
        raise ValueError('data must be a numpy array of type float64')

    p = data.shape[1]
    unique_categories = list(set(groups)) # lev
    n_categories = len(unique_categories) # nlev

    degrees_of_freedom = np.zeros(n_categories) # dofs
    log_of_det = np.zeros(n_categories)
    covariances = {}
    aux = {}
    pooled = np.zeros((p, p))


    for i in range(len(unique_categories)):
        degrees_of_freedom[i] = data[groups==unique_categories[i], :].shape[0]-1
        covariances[unique_categories[i]] = np.cov(data[groups==unique_categories[i], :].T)
        pooled = pooled + covariances[unique_categories[i]] * degrees_of_freedom[i]
        log_of_det[i] = np.log(np.linalg.det(covariances[unique_categories[i]]))

    if not np.any(degrees_of_freedom) < p:
        print("Warning: one or more categories with less observations than variables")

    tot_dof = degrees_of_freedom.sum()
    tot_inv_dof = (1/degrees_of_freedom).sum()
    pooled = pooled/tot_dof

    boxlog = degrees_of_freedom.sum() * np.log(np.linalg.det(pooled)) - np.sum(log_of_det * degrees_of_freedom)
    co = (((2 * p**2) + (3 * p) - 1)/(6 * (p + 1) * (n_categories - 1))) * (tot_inv_dof - (1/tot_dof))
    chisq = boxlog * (1 - co)
    dof_chisq = (sp.misc.comb(p, 2) + p) * (n_categories - 1)

    p_value = sp.stats.chi2.sf(x=chisq, df=dof_chisq)

    return({'Chi-squared': chisq,
            'Parameter': dof_chisq,
            'P-value': p_value,
            'Covariances': covariances,
            'Pooled covariances': pooled,
            'Log of determinants': log_of_det})

def pairsplot(x, level=0.05):
    if isinstance(x, pd.DataFrame):
        x = x.as_matrix()
    shape = [x.shape[1], x.shape[1]]
    plot_id = 1
    for i in range(shape[0]):
        for j in range(shape[1]):
            ax1 = plt.subplot(shape[0], shape[1], plot_id)
            if (i<j):
                correlation = stats.pearsonr(x[:,i], x[:,j])
                if correlation[1] < level:
                    corr_sign = '*'
                else:
                    corr_sign = ''
                plt.axis('off')
                plt.text(0.5, 0.5, str(np.round(correlation[0], 2))+corr_sign, ha='center', va='center', size=20)
            elif (i==j):
                plt.hist(x[:,i])
            else:
                ax1.plot(x[:,j], x[:,i], '.')
            if i<(shape[0]-1):
                ax1.get_xaxis().set_visible(False)
            if j>0:
                ax1.get_yaxis().set_visible(False)
            if (j==0) and (i==0):
                ax1.get_yaxis().set_visible(False)
            plot_id += 1
