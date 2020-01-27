from numpy import *
from scipy import interpolate
from scipy.linalg import toeplitz,pinv,inv
from scipy.signal import invres,step,impulse
import matplotlib.pyplot as plt

class ModalAnalysis(object):
    ''' Fit an step response measurement to a linear system model '''
    def __init__(self, rho_threshold = 0.999, N_degree = 50):
        ''' set constraints on calculation '''
        self.rho_threshold = rho_threshold # correlation threshold
        self.N_degree = N_degree # Maximum degree of freedom

    def fit_stepresponse(self,h,t):
        ''' fit an step response measurement to a linear system model '''
        h_impulse = diff(h)/diff(t) # get impulse response from step response
        t_impulse = t[:-1]+diff(t)/2.0 # time adjustment, take the mid-point
        return self.fit_impulseresponse(h_impulse,t_impulse)
    
    def fit_impulseresponse(self,h,t):
        #for N in range(2,self.N_degree):
        for N in range(1,self.N_degree):
            print('Trying degree', N)
            ls_result = self.leastsquare_complexexponential(h,t,N)
            if ls_result['failed'] and N >=3:
                print('Giving up because degree', N, 'failed')
                break
            rho = self.compare_impulseresponse(ls_result['h_impulse'],ls_result['h_estimated'])
            print('rho=',rho)
            if rho > self.rho_threshold:
                print('Happy with this rho, moving on now')
                break
            if N == self.N_degree:
                print('[WARNING]: Maximum degree of freedom is reached when fitting response to transfer function')
        return ls_result

    def compare_impulseresponse(self,h1,h2):

        #import matplotlib.pyplot as plt
        #plt.plot(h1, '-*')
        #plt.plot(h2, '-*')
        #plt.show()


        h1 = h1.flatten()
        h2 = h2.flatten()
        return corrcoef([h1,h2])[0,1]

    def leastsquare_complexexponential(self,h,t,N):
        ''' Model parameter estimation from impulse response
                using least-squares complex exponential method 
                h: impulse response measurement
                t: time range vector (in sec); must be uniformly-spaced
                N: degree of freedom
        '''
        h_temp, t_temp = h, t
        no_sample = h.size
        if diff(t).max() > diff(t).min(): # check for uniform time steps
            print('RESAMPLING')
            spline_fn = interpolate.InterpolatedUnivariateSpline(t,h)
            #t = linspace(t[0],t[-1],no_sample)
            # TODO i intentionally cut off the first point below to see if it would fix problems but it did not
            # if the problems go away, we should try putting that point back
            t = linspace(1e-12,t[-1],no_sample+1)
            t = t[1:]
            h = spline_fn(t)
            h = h / abs(max(h))

        #import matplotlib.pyplot as plt
        #plt.plot(h, '-*')
        #plt.show()





        h = h.reshape(no_sample,1)
        t = t.reshape(no_sample,1)
        M = no_sample - N # no of equations
        dT = t[1]-t[0]
        # least-squares estimation of eigenvalues (modes)
        R = matrix(toeplitz(h[N-1::-1],h[N-1:no_sample-1]))
        A = -1*matrix(pinv(R.transpose()))*matrix(h[N+arange(0,M,dtype=int)])
        A0 = vstack((ones(A.shape[1]),A)).getA1()

        A0_roots = roots(A0)
        #A0_roots = [(0 if r < 0 and r > -1e-9 else r) for r in A0_roots]

        P = matrix(log(A0_roots) / dT).transpose()
        # least-squares estimation of eigenvectors (modal coef)
        Q = exp(P * t.transpose())

        error = False
        try:
            Z = pinv(matrix(Q.transpose()))*matrix(h)
            print(type(Z))
        except ValueError:
            error = True
            print('Error calculating poles/zeros')

            import matplotlib.pyplot as plt
            plt.plot(t, h, '-*')
            plt.show()

            Z = matrix(zeros((Q.shape[0],h.shape[1])))
        # return values
        num,den = invres(Z.getA1(),P.getA1(),zeros(size(P)),tol=1e-4,rtype='avg')
        if not error:
            print(num, den)
        num = num.real
        den = den.real
        h_estimated = Q.transpose()*Z
        h_estimated = h_estimated.real.getA1()
        return dict(h_impulse=h,h_estimated=h_estimated,num=num,den=den,failed=error)

    def fit_transferfunction(self,H,f):
        ''' Fit a frequency response measurement to a linear system model '''
        pass

    def compare_transferfunction(self,H1,H2):
        ''' calculates the correlation coef. in frequency domain between two transfer function '''
        pass

    def selftest(self):
        pass

def main():
    X = ModalAnalysis(0.999,100)
    system = ([2.0],[1.0,2.0,1.0])
    #system = ([2.0,1.0],[1.0,2.0,1.0])
    ## impulse response test
    #t,h = impulse(system)
    #ls_result=X.fit_impulseresponse(h,t)
    #system_est = (ls_result['num'],ls_result['den'])
    #t1,h1 = impulse(system_est)
    #plt.plot(t,h,'rs',t1,h1,'bx')
    #plt.show()
    ## step response test
    t,h = step(system)
    ls_result=X.fit_stepresponse(h,t)
    system_est = (ls_result['num'],ls_result['den'])
    t1,h1 = step(system_est)
    plt.plot(t,h,'rs',t1,h1,'bx')
    plt.show()

if __name__ == "__main__":
    main()
