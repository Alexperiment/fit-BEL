from astropy.table import Table
import numpy as np
import pandas as pd
from extinction import fitzpatrick99 as fp99
from extinction import remove as ext_remove
import config


class Spectrum:
    def __init__(
            self,
            file_path,
            redshift,
            a_v_extinction=None,
            linearize_wavelength=True,
            skiprows=2,
            separator='\t',
            to_rest_frame=True,
    ):
        self.file_path = file_path
        self.name = self.file_path.split('/')[-1].split('.')[0]
        self.data = read_data(self.file_path, skiprows, separator)
        self.wavelength = self.data['lambda'].values
        self.flux = self.data['flux'].values
        self.redshift = redshift
        self.rest_frame = to_rest_frame
        self.linearize_wavelength = linearize_wavelength
        self.a_v_extinction = a_v_extinction
        self.to_rest_frame = to_rest_frame

        self._linearize_wavelength()
        self._correct_extinction()
        self._to_rest_frame()

        self.ivar = self._calculate_ivar()
        self._mask_dead_pixels()

    def _linearize_wavelength(self):
        if self.linearize_wavelength:
            if np.max(self.wavelength) < 5:
                self.wavelength = 10 ** self.wavelength

    def _correct_extinction(self, r_v_extinction=3.1):
        if self.a_v_extinction is not None:
            extinction_curve = fp99(self.wavelength.to_numpy(dtype=np.double), self.a_v_extinction, r_v_extinction)
            return ext_remove(extinction_curve, self.flux)

    def _to_rest_frame(self):
        if self.to_rest_frame:
            self.wavelength = self.wavelength / (1 + self.redshift)
            self.flux = self.flux * (1 + self.redshift)

    def _calculate_ivar(self):
        if 'ivar' in self.data.columns:
            return self.data['ivar']
        if not self.rest_frame:
            config.IVAR_INTERVALS = config.IVAR_INTERVALS * (1 + self.redshift)
        mask = (self.wavelength >= config.IVAR_INTERVALS[0]) & (self.wavelength <= config.IVAR_INTERVALS[1])
        continuum = self.flux[mask]
        ivar = 1 / (np.var(continuum))
        return np.full(len(self.wavelength), ivar)

    def _trim_data(self):
        mask = (self.wavelength >= config.TRIM_INTERVALS[0]) & (self.wavelength <= config.TRIM_INTERVALS[1])
        self.wavelength = self.wavelength[mask]
        self.flux = self.flux[mask]
        self.ivar = self.ivar[mask]

    def _mask_dead_pixels(self):
        dead_pixel_mask = self.ivar != 0
        self.flux = self.flux[dead_pixel_mask]
        self.ivar = self.ivar[dead_pixel_mask]
        self.wavelength = self.wavelength[dead_pixel_mask]


def read_data(file_path, skiprows, separator):
    if file_path.endswith('.txt'):
        return read_txt(file_path, skiprows, separator)
    elif file_path.endswith('.fits'):
        return read_fits(file_path)


def read_fits(file_path):
    spec_df = Table.read(file_path, hdu=1).to_pandas()
    spec_df.columns = [c.lower() for c in spec_df.columns]
    spec_df.rename(columns={'loglam': 'lambda'}, inplace=True)
    return spec_df


def read_txt(file_path, skiprows, separator):
    spec_df = pd.read_csv(file_path, sep=separator, skiprows=skiprows, header=None)
    spec_df.columns = ['lambda', 'flux']
    return spec_df


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    file_path = 'examples/sample.txt'
    obj = Spectrum(file_path, redshift=3)
    wl = obj.wavelength
    fl = obj.flux
    ivar = obj.ivar

    plt.plot(wl, fl)
    plt.show()