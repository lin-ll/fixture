from scipy.interpolate import interp1d
from fixture import template_master
import fixture.modal_analysis as modal_analysis
import numpy as np

def plot(x, y, legend = None):
    print('called to plot')
    import matplotlib.pyplot as plt
    if type(y) != tuple:
        y = (y,)
    for y in y:
        plt.plot(x, y, '-*')
    if legend:
        plt.legend(legend)
    plt.grid()
    plt.show()

def extract_pzs(nps, nzs, x, y):
    def pad(xs, n):
        if len(xs) == n:
            return xs
        elif len(xs) > n:
            return sorted(xs)[:n]
        else:
            return xs + [float('inf')]*(n - len(xs))
    # TODO
    if type(x) == list:
        x = np.array(x)
    if type(y) == list:
        y = np.array(y)

    if len(x) <= 1:
        # happens when y is constant - only one datapoint
        return (pad([], nps), pad([], nzs))

    #print(x)
    #print(y)
    #plot(x, y)
    first_good_index = np.where(x > 0)[0][0]
    x_trimmed = x[first_good_index:]
    y_trimmed = y[first_good_index:]


    # TODO delete this
    y_trimmed += np.random.normal(0, .001, y_trimmed.shape)

    ma = modal_analysis.ModalAnalysis(rho_threshold=1, N_degree=max(nps, nzs))
    #tf = ma.fit_stepresponse(y - y[0], x)

    # step response fit will always start from exactly zero
    tf = ma.fit_step_response_direct(x_trimmed, y_trimmed, nps, nzs)
    zs = np.roots(tf['num']) / (2*np.pi)
    ps = np.roots(tf['den']) / (2*np.pi)
    print('GOT PZs')
    print(ps, zs)
    ps, zs = np.abs(ps), np.abs(zs)

    #bode_plot(ps, zs)

    return (pad(ps, nps), pad(zs, nzs))


def dynamic(template):
    # NOTE: the only reason I inherit directly from TemplateMaster
    # here is because I check whether a class is a template by checking
    # whether it's a direct subclass of TemplateMaster
    class Dynamic(template, template_master.TemplateMaster):
        dynamic_reads = {}

        # create function for reading transient in run_single_test
        @classmethod
        def read_transient(self, tester, port, duration):
            r = tester.read(port, style='block', params={'duration':duration})
            self.dynamic_reads[port] = r

        # wrap run_single_test to return read_transient
        @classmethod
        def run_single_test(self, *args, **kwargs):
            ret = super().run_single_test(*args, **kwargs)
            err = ('If you use the Dynamic Template type, you must call '
                'read_transient in your run_single_test!')
            assert len(self.dynamic_reads) > 0, err
            dynamic_reads = self.dynamic_reads
            self.dynamic_reads = {}
            return (ret, dynamic_reads)

        # wrap process_single_test to process the block read
        @classmethod
        def process_single_test(self, reads, *args, **kwargs):
            # we purposely put dynamic_reads in a scope the template creator
            # can access so that they can edit it before we process
            reads_orig, block_reads = reads
            self.dynamic_reads = {p:r.value for p,r in block_reads.items()}
            for p,r in self.dynamic_reads.items():
                print('p')
                if len(r[0]) < 100:
                    print('PROBLEM WITH r')
                    pass
                print(len(r[0]))
            ret_dict = super().process_single_test(reads_orig, *args, **kwargs)
            for port, (x,y) in self.dynamic_reads.items():

                ps, zs = extract_pzs(1, 0, x, y)
                p1 = ps[0]

                # add these ps zs to parameter algebra if they are not already there
                def add_to_p_a(name):
                    if not name in [n for n, _ in self.parameter_algebra]:
                        self.parameter_algebra.append((name, {name:'1'}))
                for n,p in enumerate(ps):
                    name = f'{self.get_name(port)}_p{n}'
                    add_to_p_a(name)
                for n,z in enumerate(zs):
                    name = f'{self.get_name(port)}_z{n}'
                    add_to_p_a(name)


                # add to the dict so they can be used for regression later
                ret_dict[name] = p1
            return ret_dict

    return Dynamic

