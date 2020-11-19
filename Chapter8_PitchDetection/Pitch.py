# Class Pitch Detection

from spectrum import xcorr

from VAD import *


class Pitch:
	def linsmoothm(self, x, n=3):
		"""
		linear smoothing
		:param x:
		:param n: default = 3
		:return:
		"""
		win = np.hanning(n)  # hanning window
		win = win / np.sum(win)  # normalized
		x = x.reshape(-1, 1)  # --> column vector
		
		length = len(x)
		y = np.zeros(length)  # initialization
		# complement before and after the output to ensure the length is the same as x
		x = x.squeeze()
		if n % 2 == 0:
			L = int(n / 2)
			x = np.concatenate([np.ones(1) * x[0], x, np.ones(L) * x[L]]).T
		else:
			L = int((n - 1) / 2)
			x = np.concatenate([np.ones(1) * x[0], x, np.ones(L + 1) * x[L]]).T
		
		for k in range(length):
			y[k] = np.dot(win.T, x[k: k + n])
		
		return y
	
	def pitfilterm1(self, x, vseg, vsl):
		"""
		smoothing fundamental frequency T0
		:param x:
		:param vseg: voice segment
		:param vsl: voice sgement length
		:return y: linear smoothing T0
		"""
		y = np.zeros(x.shape)  # initialization
		for i in range(vsl):  # data segment
			ixb = vseg['begin'][i]
			ixe = vseg['end'][i]
			u0 = x[ixb: ixe]  # one segment data
			y0 = VAD().multimidfilter(u0, 5)  # 5 point medfilter
			v0 = self.linsmoothm(y0, 5)  # linear smoothing
			y[ixb: ixe] = v0
		
		return y
	
	def ACF_corr(self, y, fn, vseg, vsl, lmax, lmin):
		"""
		Auto correlation function Pitch detection
		:param y: enframe matrix (size: window length * frame number)
		:param fn: frame number
		:param vseg: vad
		:param vsl: vad
		:param lmax: min pitch period
		:param lmin: max pitch period
		:return period: pitch period
		"""
		pn = y.shape[1]
		if pn != fn:
			y = y.T
		wlen = y.shape[0]  # frame length
		period = np.zeros(fn)  # pitch period
		
		for i in range(vsl):  # only for voice segment
			ixb = vseg['begin'][i]  # segment begin index
			ixe = vseg['end'][i]  # segment end index
			ixd = ixe - ixb + 1  # segment duration
			for k in range(ixd):
				u = y[:, k + ixb - 1]  # one frame data
				ru, _ = xcorr(u, norm='coeff')
				ru = ru[wlen: 2 * wlen - 1]
				tloc = np.argmax(ru[lmin: lmax])  # find max in [lmin : lmax]
				period[k + ixb - 1] = lmin + tloc - 1
		
		return period
	
	def ACF_clip(self, y, fn, vseg, vsl, lmax, lmin):
		"""
		Auto correlation & clip function Pitch detection
		:param y: enframe matrix (size: window length * frame number)
		:param fn: frame number
		:param vseg: vad
		:param vsl: vad
		:param lmax: min pitch period
		:param lmin: max pitch period
		:return period: pitch period
		"""
		pn = y.shape[1]
		if pn != fn:
			y = y.T
		wlen = y.shape[0]  # frame length
		period = np.zeros(fn)  # pitch period
		
		for i in range(vsl):  # only for voice segment
			ixb = vseg['begin'][i]  # segment begin index
			ixe = vseg['end'][i]  # segment end index
			ixd = ixe - ixb + 1  # segment duration
			for k in range(ixd):
				u = y[:, k + ixb - 1]  # one frame data
				rate = 0.7                      # clip parameter
				CL = np.max(u) * rate           # threshold
				for j in range(wlen):
					if u[j] > CL:
						u[j] = u[j] - CL
					elif u[j] <= (-CL):
						u[j] = u[j] + CL
					else:
						u[j] =0
				u = u / np.max(u)  # normalization
				ru, _ = xcorr(u, norm='coeff')
				ru = ru[wlen: 2 * wlen - 1]
				tloc = np.argmax(ru[lmin: lmax])  # find max in [lmin : lmax]
				period[k + ixb - 1] = lmin + tloc - 1
		
		return period
	
	def ACF_threelevel(self, y, fn, vseg, vsl, lmax, lmin):
		"""
		Auto correlation & three level clip function Pitch detection
		:param y: enframe matrix (size: window length * frame number)
		:param fn: frame number
		:param vseg: vad
		:param vsl: vad
		:param lmax: min pitch period
		:param lmin: max pitch period
		:return period: pitch period
		"""
		pn = y.shape[1]
		if pn != fn:
			y = y.T
		wlen = y.shape[0]  # frame length
		period = np.zeros(fn)  # pitch period
		
		for i in range(vsl):  # only for voice segment
			ixb = vseg['begin'][i]  # segment begin index
			ixe = vseg['end'][i]  # segment end index
			ixd = ixe - ixb + 1  # segment duration
			for k in range(ixd):
				u = y[:, k + ixb - 1]  # one frame data
				px1 = u[0 : 100]        # first 100 points
				px2 = u[wlen - 100 : wlen] # last 100 points
				CLm = min(max(px1), max(px2))
				CL = CLm * 0.68  # threshold
				ThreeLevel = np.zeros(wlen)     # initialization
				for j in range(wlen):
					if u[j] > CL:
						u[j] = u[j] - CL
						ThreeLevel[j] = 1
					elif u[j] <= (-CL):
						u[j] = u[j] + CL
						ThreeLevel[j] = -1
					else:
						u[j] = 0
						ThreeLevel[j] = 0
				u = u / np.max(u)  # normalization
				ru, _ = xcorr(ThreeLevel, u, norm='coeff')
				ru = ru[wlen: 2 * wlen - 1]
				tloc = np.argmax(ru[lmin: lmax])  # find max in [lmin : lmax]
				period[k + ixb - 1] = lmin + tloc - 1
		
		return period
	
	def AMDF_mod(self, y, fn, vseg, vsl, lmax, lmin):
		"""
		average magnitude difference function --> pitch detection
		:param y: enframe matrix (size: window length * frame number)
		:param fn: frame number
		:param vseg: vad
		:param vsl: vad
		:param lmax: min pitch period
		:param lmin: max pitch period
		:return period: pitch period
		"""
	
		pn = y.shape[1]
		if pn != fn:
			y = y.T
		wlen = y.shape[0]  # frame length
		period = np.zeros(fn)  # pitch period
		
		for i in range(vsl):  # only for voice segment
			ixb = vseg['begin'][i]  # segment begin index
			ixe = vseg['end'][i]  # segment end index
			ixd = ixe - ixb + 1  # segment duration
			R0 = np.zeros(wlen)     # average magnitude difference
			R = np.zeros(wlen)  # linear transformation
			for k in range(ixd):
				u = y[:, k + ixb - 1]  # one frame data
				for m in range(wlen):
					R0[m] = np.sum(np.abs(u[m : wlen - 1] - u[0 : wlen - m - 1]))
				Rmax = max(R0)
				Nmax = np.argmax(R0)
				for j in range(wlen):
					R[j] = Rmax * (wlen - j) / (wlen - Nmax) - R0[j]
				T = np.argmax(R[lmin: lmax])  # find max in [lmin : lmax]
				T0 = T + lmin - 1
				period[k + ixb - 1] = T0
		
		return period