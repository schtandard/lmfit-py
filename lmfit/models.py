import numpy as np
from .model import Model
from .lineshapes import (gaussian, lorentzian, voigt,
                         exponential,
                         powerlaw, linear, parabolic)

class DimensionalError(Exception):
    pass

def _validate_1d(independent_vars):
    if len(independent_vars) != 1:
        raise DimensionalError(
            "This model requires exactly one independent variable.")

def index_of(arr, val):
    """return index of array nearest to a value
    """
    if val < min(arr):
        return 0
    return np.abs(arr-val).argmin()

def estimate_peak(y, x, negative):
    "estimate amp, cen, sigma for a peak"
    if x is None:
        return 1.0, 0.0, 1.0
    maxy, miny = max(y), min(y)
    maxx, minx = max(x), min(x)
    imaxy = index_of(y, maxy)
    cen = x[imaxy]
    amp = (maxy - miny)*1.5
    sig = (maxx-minx)/6.0

    halfmax_vals = np.where(y > (maxy+miny)/2.0)[0]
    if negative:
        imaxy = index_of(y, miny)
        amp = -(maxy - miny)*1.5
        halfmax_vals = np.where(y < (maxy+miny)/2.0)[0]
    if len(halfmax_vals) > 2:
        sig = (x[halfmax_vals[-1]] - x[halfmax_vals[0]])/2.0
    return amp, cen, sig

COMMON_DOC = """

Parameters
----------
independent_vars: list of strings to be set as variable names
missing: None, 'drop', or 'raise'
    None: Do not check for null or missing values.
    'drop': Drop null or missing observations in data.
        Use pandas.isnull if pandas is available; otherwise,
        silently fall back to numpy.isnan.
    'raise': Raise a (more helpful) exception when data contains null
        or missing values.
suffix: string to append to paramter names, needed to add two Models that
    have parameter names in common. None by default.
"""
class ConstantModel(Model):
    __doc__ = "x -> c" + COMMON_DOC
    def __init__(self, **kwargs):
        def func(x, c):
            return c
        super(ConstantModel, self).__init__(func, **kwargs)

    def guess_starting_values(self, data, **kwargs):
        self.params['%sc' % self.prefix].value = data.mean()
        self.has_initial_guess = True

class LinearModel(Model):
    __doc__ = linear.__doc__ + COMMON_DOC
    def __init__(self, **kwargs):
        super(LinearModel, self).__init__(linear, **kwargs)

    def guess_starting_values(self, data, x=None, **kwargs):
        sval, oval = 0., 0.
        if x is not None:
            sval, oval = np.polyfit(x, data, 1)
        self.params['%sintercept' % self.prefix].value = oval
        self.params['%sslope' % self.prefix].value = sval
        self.has_initial_guess = True

class QuadraticModel(Model):
    __doc__ = parabolic.__doc__ + COMMON_DOC
    def __init__(self, **kwargs):
        super(QuadraticModel, self).__init__(parabolic, **kwargs)

    def guess_starting_values(self, data, x=None, **kwargs):
        a, b, c = 0., 0., 0.
        if x is not None:
            a, b, c = np.polyfit(x, data, 2)
        self.params['%sa' % self.prefix].value = a
        self.params['%sb' % self.prefix].value = b
        self.params['%sc' % self.prefix].value = c
        self.has_initial_guess = True

ParabolicModel = QuadraticModel