def bode_plot(ps, zs):
    import matplotlib.pyplot as plt
    import numpy as np
    N = 100
    fmin = min(abs(np.real(ps + zs)))
    fmax = max(abs(np.real(ps + zs)))
    fs = np.logspace(np.floor(np.log10(fmin))-1, np.ceil(np.log10(fmax))+1, N)
    ys = np.ones(N, dtype=np.complex128)
    for z in zs:
        if z == 0:
            ys *= fs * 1j
        else:
            ys *= (1 + fs * 1j / z)
    for p in ps:
        if p == 0:
            ys /= fs * 1j
        else:
            ys /= (1 + fs * 1j / p)

    top = plt.subplot(2, 1, 1)
    top.grid()
    top.loglog(fs, np.absolute(ys), '-+')
    top.set_ylabel('Magnitude (normalized)')

    bottom = plt.subplot(2, 1, 2)
    bottom.semilogx(fs, np.degrees(np.angle(ys)))
    bottom.grid()
    bottom.set_ylabel('Phase (degrees)')
    bottom.set_xlabel('Frequency (Hz)')

    plt.show()

#bode_plot([10e6 + 100e6*1j, 10e6 - 100e6*1j], [])

'''
def plot(xs, ys):
    import matplotlib.pyplot as plt
    plt.plot(xs, ys, '-+')
    plt.grid()
    plt.show()
'''

def debug(test):
    class DebugTest(test):

        def debug(self, tester, port, duration):
            r = tester.get_value(port, params={'style':'block', 'duration': duration})
            self.debug_dict.append((port, r))

        def testbench(self, *args, **kwargs):
            self.debug_dict = []
            self.debug_plot_shown = False
            retval = super().testbench(*args, **kwargs)
            return (self.debug_dict, retval)

        def analysis(self, reads):
            debug_dict, reads_orig = reads

            if not self.debug_plot_shown:
                import matplotlib.pyplot as plt
                leg = []
                bump = 0
                for p, r in debug_dict:
                    leg.append(str(self.template.signals.from_spice_pin(p)))
                    plt.plot(r.value[0], r.value[1] + bump, '-+')
                    bump += 0.0 # useful for separating clock signals
                plt.grid()
                plt.legend(leg)
                plt.show()
                self.debug_plot_shown = True

            return super().analysis(reads_orig)

    return DebugTest

def make_nondecreasing(ys):
    '''
    Given a list of y values, give a new list of y values that is nondecreasing
    such that the MSE between the two lists is minimized
    '''
    ys = [float(y) for y in ys]
    new_ys = [ys[0]]
    for i in range(1, len(ys)):
        y = ys[i]
        new_ys.append(y)
        if new_ys[-1] < new_ys[-2]:
            # do some approximating
            # The best thing to do is to take the previous n points and set
            # them equal to their collective average, for some n
            cum_sum = y
            count = 1
            error_added_best = float('inf')
            avg_prev = None
            j = i
            while j > 0:
                j -= 1
                cum_sum += ys[j]
                count += 1
                avg = cum_sum / count
                # this time through the loop, we are proposing to set all
                # new_ys[j:i+1] equal to avg (that's j to i, inclusive)
                if j>0 and avg < new_ys[j-1]:
                    # this is illegal because it would be decreasing
                    continue
                error_added = 0
                # loop over all indices we propose to change
                for k in range(j, i+1):
                    error_added += (ys[k] - avg)**2 - (ys[k]-new_ys[k])**2
                if error_added >= error_added_best:
                    # we've gone too far! quit now and use our current best
                    break
                error_added_best = error_added
                avg_best = avg
                j_best = j

            # now that we're out of the loop, we have the j and avg we want
            for k in range(j_best, i+1):
                new_ys[k] = avg_best

    '''
    import matplotlib.pyplot as plt
    xs = list(range(len(ys)))
    plt.plot(xs, ys, '+')
    plt.plot(xs, new_ys, '--')
    plt.grid()
    plt.show()
    '''

    return new_ys



