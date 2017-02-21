import numpy as np
from pyfftw.interfaces.scipy_fftpack import fft2
from pyfftw.interfaces.scipy_fftpack import ifft2

from scipy.interpolate import splrep,splev
from scipy.fftpack import fftshift
from scipy.interpolate import RectBivariateSpline,interp2d
from orphics.tools.stats import timeit


#Take divergence using fourier space gradients
def takeDiv(vecStampX,vecStampY,lxMap,lyMap):

    fX = fft2(vecStampX)
    fY = fft2(vecStampY)

    return ifft2((lxMap*fX+lyMap*fY)*1j).real



@timeit
def interpolateGrid(inGrid,inY,inX,outY,outX,regular=True,kind="cubic",kx=3,ky=3,**kwargs):
    '''
    if inGrid is [j,i]
    Assumes inY is along j axis
    Assumes inX is along i axis
    Similarly for outY/X
    '''

    if regular:
        interp_spline = RectBivariateSpline(inY,inX,inGrid,kx=kx,ky=ky,**kwargs)
        outGrid = interp_spline(outY,outX)
    else:
        interp_spline = interp2d(inX,inY,inGrid,kind=kind,**kwargs)
        outGrid = interp_spline(outX,outY)
    

    return outGrid


class GRFGen(object):

    def __init__(self,templateLiteMap,ell,Cell,bufferFactor=1):
        # Cell is dimensionless

        self.lxMap,self.lyMap,self.modLMap,self.thetaMap,self.lx,self.ly = getFTAttributesFromLiteMap(templateLiteMap)

        bufferFactor = int(bufferFactor)
        self.b = bufferFactor

        self.Ny = templateLiteMap.data.shape[1]*bufferFactor
        self.Nx = templateLiteMap.data.shape[0]*bufferFactor

        Ny = self.Ny
        Nx = self.Nx

        Cell[Cell<0.]=0.

        s = splrep(ell,Cell,k=3) # maps will be uK fluctuations about zero
        #ll = np.ravel(self.modLMap)
        #kk = splev(ll,s)
        kk = splev(self.modLMap,s)


        

        kk[self.modLMap<2.]=0.
        #kk[ll<2.]=0.
        
        #id = np.where(ll>ell.max())
        #kk[id] = 0.
        kk[self.modLMap>ell.max()] = 0.

        area = Nx*Ny*templateLiteMap.pixScaleX*templateLiteMap.pixScaleY
        #p = np.reshape(kk,[Ny,Nx]) /area * (Nx*Ny)**2
        p = kk /area * (Nx*Ny)**2

        
        self.sqp = np.sqrt(p)

    #@timeit
    def getMap(self,stepFilterEll=None):
        """
        Modified from sudeepdas/flipper
        Generates a GRF from an input power spectrum specified as ell, Cell 
        BufferFactor =1 means the map will be periodic boundary function
        BufferFactor > 1 means the map will be genrated on  a patch bufferFactor times 
        larger in each dimension and then cut out so as to have non-periodic bcs.

        Fills the data field of the map with the GRF realization
        """


        realPart = self.sqp*np.random.randn(self.Ny,self.Nx)
        imgPart = self.sqp*np.random.randn(self.Ny,self.Nx)


        kMap = realPart+1.j*imgPart
        
        if stepFilterEll is not None:
            kMap[self.modLMap>stepFilterEll]=0.



        data = np.real(ifft2(kMap)) 

        data = data[(self.b-1)/2*self.Ny:(self.b+1)/2*self.Ny,(self.b-1)/2*self.Nx:(self.b+1)/2*self.Nx]


        return data - data.mean()


def stepFunctionFilterLiteMap(map2d,modLMap,ell):

    kmap = fft2(map2d.copy())
    kmap[modLMap>ell]=0.
    retMap = ifft2(kmap).real

    return retMap