class PolynomialModel(Model):
    __doc__ = "x -> c0 + c1 * x + c2 * x**2 + ... c7 * x**7" + COMMON_DOC
    MAX_DEGREE=7
    DEGREE_ERR = "degree must be an integer less than %d."
    def __init__(self, deg, **kwargs):
        if not isinstance(deg, int)  or deg > self.MAX_DEGREE:
            raise TypeError(self.DEGREE_ERR % self.MAX_DEGREE)

        self.poly_degree = deg
        pnames = ['c%i' % (i) for i in range(deg + 1)]
        kwargs['param_names'] = pnames

        def polynomial(x, c0=0, c1=0, c2=0, c3=0, c4=0, c5=0, c6=0, c7=0):
            out = np.zeros_like(x)
            args = dict(c0=c0, c1=c1, c2=c2, c3=c3,
                        c4=c4, c5=c5, c6=c6, c7=c7)
            for i in range(self.poly_degree+1):
                out += x**i * args.get('c%i' % i, 0)
            return out
        super(PolynomialModel, self).__init__(polynomial, **kwargs)

    def guess_starting_values(self, data, x=None, **kws):
        coefs = np.zeros(self.MAX_DEGREE+1)
        if x is not None:
            out = np.polyfit(x, data, self.poly_degree)
            for i, coef in enumerate(out[::-1]):
                coefs[i] = coef
        for i in range(self.poly_degree+1):
            self.params['%sc%i' % (self.prefix, i)].value = coefs[i]
        self.has_initial_guess = True


class GaussianModel(Model):
    __doc__ = gaussian.__doc__ + COMMON_DOC
    fwhm_factor = 2.354820
    def __init__(self, **kwargs):
        super(GaussianModel, self).__init__(gaussian, **kwargs)
        self.params.add('%sfwhm' % self.prefix,
                        expr='%.6f*%ssigma' % (self.fwhm_factor, self.prefix))

    def guess_starting_values(self, data, x=None, negative=False, **kwargs):
        amp, cen, sig = estimate_peak(data, x, negative)
        self.params['%samplitude' % self.prefix].value = amp
        self.params['%scenter' % self.prefix].value = cen
        self.params['%ssigma' % self.prefix].value = sig
        self.has_initial_guess = True

class LorentzianModel(Model):
    __doc__ = lorentzian.__doc__ + COMMON_DOC
    fwhm_factor = 2.0
    def __init__(self, **kwargs):
        super(LorentzianModel, self).__init__(lorentzian, **kwargs)
        self.params.add('%sfwhm' % self.prefix,
                        expr='%.7f*%ssigma' % (self.fwhm_factor,
                                               self.prefix))

    def guess_starting_values(self, data, x=None, negative=False, **kwargs):
        amp, cen, sig = estimate_peak(data, x, negative)
        self.params['%samplitude' % self.prefix].value = amp
        self.params['%scenter' % self.prefix].value = cen
        self.params['%ssigma' % self.prefix].value = sig
        self.has_initial_guess = True

class VoigtModel(Model):
    __doc__ = voigt.__doc__ + COMMON_DOC
    fwhm_factor = 3.60131
    def __init__(self, **kwargs):
        super(VoigtModel, self).__init__(voigt, **kwargs)
        self.params.add('%sfwhm' % self.prefix,
                        expr='%.7f*%ssigma' % (self.fwhm_factor,
                                               self.prefix))

    def guess_starting_values(self, data, x=None, negative=False, **kwargs):
        amp, cen, sig = estimate_peak(data, x, negative)
        self.params['%samplitude' % self.prefix].value = amp
        self.params['%scenter' % self.prefix].value = cen
        self.params['%ssigma' % self.prefix].value = sig
        self.has_initial_guess = True

class PowerLawModel(Model):
    __doc__ = powerlaw.__doc__ + COMMON_DOC
    def __init__(self, **kwargs):
        super(PowerLawModel, self).__init__(powerlaw, **kwargs)

    def guess_starting_values(self, data, x=None, **kws):
        try:
            expon, amp = np.polyfit(log(x+1.e-14), log(data+1.e-14), 1)
        except:
            expon, amp = 1, np.log(abs(max(data)+1.e-9))
        self.params['amplitude'].value = np.exp(amp)
        self.params['exponent'].value = expon
        self.has_initial_guess = True

class ExponentialModel(Model):
    __doc__ = exponential.__doc__ + COMMON_DOC
    def __init__(self, **kwargs):
        super(ExponentialModel, self).__init__(exponential, **kwargs)

    def guess_starting_values(self, data, x=None, **kws):
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        self.params['amplitude'].value = np.exp(oval)
        self.params['decay'].value = -1/sval
        self.has_initial_guess = True