def invert_function(xs, ys):
    #ys = [float(y) + random.random()*0.02 for y in ys]
    xs = [float(x) for x in xs]
    #xs = list(range(len(xs)))
    #TODO: this is broken for decreasing things
    if ys[0] > ys[-1]:
        temp = [-y for y in ys]
        temp2 = make_nondecreasing(temp)
        ys_up = [-y for y in temp2]
    else:
        ys_up = make_nondecreasing(ys)
    
    new_xs = [xs[0]]
    new_ys = [ys_up[0]]
    float_eps = (ys_up[-1] - ys_up[0])*1e-10 # 1e-10
    for i in range(1, len(xs)-1):
        # look for flat regions
        # start
        if ys_up[i-1] < ys_up[i] - float_eps:
            if ys_up[i] < ys_up[i+1] - float_eps:
                # normal
                new_xs.append(xs[i])
                new_ys.append(ys_up[i])
                #print('normal', i)
            else:
                # start of flat region
                frac = (ys_up[i] - ys[i-1]) / (ys[i] - ys[i-1])
                new_x = xs[i-1] + frac * (xs[i] - xs[i-1])
                new_xs.append(new_x)
                new_ys.append(ys_up[i])
                #print('start of flat', i, frac, xs[i-1:i+2], new_x)
        else:
            if ys_up[i] < ys_up[i+1] - float_eps:
                # end of flat region
                frac = (ys_up[i] - ys[i]) / (ys[i+1] - ys[i])
                new_x = xs[i] + frac * (xs[i+1] - xs[i])
                new_xs.append(new_x)
                new_ys.append(ys_up[i])
                #print('end of flat', i, frac, xs[i-1:i+2], new_x)
            else:
                # middle of flat region - no points necessary
                #print('middle of flat', i)
                pass

    new_xs.append(xs[-1])
    new_ys.append(ys_up[-1])

    #import matplotlib.pyplot as plt
    #plt.plot(xs, ys, '--')
    #plt.plot(xs, ys_up, '+')
    #plt.plot(new_xs, new_ys, '-x')
    #plt.grid()
    #plt.show()

    # TODO I would like to give each flat region a slight tilt because it
    # would help in cases where the true curve is increasing but noise
    # messed it up - we don't want everything in that region collected on
    # one end of the flat region

    endpoints = (new_xs[0], new_xs[-1])
    return interp1d(new_ys, new_xs, bounds_error=False, fill_value=endpoints, assume_sorted=True)

def remove_repeated_timesteps(t, h):
    # issues with multiple repeated ts
    t_norepeat, h_norepeat = [], []
    tt_prev = float('nan')
    for tt, hh in zip(t, h):
        if tt != tt_prev:
            t_norepeat.append(tt)
            h_norepeat.append(hh)
            tt_prev = tt
        else:
            # take last version
            h_norepeat[-1] = hh
    return t_norepeat, h_norepeat

#import numpy as np
#from scipy import signal
#x = np.array([0, 1, 2, 3, 4, 5])
##y = 0.5 * np.exp(-1 * x) + 2.0 * np.exp(-1.5 * x)
#num = np.polynomial.polynomial.polyfromroots([30])[::-1]
#den = np.polynomial.polynomial.polyfromroots([50, 55])[::-1]
#y = signal.step(signal.lti(num, den), T=x)[1]

import numpy as np

# h = np.array([.63-.167, .167-.0471, .0471-.0141, .0141-.00447, .00447-.00149])
#t = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

# this works beautifully
#h_step = 5 * np.exp(-.7 * t) + -5 * np.exp(-.3 * t)

# this crashes, I mistyped - not anymore?
# coefficients from "partial fraction decomposition (x-1)/((x-1.5)(x-1.6))"
#h_step = 6 * np.exp(-1.6 * t) + 5 * np.exp(-1.5 * t)

# This is fine
#h_step = 6 * np.exp(-1.6 * t) - 5 * np.exp(-1.5 * t)

#t = np.array(range(100)) * 0.08 * 1e-9
## should be a zero at 8.9G, and you can see the poles
#h_impulse = 90e9 * np.exp(-3.5e9 * t) - 115e9 * np.exp(-2e9 * t)
#
##h_impulse = np.concatenate(([0], np.cumsum(h_impulse)))
#h = np.cumsum(h_impulse) #/ (-4e11)
##print('h', h)
#h += np.random.normal(0, 10e9, h.shape)
#
#import scipy
#import matplotlib.pyplot as plt
#
###h_smooth = scipy.ndimage.gaussian_filter1d(h, 2, mode='nearest')
##t2 = np.array(range(1000)) * 0.002 * 1e-9
##spline = scipy.interpolate.UnivariateSpline(t*1e9, h*1e-9, s=3)
##spline.set_smoothing_factor(1e16)
##h_smooth = spline(t2*1e9)
###plt.plot(t*1e9, h*1e-9, 'ro')
###plt.plot(t2*1e9, h_smooth, 'g+')
###plt.grid()
###plt.show()
#
#
#h[1] += 0.2
#no_sample = len(h)
#
#
#t = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
#h_step = 5 * np.exp(-.7 * t) + -4 * np.exp(-.3 * t) + -2 * np.exp(-.2 * t) + 1
##h_step = 2**t + 3**t - 1
#
#extract_pzs(3, 2, t, h_step)
#
#########