def TQUtoFourierTEB(T_map,Q_map,U_map,modLMap,angLMap):

    fT=fft2(T_map)    
    fQ=fft2(Q_map)        
    fU=fft2(U_map)
    
    fE=fT.copy()
    fB=fT.copy()
    fE[:]=fQ[:]*np.cos(2.*angLMap)+fU*np.sin(2.*angLMap)
    fB[:]=-fQ[:]*np.sin(2.*angLMap)+fU*np.cos(2.*angLMap)
    
    return(fT, fE, fB)


def getRealAttributes(templateLM):
    '''
    Given a liteMap, return a coord
    system centered on it and a map
    of distances from center in
    radians
    '''

        
    Nx = templateLM.Nx
    Ny = templateLM.Ny
    pixScaleX = templateLM.pixScaleX 
    pixScaleY = templateLM.pixScaleY
    
    
    xx =  (np.arange(Nx)-Nx/2.+0.5)*pixScaleX
    yy =  (np.arange(Ny)-Ny/2.+0.5)*pixScaleY
    
    ix = np.mod(np.arange(Nx*Ny),Nx)
    iy = np.arange(Nx*Ny)/Nx
    
    modRMap = np.zeros([Ny,Nx])
    modRMap[iy,ix] = np.sqrt(xx[ix]**2 + yy[iy]**2)
    

    xMap, yMap = np.meshgrid(xx, yy)  # is this the right order?

    return xMap,yMap,modRMap,xx,yy


def getFTAttributesFromLiteMap(templateLM):
    '''
    Given a liteMap, return the fourier frequencies,
    magnitudes and phases.
    '''

    from scipy.fftpack import fftfreq
        
    Nx = templateLM.Nx
    Ny = templateLM.Ny
    pixScaleX = templateLM.pixScaleX 
    pixScaleY = templateLM.pixScaleY
    
    
    lx =  2*np.pi  * fftfreq( Nx, d = pixScaleX )
    ly =  2*np.pi  * fftfreq( Ny, d = pixScaleY )
    
    ix = np.mod(np.arange(Nx*Ny),Nx)
    iy = np.arange(Nx*Ny)/Nx
    
    modLMap = np.zeros([Ny,Nx])
    modLMap[iy,ix] = np.sqrt(lx[ix]**2 + ly[iy]**2)
    
    thetaMap = np.zeros([Ny,Nx])
    thetaMap[iy[:],ix[:]] = np.arctan2(ly[iy[:]],lx[ix[:]])
    #thetaMap *=180./np.pi


    lxMap, lyMap = np.meshgrid(lx, ly)  # is this the right order?

    return lxMap,lyMap,modLMap,thetaMap,lx,ly






def makeTemplate(l,Fl,modLMap,k=1,debug=False):
    """                                                                                                                                    
    Given 1d function Fl of l, creates the 2d version                                                                                   
    of Fl on 2d k-space defined by ftMap                                                                                                   
    """
    from scipy.interpolate import splrep, splev

    #Fl[Fl>1.e90] = 1.e90

    Ny,Nx = modLMap.shape
    tck = splrep(l,Fl,k=k)
    lmap = modLMap
    lmapunravel = lmap.ravel()
    template1d = splev(lmapunravel,tck)
    template = np.reshape(template1d,[Ny,Nx])

    if debug:
        from ..tools.output import Plotter

        pl = Plotter()
        pl.add(l,Fl)
        pl.done("fl.png")

        pl = Plotter(scaleX='log',scaleY='log')
        pl.add(lmapunravel,template1d)
        pl.done('debug.png')

        
        template[np.where(lmap <= 100.)] = 0.
        template[np.where(lmap >= 1000.)] = 0.
        
        
        pl = Plotter()
        pl.plot2d(np.log10((fftshift(template))))
        pl.done("temp.png")
        sys.exit()
    
    return template



def whiteNoise2D(noiseLevels,beamArcmin,modLMap,TCMB = 2.7255e6,lknees=None,alphas=None,beamFile=None, \
                 noiseFiles=None):
    # Returns 2d map noise in units of uK**0.
    # Despite the name of the function, there are options to add
    # a simplistic atmosphere noise model


    if lknees is None:
        lknees = (np.array(noiseLevels)*0.).tolist()
    if alphas is None:
        alphas = (np.array(noiseLevels)*0.+1.).tolist()

    if noiseFiles is None: noiseFiles = [None]*len(noiseLevels)
        

    
        
    if beamFile is not None:
        from scipy.interpolate import interp1d
        ell, f_ell = np.transpose(np.loadtxt(beamFile))[0:2,:]
        filt = 1./(np.array(f_ell)**2.)
        bfunc = interp1d(ell,f_ell,bounds_error=False,fill_value=np.inf)
        filt2d = bfunc(modLMap)
    else:
        Sigma = beamArcmin *np.pi/60./180./ np.sqrt(8.*np.log(2.))  # radians
        filt2d = np.exp(-(modLMap**2.)*Sigma*Sigma)


    retList = []

    for noiseLevel,lknee,alpha,noiseFile in zip(noiseLevels,lknees,alphas,noiseFiles):
        if noiseFile is not None:
            ls,Nls = np.loadtxt(noiseFile,unpack=True)
            nfunc = interp1d(ls,Nls,bounds_error=False,fill_value=np.inf)
            retList.append(nfunc(modLMap))
        else:
        
            noiseForFilter = (np.pi / (180. * 60))**2.  * noiseLevel**2. / TCMB**2.  

            if lknee>0.:
                atmFactor = (lknee*np.nan_to_num(1./modLMap))**(-alpha)
            else:
                atmFactor = 0.

            retList.append(noiseForFilter*(atmFactor+1.)/filt2d.copy())

    return retList


    


def fourierMask(lx,ly,modLMap, lxcut = None, lycut = None, lmin = None, lmax = None):
    output = np.zeros(modLMap.shape, dtype = int)
    output[:] = 1
    if lmin != None:
        wh = np.where(modLMap <= lmin)
        output[wh] = 0
    if lmax != None:
        wh = np.where(modLMap >= lmax)
        output[wh] = 0
    if lxcut != None:
        wh = np.where(np.abs(lx) < lxcut)
        output[:,wh] = 0
    if lycut != None:
        wh = np.where(np.abs(ly) < lycut)
        output[wh,:] = 0
    return output




def initializeCosineWindow(templateLiteMap,lenApod=30,pad=0):
	
    Nx=templateLiteMap.Nx
    Ny=templateLiteMap.Ny
    win=templateLiteMap.copy()
    win.data[:]=1

    winX=win.copy()
    winY=win.copy()

    for j in range(pad,Ny-pad):
            for i in range(pad,Nx-pad):
                    if i<=(lenApod+pad):
                            r=float(i)-pad
                            winX.data[j,i]=1./2*(1-np.cos(-np.pi*r/lenApod))
                    if i>=(Nx-1)-lenApod-pad:
                            r=float((Nx-1)-i-pad)
                            winX.data[j,i]=1./2*(1-np.cos(-np.pi*r/lenApod))

    for i in range(pad,Nx-pad):
            for j in range(pad,Ny-pad):
                    if j<=(lenApod+pad):
                            r=float(j)-pad
                            winY.data[j,i]=1./2*(1-np.cos(-np.pi*r/lenApod))
                    if j>=(Ny-1)-lenApod-pad:
                            r=float((Ny-1)-j-pad)
                            winY.data[j,i]=1./2*(1-np.cos(-np.pi*r/lenApod))

    win.data[:]*=winX.data[:,:]*winY.data[:,:]
    win.data[0:pad,:]=0
    win.data[:,0:pad]=0
    win.data[Nx-pad:Nx,:]=0
    win.data[:,Nx-pad:Nx]=0

    return(win.data)


def deconvolveBeam(data,modLMap,ell,beam,returnFTOnly = False):


    beamTemplate =  makeTemplate(ell,beam,modLMap)

    kMap = fft2(data)

    kMap[:,:] = (kMap[:,:] / beamTemplate[:,:])
    if returnFTOnly:
        return kMap
    else:
        return ifft2(kMap).real

