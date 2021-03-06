# * Copyright (C) 2017 J.Mittaz University of Reading
# * This code was developed for the EC project Fidelity and Uncertainty in
# * Climate Data Records from Earth Observations (FIDUCEO). 
# * Grant Agreement: 638822
# *
# * This program is free software; you can redistribute it and/or modify it
# * under the terms of the GNU General Public License as published by the Free
# * Software Foundation; either version 3 of the License, or (at your option)
# * any later version.
# * This program is distributed in the hope that it will be useful, but WITHOUT
# * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# * more details.
# * 
# * A copy of the GNU General Public License should have been supplied along
# * with this program; if not, see http://www.gnu.org/licenses/
# * ------------------------------------------------------------------------
# * MT: 18-10-2017: added quality flag fields
# * MT: 30-10-2017: uncertainty variables renamed in line with FCDR-CDR file format spec fv1.1.1
# * MT: 09-11-2017: channel_correlation_matrix added (sensor specific)
# * MT: 10-11-2017: spatial_correlation_scale added (sensor specific)
# * JM: 06-07-2018: Real channel/spatial correlation scales added plus SRF
# * JM: 07-07-2018: Output GBCS L1C option for SST with channel covariance
# * JM: 07-02-2019: Fix issues with CURUC

from fiduceo.fcdr.writer.fcdr_writer import FCDRWriter
from fiduceo.fcdr.writer.templates import avhrr
import sys
import netCDF4
import numpy as np
import datetime
import xarray
import argparse
from optparse import OptionParser
import FCDR_HIRS.metrology as met
import write_l1c_data as l1c
import matplotlib.pyplot as plt
import uuid
import os


class read_netcdf(object):

    def add_nan_values(self,values):
        with np.errstate(invalid='ignore'):
            gd = np.isfinite(values) & (values < -1e20)
        if np.sum(gd) > 0:
            values[gd] = np.NaN
        return values

    def scale_values(self,values):
        with np.errstate(invalid='ignore'):
            gd = (values > -1e20) & np.isfinite(values)
        if np.sum(gd) > 0:
            values[gd] = values[gd]*100.
        return values

    def read_data(self,filename):

        ncid = netCDF4.Dataset(filename,'r')

        self.sources = ncid.sources
        self.noaa_string = ncid.noaa_string
        self.version = ncid.version
        self.spatial_correlation_scale = ncid.spatial_correlation_scale
        year = ncid.variables['year'][:]
        month = ncid.variables['month'][:]
        day = ncid.variables['day'][:]
        hours = ncid.variables['hours'][:]
        gd = (year > 1900) & (day > 0) & (month > 0) & (hours >= 0)
        if 0 == np.sum(gd):
            raise Exception('No good data in netcdf')
        yr = year[:]
        mn = month[:]
        dy = day[:]
        temp = hours[:]
        hour = temp.astype(np.int)
        temp = (temp - hour)*60.
        minute = temp.astype(np.int)
        temp = (temp - minute)*60.
        second = temp.astype(np.int)
        microsec = ((temp-second)*1e6).astype(np.int)
        self.date_time = []
        for i in range(len(hour)):
            if gd[i]:
                self.date_time.append(datetime.datetime(yr[i],mn[i],dy[i],hour[i],minute[i],second[i],microsec[i]))
            else:
                self.date_time.append(datetime.datetime(1,1,1,0,0,0,0))
        self.time = netCDF4.date2num(self.date_time,'seconds since 1970-01-01')
        self.lat = ncid.variables['latitude'][:,:]
        self.lon = ncid.variables['longitude'][:,:]
        self.satza = ncid.variables['satza'][:,:]
        self.solza = ncid.variables['solza'][:,:]
        self.relaz = ncid.variables['relaz'][:,:]
        self.ch1 = ncid.variables['ch1'][:,:]
        self.ch2 = ncid.variables['ch2'][:,:]
        self.ch3a = ncid.variables['ch3a'][:,:]
        self.ch3a_there_int = ncid.variables['ch3a_there'][:]
        self.ch3a_there = False
        gd = (self.ch3a_there_int == 1)
        if np.sum(gd) > 0:
            self.ch3a_there = True
        self.ch3b = ncid.variables['ch3b'][:,:]
        self.ch4 = ncid.variables['ch4'][:,:]
        try:
            self.ch5 = ncid.variables['ch5'][:,:]
            self.ch5_there = True
        except:
            self.ch5_there = False
        self.u_random_ch1 = ncid.variables['ch1_random'][:,:]
        self.u_random_ch2 = ncid.variables['ch2_random'][:,:]
        if self.ch3a_there:
            self.u_random_ch3a = ncid.variables['ch3a_random'][:,:]
        self.u_random_ch3b = ncid.variables['ch3b_random'][:,:]
        self.u_random_ch4 = ncid.variables['ch4_random'][:,:]
        if self.ch5_there:
            self.u_random_ch5 = ncid.variables['ch5_random'][:,:]
        self.u_non_random_ch1 = ncid.variables['ch1_non_random'][:,:]
        self.u_non_random_ch2 = ncid.variables['ch2_non_random'][:,:]
        if self.ch3a_there:
            self.u_non_random_ch3a = ncid.variables['ch3a_non_random'][:,:]
        self.u_non_random_ch3b = ncid.variables['ch3b_non_random'][:,:]
        self.u_non_random_ch4 = ncid.variables['ch4_non_random'][:,:]
        if self.ch5_there:
            self.u_non_random_ch5 = ncid.variables['ch5_non_random'][:,:]
        self.u_common_ch3b = ncid.variables['ch3b_common'][:,:]
        self.u_common_ch4 = ncid.variables['ch4_common'][:,:]
        if self.ch5_there:
            self.u_common_ch5 = ncid.variables['ch5_common'][:,:]
        self.u_common_ch1 = ncid.variables['ch1_common'][:,:]
        self.u_common_ch2 = ncid.variables['ch2_common'][:,:]
        if self.ch3a_there:
            self.u_common_ch3a = ncid.variables['ch3a_common'][:,:]
        self.scan_qual = ncid.variables['quality_scanline_bitmask'][:]
        self.chan_qual = ncid.variables['quality_channel_bitmask'][:,:]
        self.dBT3_over_dT = ncid.variables['dBT3_over_dT'][:,:]
        self.dBT4_over_dT = ncid.variables['dBT4_over_dT'][:,:]
        if self.ch5_there:
            self.dBT5_over_dT = ncid.variables['dBT5_over_dT'][:,:]
        self.dRe1_over_dCS = ncid.variables['dRe1_over_dCS'][:,:]
        self.dRe2_over_dCS = ncid.variables['dRe2_over_dCS'][:,:]
        if self.ch3a_there:
            self.dRe3a_over_dCS = ncid.variables['dRe3a_over_dCS'][:,:]
        self.dBT3_over_dCS = ncid.variables['dBT3_over_dCS'][:,:]
        self.dBT4_over_dCS = ncid.variables['dBT4_over_dCS'][:,:]
        if self.ch5_there:
            self.dBT5_over_dCS = ncid.variables['dBT5_over_dCS'][:,:]
        self.dBT3_over_dCICT = ncid.variables['dBT3_over_dCICT'][:,:]
        self.dBT4_over_dCICT = ncid.variables['dBT4_over_dCICT'][:,:]
        if self.ch5_there:
            self.dBT5_over_dCICT = ncid.variables['dBT5_over_dCICT'][:,:]
        self.smoothPRT = ncid.variables['dBT5_over_dCICT'][:]
        self.cal_cnts_noise = ncid.variables['cal_cnts_noise'][:]
        self.cnts_noise = ncid.variables['cnts_noise'][:]
        self.spatial_correlation_scale = ncid.spatial_correlation_scale
        self.ICT_Temperature_Uncertainty = ncid.ICT_Temperature_Uncertainty
        self.PRT_Uncertainty = ncid.PRT_Uncertainty
        self.noaa_string = ncid.noaa_string
        self.orbital_temperature = ncid.orbital_temperature
        self.scanline = ncid.variables['scanline'][:]
        self.orig_scanline = ncid.variables['orig_scanline'][:]
        self.ch3b_harm = ncid.variables['ch3b_harm_uncertainty'][:,:]
        self.ch4_harm = ncid.variables['ch4_harm_uncertainty'][:,:]
        self.ch5_harm = ncid.variables['ch5_harm_uncertainty'][:,:]

        self.badNav = ncid.variables['badNavigation'][:]
        self.badCal = ncid.variables['badCalibration'][:]
        self.badTime = ncid.variables['badTime'][:]
        self.missingLines = ncid.variables['missingLines'][:]
        self.solar3 = ncid.variables['solar_contam_3b'][:]
        self.solar4 = ncid.variables['solar_contam_4'][:]
        self.solar5 = ncid.variables['solar_contam_5'][:]

        self.nx = self.lat.shape[1]
        self.ny = self.lat.shape[0]

        try:
            self.montecarlo_seed = ncid.montecarlo_seed
            self.ch1_MC = ncid.variables['ch1_MC'][:,:,:]
            self.ch2_MC = ncid.variables['ch2_MC'][:,:,:]
            self.ch3a_MC = ncid.variables['ch3a_MC'][:,:,:]
            self.ch3_MC = ncid.variables['ch3_MC'][:,:,:]
            self.ch4_MC = ncid.variables['ch4_MC'][:,:,:]
            self.ch5_MC = ncid.variables['ch5_MC'][:,:,:]
            self.nmc = self.ch1_MC.shape[0]
            self.montecarlo = True
        except:
            self.montecarlo = False

        ncid.close()

        if True:
            self.lat = np.ma.filled(self.lat,np.NaN)
            self.lon = np.ma.filled(self.lon,np.NaN)
            self.time = np.ma.filled(self.time,np.NaN)
            self.satza = np.ma.filled(self.satza,np.NaN)
            self.solza = np.ma.filled(self.solza,np.NaN)
            self.relaz = np.ma.filled(self.relaz,np.NaN)
            self.ch1 = np.ma.filled(self.ch1,np.NaN)
            self.ch2 = np.ma.filled(self.ch2,np.NaN)
            if self.ch3a_there:
                self.ch3a = np.ma.filled(self.ch3a,np.NaN)
            self.ch3b = np.ma.filled(self.ch3b,np.NaN)
            self.ch4 = np.ma.filled(self.ch4,np.NaN)
            if self.ch5_there:
                self.ch5 = np.ma.filled(self.ch5,np.NaN)
            self.u_random_ch1 = np.ma.filled(self.u_random_ch1,np.NaN)
            self.u_random_ch2 = np.ma.filled(self.u_random_ch2,np.NaN)
            if self.ch3a_there:
                self.u_random_ch3a = np.ma.filled(self.u_random_ch3a,np.NaN)
            self.u_random_ch3b = np.ma.filled(self.u_random_ch3b,np.NaN)
            self.u_random_ch4 = np.ma.filled(self.u_random_ch4,np.NaN)
            if self.ch5_there:
                self.u_random_ch5 = np.ma.filled(self.u_random_ch5,np.NaN)
            self.u_non_random_ch1 = np.ma.filled(self.u_non_random_ch1,np.NaN)
            self.u_non_random_ch2 = np.ma.filled(self.u_non_random_ch2,np.NaN)
            if self.ch3a_there:
                self.u_non_random_ch3a = np.ma.filled(self.u_non_random_ch3a,np.NaN)
            self.u_non_random_ch3b = np.ma.filled(self.u_non_random_ch3b,np.NaN)
            self.u_non_random_ch4 = np.ma.filled(self.u_non_random_ch4,np.NaN)
            if self.ch5_there:
                self.u_non_random_ch5 = np.ma.filled(self.u_non_random_ch5,np.NaN)
            self.u_common_ch1 = np.ma.filled(self.u_common_ch1,np.NaN)
            self.u_common_ch2 = np.ma.filled(self.u_common_ch2,np.NaN)
            if self.ch3a_there:
                self.u_common_ch3a = np.ma.filled(self.u_common_ch3a,np.NaN)
            self.u_common_ch3b = np.ma.filled(self.u_common_ch3b,np.NaN)
            self.u_common_ch4 = np.ma.filled(self.u_common_ch4,np.NaN)
            if self.ch5_there:
                self.u_common_ch5 = np.ma.filled(self.u_common_ch5,np.NaN)
            self.dBT3_over_dT = np.ma.filled(self.dBT3_over_dT,np.NaN)
            self.dBT4_over_dT = np.ma.filled(self.dBT4_over_dT,np.NaN)
            if self.ch5_there:
                self.dBT5_over_dT = np.ma.filled(self.dBT5_over_dT,np.NaN)
            self.dRe1_over_dCS = np.ma.filled(self.dRe1_over_dCS,np.NaN)
            self.dRe2_over_dCS = np.ma.filled(self.dRe2_over_dCS,np.NaN)
            if self.ch3a_there:
                self.dRe3a_over_dCS = np.ma.filled(self.dRe3a_over_dCS,np.NaN)
            self.dBT3_over_dCS = np.ma.filled(self.dBT3_over_dCS,np.NaN)
            self.dBT4_over_dCS = np.ma.filled(self.dBT4_over_dCS,np.NaN)
            if self.ch5_there:
                self.dBT5_over_dCS = np.ma.filled(self.dBT5_over_dCS,np.NaN)
            self.dBT3_over_dCICT = np.ma.filled(self.dBT3_over_dCICT,np.NaN)
            self.dBT4_over_dCICT = np.ma.filled(self.dBT4_over_dCICT,np.NaN)
            if self.ch5_there:
                self.dBT5_over_dCICT = np.ma.filled(self.dBT5_over_dCICT,np.NaN)
            self.cal_cnts_noise = np.ma.filled(self.cal_cnts_noise,np.NaN)
            self.cnts_noise = np.ma.filled(self.cnts_noise,np.NaN)

            if self.montecarlo:
                self.ch1_MC = np.ma.filled(self.ch1_MC,np.NaN)
                self.ch2_MC = np.ma.filled(self.ch2_MC,np.NaN)
                self.ch3a_MC = np.ma.filled(self.ch3a_MC,np.NaN)
                self.ch3_MC = np.ma.filled(self.ch3_MC,np.NaN)
                self.ch4_MC = np.ma.filled(self.ch4_MC,np.NaN)
                self.ch5_MC = np.ma.filled(self.ch5_MC,np.NaN)

        self.lat = self.add_nan_values(self.lat)
        self.lon = self.add_nan_values(self.lon)
        self.time = self.add_nan_values(self.time)
        self.satza = self.add_nan_values(self.satza)
        self.relaz = self.add_nan_values(self.relaz)
        self.ch1 = self.add_nan_values(self.ch1)
        self.ch2 = self.add_nan_values(self.ch2)
        if self.ch3a_there:
            self.ch3a = self.add_nan_values(self.ch3a)
        self.ch3b = self.add_nan_values(self.ch3b)
        self.ch4 = self.add_nan_values(self.ch4)
        if self.ch5_there:
            self.ch5 = self.add_nan_values(self.ch5)
        self.u_random_ch1 = self.add_nan_values(self.u_random_ch1)
        self.u_random_ch2 = self.add_nan_values(self.u_random_ch2)
        if self.ch3a_there:
            self.u_random_ch3a = self.add_nan_values(self.u_random_ch3a)
        self.u_random_ch3b = self.add_nan_values(self.u_random_ch3b)
        self.u_random_ch4 = self.add_nan_values(self.u_random_ch4)
        if self.ch5_there:
            self.u_random_ch5 = self.add_nan_values(self.u_random_ch5)
        self.u_non_random_ch1 = self.add_nan_values(self.u_non_random_ch1)
        self.u_non_random_ch2 = self.add_nan_values(self.u_non_random_ch2)
        if self.ch3a_there:
            self.u_non_random_ch3a = self.add_nan_values(self.u_non_random_ch3a)
        self.u_non_random_ch3b = self.add_nan_values(self.u_non_random_ch3b)
        self.u_non_random_ch4 = self.add_nan_values(self.u_non_random_ch4)
        if self.ch5_there:
            self.u_non_random_ch5 = self.add_nan_values(self.u_non_random_ch5)
        self.u_common_ch1 = self.add_nan_values(self.u_common_ch1)
        self.u_common_ch2 = self.add_nan_values(self.u_common_ch2)
        if self.ch3a_there:
            self.u_common_ch3a = self.add_nan_values(self.u_common_ch3a)
        self.u_common_ch3b = self.add_nan_values(self.u_common_ch3b)
        self.u_common_ch4 = self.add_nan_values(self.u_common_ch4)
        if self.ch5_there:
            self.u_common_ch5 = self.add_nan_values(self.u_common_ch5)
        self.dBT3_over_dT = self.add_nan_values(self.dBT3_over_dT)
        self.dBT4_over_dT = self.add_nan_values(self.dBT4_over_dT)
        if self.ch5_there:
            self.dBT5_over_dT = self.add_nan_values(self.dBT5_over_dT)
        self.dRe1_over_dCS = self.add_nan_values(self.dRe1_over_dCS)
        self.dRe2_over_dCS = self.add_nan_values(self.dRe2_over_dCS)
        if self.ch3a_there:
            self.dRe3a_over_dCS = self.add_nan_values(self.dRe3a_over_dCS)
        self.dBT3_over_dCS = self.add_nan_values(self.dBT3_over_dCS)
        self.dBT4_over_dCS = self.add_nan_values(self.dBT4_over_dCS)
        if self.ch5_there:
            self.dBT5_over_dCS = self.add_nan_values(self.dBT5_over_dCS)
        self.dBT3_over_dCICT = self.add_nan_values(self.dBT3_over_dCICT)
        self.dBT4_over_dCICT = self.add_nan_values(self.dBT4_over_dCICT)
        if self.ch5_there:
            self.dBT5_over_dCICT = self.add_nan_values(self.dBT5_over_dCICT)
        self.cal_cnts_noise = self.add_nan_values(self.cal_cnts_noise)
        self.cnts_noise = self.add_nan_values(self.cnts_noise)
        self.ch3b_harm = self.add_nan_values(self.ch3b_harm)
        self.ch4_harm = self.add_nan_values(self.ch4_harm)
        self.ch5_harm = self.add_nan_values(self.ch5_harm)

        if self.montecarlo:
            self.ch1_MC = self.add_nan_values(self.ch1_MC)
            self.ch2_MC = self.add_nan_values(self.ch2_MC)
            self.ch3a_MC = self.add_nan_values(self.ch3a_MC)
            self.ch3_MC = self.add_nan_values(self.ch3_MC)
            self.ch4_MC = self.add_nan_values(self.ch4_MC)
            self.ch5_MC = self.add_nan_values(self.ch5_MC)

#        self.ch1 = self.scale_values(self.ch1)
#        self.ch2 = self.scale_values(self.ch2)
#        if self.ch3a_there:
#            self.ch3a = self.scale_values(self.ch3a)
#        self.u_random_ch1 = self.scale_values(self.u_random_ch1)
#        self.u_random_ch2 = self.scale_values(self.u_random_ch2)
#        if self.ch3a_there:
#            self.u_random_ch3a = self.scale_values(self.u_random_ch3a)
#        self.u_non_random_ch1 = self.scale_values(self.u_non_random_ch1)
#        self.u_non_random_ch2 = self.scale_values(self.u_non_random_ch2)
#        if self.ch3a_there:
#            self.u_non_random_ch3a = self.scale_values(self.u_non_random_ch3a)

        gd = np.zeros(len(self.time),dtype=np.bool)
        gd[:] = True
        for i in range(len(self.time)):
            if self.time[i] < 0:
                gd[i] = False
            else:
                break
        for i in range(len(self.time)-1,0,-1):
            if self.time[i] < 0:
                gd[i] = False
            else:
                break
        if np.sum(gd) == 0:
            raise Exception("cannot find good times")

        self.time = self.time[gd]
        ggd = (self.time < 0)
        if np.sum(ggd) > 0:
            self.time[ggd] = float('nan')
        date_time=[]
        for i in range(len(gd)):
            if gd[i]:
                date_time.append(self.date_time[i])
        self.date_time = date_time[:]
        self.lat = self.lat[gd,:]
        self.lon = self.lon[gd,:]
        self.satza = self.satza[gd,:]
        self.solza = self.solza[gd,:]
        self.relaz = self.relaz[gd,:]
        self.ch1 = self.ch1[gd,:]
        self.ch2 = self.ch2[gd,:]
        self.ch3a = self.ch3a[gd,:]
        self.ch3a_there_int = self.ch3a_there_int[gd]
        self.ch3b = self.ch3b[gd,:]
        self.ch4 = self.ch4[gd,:]
        if self.ch5_there:
            self.ch5 = self.ch5[gd,:]

        self.u_random_ch1 = self.u_random_ch1[gd,:]
        self.u_random_ch2 = self.u_random_ch2[gd,:]
        if self.ch3a_there:
            self.u_random_ch3a = self.u_random_ch3a[gd,:]
        self.u_random_ch3b = self.u_random_ch3b[gd,:]
        self.u_random_ch4 = self.u_random_ch4[gd,:]
        if self.ch5_there:
            self.u_random_ch5 = self.u_random_ch5[gd,:]

        self.u_non_random_ch1 = self.u_non_random_ch1[gd,:]
        self.u_non_random_ch2 = self.u_non_random_ch2[gd,:]
        if self.ch3a_there:
            self.u_non_random_ch3a = self.u_non_random_ch3a[gd,:]
        self.u_non_random_ch3b = self.u_non_random_ch3b[gd,:]
        self.u_non_random_ch4 = self.u_non_random_ch4[gd,:]
        if self.ch5_there:
            self.u_non_random_ch5 = self.u_non_random_ch5[gd,:]

        self.u_common_ch1 = self.u_common_ch1[gd,:]
        self.u_common_ch2 = self.u_common_ch2[gd,:]
        if self.ch3a_there:
            self.u_common_ch3a = self.u_common_ch3a[gd,:]
        self.u_common_ch3b = self.u_common_ch3b[gd,:]
        self.u_common_ch4 = self.u_common_ch4[gd,:]
        if self.ch5_there:
            self.u_common_ch5 = self.u_common_ch5[gd,:]

        self.scan_qual = self.scan_qual[gd]
        self.chan_qual = self.chan_qual[gd,:]

        self.dBT3_over_dT = self.dBT3_over_dT[gd,:]
        self.dBT4_over_dT = self.dBT4_over_dT[gd,:]
        if self.ch5_there:
            self.dBT5_over_dT = self.dBT5_over_dT[gd,:]

        self.dRe1_over_dCS = self.dRe1_over_dCS[gd,:]
        self.dRe2_over_dCS = self.dRe2_over_dCS[gd,:]
        if self.ch3a_there:
            self.dRe3a_over_dCS = self.dRe3a_over_dCS[gd,:]
        self.dBT3_over_dCS = self.dBT3_over_dCS[gd,:]
        self.dBT4_over_dCS = self.dBT4_over_dCS[gd,:]
        if self.ch5_there:
            self.dBT5_over_dCS = self.dBT5_over_dCS[gd,:]

        self.dBT3_over_dCICT = self.dBT3_over_dCICT[gd,:]
        self.dBT4_over_dCICT = self.dBT4_over_dCICT[gd,:]
        if self.ch5_there:
            self.dBT5_over_dCICT = self.dBT5_over_dCICT[gd,:]

        self.smoothPRT = self.smoothPRT[gd]
        self.scanline = self.scanline[gd]
        self.orig_scanline = self.orig_scanline[gd]
        self.ch3b_harm = self.ch3b_harm[gd,:]
        self.ch4_harm = self.ch4_harm[gd,:]
        self.ch5_harm = self.ch5_harm[gd,:]

        self.badNav = self.badNav[gd]
        self.badCal = self.badCal[gd]
        self.badTime = self.badTime[gd]
        self.missingLines = self.missingLines[gd]
        self.solar3 = self.solar3[gd]
        self.solar4 = self.solar4[gd]
        self.solar5 = self.solar5[gd]

        self.nx = self.lat.shape[1]
        self.ny = self.lat.shape[0]

        if self.montecarlo:
            self.ch1_MC = self.ch1_MC[:,gd,:]
            self.ch2_MC = self.ch2_MC[:,gd,:]
            self.ch3a_MC = self.ch3a_MC[:,gd,:]
            self.ch3_MC = self.ch3_MC[:,gd,:]
            self.ch4_MC = self.ch4_MC[:,gd,:]
            self.ch5_MC = self.ch5_MC[:,gd,:]
            self.nmc = self.ch1_MC.shape[0]

    def __init__(self,filename):

        self.read_data(filename)
#
# Run Gerrits CURUC routines
#
#
# Force bad data to be nan's
#
def set_to_nan(TL):

    # Set -1e30 to NaN
    gd = np.isfinite(TL)
    newTL = TL[gd]
    gd2 = (newTL < -1e20)
    if np.sum(gd2) > 0:
        newTL[gd2] = float('nan')
        TL[gd] = newTL
    if np.ma.is_masked(TL):
        gd = ~TL.mask
        TL[gd] = float('nan')

    return TL

#
# Copy over to sensitivity using the coords (xarray) arrays
#
def copy_over_C(inarray,n_l_coord,n_e_coord,inverse=False,string=''):

    nbad = 0
    nbad_orig = 0
    if inverse:
        outarray = np.zeros((len(n_e_coord.values),len(n_l_coord.values)))
        for i in range(len(n_l_coord.values)):
            outarray[:,i] = np.copy(inarray[n_l_coord.values[i],n_e_coord.values])
    else:
        outarray = np.zeros((len(n_l_coord.values),len(n_e_coord.values)))
        for i in range(len(n_l_coord.values)):
            outarray[i,:] = np.copy(inarray[n_l_coord.values[i],n_e_coord.values])
    return outarray

#
# Do copy in a block and deal with different channel selection
#
def copy_C3(dBT3_over_dX,dBT4_over_dX,dBT5_over_dX,\
                n_l,n_e,chans,inverse=False,xchan=False):

    if xchan:
        if inverse:
            output = np.zeros((len(n_e),len(n_l),len(chans)))
            for i in range(len(chans)):
                if 3 == chans[i]:
                    output[:,:,i] = copy_over_C(dBT3_over_dX,n_l,n_e,inverse=True,\
                                                    string='dBT3_over_dX xchan inverse')
                elif 4 == chans[i]:
                    output[:,:,i] = copy_over_C(dBT4_over_dX,n_l,n_e,inverse=True,\
                                                    string='dBT3_over_dX xchan inverse')
                elif 5 == chans[i]:
                    output[:,:,i] = copy_over_C(dBT5_over_dX,n_l,n_e,inverse=True,\
                                                    string='dBT3_over_dX xchan inverse')
        else:
            output = np.zeros((len(n_l),len(n_e),len(chans)))
            for i in range(len(chans)):
                if 3 == chans[i]:
                    output[:,:,i] = copy_over_C(dBT3_over_dX,n_l,n_e,\
                                                    string='dBT3_over_dX xchan')
                elif 4 == chans[i]:
                    output[:,:,i] = copy_over_C(dBT4_over_dX,n_l,n_e,\
                                                    string='dBT3_over_dX xchan')
                elif 5 == chans[i]:
                    output[:,:,i] = copy_over_C(dBT5_over_dX,n_l,n_e,\
                                                    string='dBT3_over_dX xchan')
    else:
        if inverse:
            output = np.zeros((len(chans),len(n_e),len(n_l)))
            for i in range(len(chans)):
                if 3 == chans[i]:
                    output[i,:,:] = copy_over_C(dBT3_over_dX,n_l,n_e,inverse=True,\
                                                    string='dBT3_over_dX not xchan inverse')
                elif 4 == chans[i]:
                    output[i,:,:] = copy_over_C(dBT4_over_dX,n_l,n_e,inverse=True,\
                                                    string='dBT3_over_dX not xchan inverse')
                elif 5 == chans[i]:
                    output[i,:,:] = copy_over_C(dBT5_over_dX,n_l,n_e,inverse=True,\
                                                    string='dBT3_over_dX not xchan inverse')
        else:
            output = np.zeros((len(chans),len(n_l),len(n_e)))
            for i in range(len(chans)):
                if 3 == chans[i]:
                    output[i,:,:] = copy_over_C(dBT3_over_dX,n_l,n_e,\
                                                    string='dBT3_over_dX not xchan')
                elif 4 == chans[i]:
                    output[i,:,:] = copy_over_C(dBT4_over_dX,n_l,n_e,\
                                                    string='dBT3_over_dX not xchan')
                elif 5 == chans[i]:
                    output[i,:,:] = copy_over_C(dBT5_over_dX,n_l,n_e,\
                                                    string='dBT3_over_dX not xchan')
                    
    return output
#
# No 12 micron channel case
#
def copy_C2(dBT3_over_dX,dBT4_over_dX,\
                n_l,n_e,chans,inverse=False,xchan=False,ch3a=False):

    if ch3a:
        if xchan:
            if inverse:
                output = np.zeros((len(n_e),len(n_l),len(chans)))
                for i in range(len(chans)):
                    if 4 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT3_over_dX,n_l,n_e,inverse=True)
                    elif 5 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT4_over_dX,n_l,n_e,inverse=True)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
            else:
                output = np.zeros((len(n_l),len(n_e),len(chans)))
                for i in range(len(chans)):
                    if 4 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT3_over_dX,n_l,n_e)
                    elif 5 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT4_over_dX,n_l,n_e)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
        else:
            if inverse:
                output = np.zeros((len(chans),len(n_e),len(n_l)))
                for i in range(len(chans)):
                    if 4 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT3_over_dX,n_l,n_e,inverse=True)
                    elif 5 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT4_over_dX,n_l,n_e,inverse=True)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
            else:
                output = np.zeros((len(chans),len(n_l),len(n_e)))
                for i in range(len(chans)):
                    if 4 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT3_over_dX,n_l,n_e)
                    elif 5 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT4_over_dX,n_l,n_e)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
    else:
        if xchan:
            if inverse:
                output = np.zeros((len(n_e),len(n_l),len(chans)))
                for i in range(len(chans)):
                    if 3 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT3_over_dX,n_l,n_e,inverse=True)
                    elif 4 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT4_over_dX,n_l,n_e,inverse=True)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
            else:
                output = np.zeros((len(n_l),len(n_e),len(chans)))
                for i in range(len(chans)):
                    if 3 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT3_over_dX,n_l,n_e)
                    elif 4 == chans[i]:
                        output[:,:,i] = copy_over_C(dBT4_over_dX,n_l,n_e)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
        else:
            if inverse:
                output = np.zeros((len(chans),len(n_e),len(n_l)))
                for i in range(len(chans)):
                    if 3 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT3_over_dX,n_l,n_e,inverse=True)
                    elif 4 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT4_over_dX,n_l,n_e,inverse=True)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')
            else:
                output = np.zeros((len(chans),len(n_l),len(n_e)))
                for i in range(len(chans)):
                    if 3 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT3_over_dX,n_l,n_e)
                    elif 4 == chans[i]:
                        output[i,:,:] = copy_over_C(dBT4_over_dX,n_l,n_e)
                    else:
                        print('chans:',chans)
                        raise Exception('chans out of range in copy_C2')

    return output

#
# Visible channel case - only from CS data
#

#
# Do copy in a block and deal with different channel selection
#
def copy_C3_vis(dRe1_over_dCS,dRe2_over_dCS,dRe3a_over_dCS,\
                n_l,n_e,chans,inverse=False,xchan=False):

    if xchan:
        if inverse:
            output = np.zeros((len(n_e),len(n_l),len(chans)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe1_over_dCS,n_l,n_e,inverse=True)
                elif 1 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe2_over_dCS,n_l,n_e,inverse=True)
                elif 2 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe3a_over_dCS,n_l,n_e,inverse=True)
        else:
            output = np.zeros((len(n_l),len(n_e),len(chans)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe1_over_dCS,n_l,n_e)
                elif 1 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe2_over_dCS,n_l,n_e)
                elif 2 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe3a_over_dCS,n_l,n_e)
    else:
        if inverse:
            output = np.zeros((len(chans),len(n_e),len(n_l)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe1_over_dCS,n_l,n_e,inverse=True)
                elif 1 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe2_over_dCS,n_l,n_e,inverse=True)
                elif 2 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe3a_over_dCS,n_l,n_e,inverse=True)
        else:
            output = np.zeros((len(chans),len(n_l),len(n_e)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe1_over_dCS,n_l,n_e)
                elif 1 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe2_over_dCS,n_l,n_e)
                elif 2 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe3a_over_dCS,n_l,n_e)
                    
    return output
#
# No 1.6 micron channel case
#
def copy_C2_vis(dRe1_over_dCS,dRe2_over_dCS,\
                n_l,n_e,chans,inverse=False,xchan=False):

    if xchan:
        if inverse:
            output = np.zeros((len(n_e),len(n_l),len(chans)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe1_over_dCS,n_l,n_e,inverse=True)
                elif 1 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe2_over_dCS,n_l,n_e,inverse=True)
                else:
                    raise Exception('chans out of range in copy_C2_vis')
        else:
            output = np.zeros((len(n_l),len(n_e),len(chans)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe1_over_dCS,n_l,n_e)
                elif 1 == chans[i]:
                    output[:,:,i] = copy_over_C(dRe2_over_dCS,n_l,n_e)
                else:
                    raise Exception('chans out of range in copy_C2_vis')
    else:
        if inverse:
            output = np.zeros((len(chans),len(n_e),len(n_l)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe1_over_dCS,n_l,n_e,inverse=True)
                elif 1 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe2_over_dCS,n_l,n_e,inverse=True)
                else:
                    raise Exception('chans out of range in copy_C2_vis')
        else:
            output = np.zeros((len(chans),len(n_l),len(n_e)))
            for i in range(len(chans)):
                if 0 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe1_over_dCS,n_l,n_e)
                elif 1 == chans[i]:
                    output[i,:,:] = copy_over_C(dRe2_over_dCS,n_l,n_e)
                else:
                    raise Exception('chans out of range in copy_C2_vis')

    return output

#
# Check for bad data at the array level
#
def check_for_bad_data_TL(array):

    test1 = ~np.isfinite(array)
    gd = np.isfinite(array)
    test2 = (array[gd] < -1e20)
    if np.ma.is_masked(array):
        test3 = ~array.mask 
        error = np.sum(test1) + np.sum(test2) + np.sum(test3)
    else:
        error = np.sum(test1) + np.sum(test2)
    if 0 == error:
        return False
    else:
        return True

#
# Check for bad data to mask out in CURUC routines
#
def check_bad_data_5(lines,elems,quality,dBT3_over_dT,dBT4_over_dT,\
                         dBT5_over_dT,dBT3_over_dCS,\
                         dBT4_over_dCS,dBT5_over_dCS,\
                         dBT3_over_dCICT,dBT4_over_dCICT,\
                         dBT5_over_dCICT,single=False):

    index = np.zeros(len(lines),dtype=np.int32)
    
    j=0
    for i in range(len(lines)): 
        if not single:
            test = (quality[lines[i]] > 0) or \
                check_for_bad_data_TL(dBT3_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT5_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT3_over_dCS[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dCS[lines[i],elems]) or \
                check_for_bad_data_TL(dBT5_over_dCS[lines[i],elems]) or \
                check_for_bad_data_TL(dBT3_over_dCICT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dCICT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT5_over_dCICT[lines[i],elems])
        else:
            test = (quality[lines[i]] > 0) or \
                check_for_bad_data_TL(dBT3_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT5_over_dT[lines[i],elems])
        if test:
            index[j] = i
            j=j+1

    index = index[0:j]

    return index

def check_bad_data_no5(lines,elems,quality,dBT3_over_dT,dBT4_over_dT,\
                         dBT3_over_dCS,\
                         dBT4_over_dCS,\
                         dBT3_over_dCICT,dBT4_over_dCICT,\
                         single=False):

    index = np.zeros(len(lines),dtype=np.int32)
    
    j=0
    for i in range(len(lines)): 
        if not single:
            test = (quality[lines[i]] > 0) or \
                check_for_bad_data_TL(dBT3_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT3_over_dCS[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dCS[lines[i],elems]) or \
                check_for_bad_data_TL(dBT3_over_dCICT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dCICT[lines[i],elems])
        else:
            test = (quality[lines[i]] > 0) or \
                check_for_bad_data_TL(dBT3_over_dT[lines[i],elems]) or \
                check_for_bad_data_TL(dBT4_over_dT[lines[i],elems])
        if test:
            index[j] = i
            j=j+1

    index = index[0:j]

    return index

def check_bad_data_3(lines,elems,quality,\
                         dRe1_over_dCS,\
                         dRe2_over_dCS,\
                         dRe3_over_dCS):

    index = np.zeros(len(lines),dtype=np.int32)
    
    j=0
    for i in range(len(lines)): 
        test = (quality[lines[i]] > 0) or \
            check_for_bad_data_TL(dRe1_over_dCS[lines[i],elems]) or \
            check_for_bad_data_TL(dRe2_over_dCS[lines[i],elems]) or \
            check_for_bad_data_TL(dRe3_over_dCS[lines[i],elems]) 
        if test:
            index[j] = i
            j=j+1

    index = index[0:j]

    return index

def check_bad_data_no3(lines,elems,quality,\
                         dRe1_over_dCS,\
                         dRe2_over_dCS):

    index = np.zeros(len(lines),dtype=np.int32)
    
    j=0
    for i in range(len(lines)): 
        test = (quality[lines[i]] > 0) or \
            check_for_bad_data_TL(dRe1_over_dCS[lines[i],elems]) or \
            check_for_bad_data_TL(dRe2_over_dCS[lines[i],elems]) 
        if test:
            index[j] = i
            j=j+1

    index = index[0:j]

    return index

#
# Replace bad lines with NaNs
#
def replace_NaN_ind(array,mask,datatype=1):

    if datatype == 1:
        for i in range(array.values.shape[0]):
            if mask[i]:
                array.values[i,:,:,:] = float('nan')
    elif datatype == 2:
        for i in range(array.values.shape[1]):
            if mask[i]:
                array.values[:,i,:,:] = float('nan')
    elif datatype == 3:
        for i in range(array.values.shape[2]):
            if mask[i]:
                array.values[:,:,i,:] = float('nan')
    elif datatype == 4:
        for i in range(array.values.shape[3]):
            if mask[i]:
                array.values[:,:,:,i] = float('nan')

    return array
                            
#
# Replace TINY for individual array and then replace bad lines with NaNs
#
def replace_TINY_ind(array,derivative=None,derivative_there=False,datatype=1,\
                         datatype_nan=1,mask=None,outprint=None):

    if 1 == datatype:
        for i in range(array.values.shape[0]):
            for j in range(array.values.shape[1]):
                for k in range(array.values.shape[2]):                    
                    testarray = array.values[i,j,k,:]
                    if derivative_there:
                        derarray = derivative.values[i,j,k,:]
                        gd = (derarray == 1e-10)
                    else:
                        gd = (testarray == 1e-10)
                    if np.sum(gd) > 0:
                        gd2 = (testarray != 1e-10)
                        if np.sum(gd2) > 0:
                            newarray = testarray[gd2]
                            array.values[i,j,k,:] = np.median(newarray)
    elif 2 == datatype:
        for i in range(array.values.shape[0]):
            for j in range(array.values.shape[1]):
                for k in range(array.values.shape[3]):
                    testarray = array.values[i,j,:,k]
                    if derivative_there:
                        derarray = derivative.values[i,j,:,k]
                        gd = (derarray == 1e-10)
                    else:
                        gd = (testarray == 1e-10)
                    if np.sum(gd) > 0:
                        gd2 = (testarray != 1e-10)
                        if np.sum(gd2) > 0:
                            newarray = testarray[gd2]
                            array.values[i,j,:,k] = np.median(newarray)
    elif 3 == datatype:
        for i in range(array.values.shape[0]):
            for j in range(array.values.shape[2]):
                for k in range(array.values.shape[3]):
                    testarray = array.values[i,:,j,k]
                    if derivative_there:
                        #
                        # Note that for some reason the shape of the derivative
                        # in this case is different, so different ordering
                        #
                        derarray = derivative.values[j,i,:,k]
                        gd = (derarray == 1e-10)
                    else:
                        gd = (testarray == 1e-10)
                    if np.sum(gd) > 0:
                        gd2 = (testarray != 1e-10)
                        if np.sum(gd2) > 0:
                            newarray = testarray[gd2]
                            array.values[i,:,j,k] = np.median(newarray)

    #
    # Anything < -1e20 with nans
    #
    gd = (array.values < -1e20)
    if np.sum(gd) > 0:
        array.values[gd] = float('nan')

    #
    # Replace data in bad lines with NaNs if mask present
    #
    if mask is None:
        pass
    else:
        array = replace_NaN_ind(array,mask,datatype=datatype_nan)

    return array
                            
#
# Replace TINY values with median values
# Used for HIRS based on Gerrit's comments
#
def replace_TINY(U_xelem_s,U_xline_s,U_xchan_i,U_xchan_s,\
                     C_xelem_s,C_xline_s,C_xchan_i,C_xchan_s,mask=None):

    U_xelem_s_new = replace_TINY_ind(U_xelem_s,\
                                         derivative=C_xelem_s,\
                                         derivative_there=True,\
                                         datatype=1,datatype_nan=3,\
                                         mask=mask,outprint='U_xelem_s')
    C_xelem_s_new = replace_TINY_ind(C_xelem_s,datatype=1,\
                                         datatype_nan=3,\
                                         mask=mask,outprint='C_xelem_s')
    U_xline_s_new = replace_TINY_ind(U_xline_s,derivative=C_xline_s,\
                                         derivative_there=True,\
                                         datatype=2,datatype_nan=4,\
                                         mask=mask,outprint='U_xline_s')
    C_xline_s_new = replace_TINY_ind(C_xline_s,datatype=2,\
                                         datatype_nan=4,\
                                         mask=mask,outprint='C_xline_s')
    U_xchan_i_new = replace_TINY_ind(U_xchan_i,derivative=C_xchan_i,\
                                         derivative_there=True,datatype=2,\
                                         datatype_nan=2,\
                                         mask=mask,outprint='U_xchan_i')
    C_xchan_i_new = replace_TINY_ind(C_xchan_i,datatype=2,\
                                         datatype_nan=2,\
                                         mask=mask,outprint='C_xchan_i')
    U_xchan_s_new = replace_TINY_ind(U_xchan_s,derivative=C_xchan_s,\
                                         derivative_there=True,datatype=3,\
                                         datatype_nan=1,\
                                         mask=mask,outprint='U_xchan_s')
    C_xchan_s_new = replace_TINY_ind(C_xchan_s,datatype=3,\
                                         datatype_nan=2,\
                                         mask=mask,outprint='C_xchan_s')
    gd = np.isfinite(U_xelem_s_new.values)

    return U_xelem_s_new,U_xline_s_new,U_xchan_i_new,U_xchan_s_new,\
                     C_xelem_s_new,C_xline_s_new,C_xchan_i_new,C_xchan_s_new

def plot_hist(datum,mask,title,subplot,datatype):
    
    if -1 != subplot:
        plt.subplot(2,2,subplot)
    if datatype == 1:
        ndata = datum.values.shape[0]
        array = np.zeros((1,datum.values.shape[1],datum.values.shape[2],datum.values.shape[3])) 
        inarray = np.zeros((1,datum.values.shape[1],datum.values.shape[2],datum.values.shape[3])) 
    elif datatype == 2:
        ndata = datum.values.shape[1]
        array = np.zeros((1,datum.values.shape[0],datum.values.shape[2],datum.values.shape[3])) 
        inarray = np.zeros((1,datum.values.shape[0],datum.values.shape[2],datum.values.shape[3])) 
    elif datatype == 3:
        ndata = datum.values.shape[2]
        array = np.zeros((1,datum.values.shape[0],datum.values.shape[1],datum.values.shape[3])) 
        inarray = np.zeros((1,datum.values.shape[0],datum.values.shape[1],datum.values.shape[3])) 
    elif datatype == 4:
        ndata = datum.values.shape[3]
        array = np.zeros((1,datum.values.shape[0],datum.values.shape[1],datum.values.shape[2])) 
        inarray = np.zeros((1,datum.values.shape[0],datum.values.shape[1],datum.values.shape[2])) 

    j=0
    for i in range(ndata):
        if not mask[i]:
            if 0 == j:
                if datatype == 1:
                    array[0,:,:,:] = datum.values[i,:,:,:]
                elif datatype == 2:
                    array[0,:,:,:] = datum.values[:,i,:,:]
                elif datatype == 3:
                    array[0,:,:,:] = datum.values[:,:,i,:]
                elif datatype == 4:
                    array[0,:,:,:] = datum.values[:,:,:,i]
                j=j+1
            else:
                if datatype == 1:
                    inarray[0,:,:,:] = datum.values[i,:,:,:]
                elif datatype == 2:
                    inarray[0,:,:,:] = datum.values[:,i,:,:]
                elif datatype == 3:
                    inarray[0,:,:,:] = datum.values[:,:,i,:]
                elif datatype == 4:
                    inarray[0,:,:,:] = datum.values[:,:,:,i]
                array = np.append(array,inarray,axis=0)
                j=j+1
    print('For {0} : nlines={1:d}'.format(title,j))
    arr = array.flatten()
    plt.hist(arr,bins=100)
    plt.title(title)
    gd = (arr == 0.)
    if np.sum(gd) > 0:
        print('There are ZEROs present')

#
# Set 1's for bad scanline quality
#
def bad_scan_quality(scan_qual):

#         1,        2,              4,               8,                16,                        32,                  64
#DO_NOT_USE, BAD_TIME, BAD_NAVIGATION, BAD_CALIBRATION, CHANNEL3A_PRESENT,SOLAR_CONTAMINATION,SOLAR_IN_EARTHVIEW

    out_scan = np.zeros(len(scan_qual),dtype=np.int8)
    for i in range(len(scan_qual)):
        if 1 == scan_qual[i]&1 or 2 == scan_qual[i]&2 or \
                4 == scan_qual[i]&4 or 8 == scan_qual[i]&8:
            out_scan[i] = 1

    return out_scan

def run_CURUC(data,inchans,vis_chans=False,common=False,\
                  line_skip=5,elem_skip=25,ch3a_version=False):

    #
    # Check chans in right order - note chans goes from 0 to 5
    #
    chans = np.sort(inchans)
    #
    # Allocate CURUC arrays
    #
    # Note three systematic effects considered:
    #
    #    1) Uncertainty in the ICT temperature
    #    2) Uncertainty in the space view counts
    #    3) Uncertainty in the ICT view counts
    #
    # Effect 1-3 are all spatially correlated due to the averaging
    #
    # Effect 1 will cause a cross channel correlation
    #
    # Just noise for the independent effect
    #
    nlines = data.ch1.shape[0]
    nelems = data.ch1.shape[1]
    #
    # Define number of structured and common effects to deal with (common 
    # effects for channel to channel only)
    #
    if vis_chans:
        # CS only
        neffects_s = 1
    else:
        if common:
            # ICT T and Harmonisation
            neffects_s = 2
        else:
            # CS, CICT, ICT T
            neffects_s = 3
    # Noise
    neffects_i = 1
    nchans = len(chans)
    R_xelem_s, R_xline_s, R_xchan_i, R_xchan_s,\
        U_xelem_s, U_xline_s, U_xchan_s, U_xchan_i,\
        C_xelem_s, C_xline_s, C_xchan_s, C_xchan_i, coords = \
        met.allocate_curuc(nchans,nlines,nelems,neffects_s,neffects_i,\
                               line_skip,elem_skip)

    # Fill CURUC arrays
    #
    # First define R (correlation) matrices
    #
    # Cross element
    R_xelem_s.values[...] = 1  # Fully systematic across elements
    
    # Cross line - block diagonal
    # Uses temp array for spatial correlation which is the copied
    # to all channels etc.
    Temp_array = np.zeros((len(R_xline_s.coords['n_l']),\
                               len(R_xline_s.coords['n_l'])))

    N = data.spatial_correlation_scale
    Nsize = N//line_skip
    step_size = line_skip*1./N

    for step in range(-Nsize,Nsize+1):
        diagonal = np.diagonal(Temp_array,step)
        diagonal.setflags(write=True)
        diagonal[:] = 1.-np.abs(step)*step_size

    R_xline_s.values[:,:,:,:,:] = \
        Temp_array[np.newaxis,np.newaxis,np.newaxis,:,:]

    # Cross channel (independent)
    # effects, lines, elements, chan, chan
    R_xchan_i.values[0,:,:,:,:] = 1

    # Cross channel (systematic)
    # Set cross channel only for effect which is cross channel
    # Other effects have Identity matrix
    # Take into account visible channels which are not correlated with
    # the first effect (Tict)
    # Diagnonal for the vis chans, full matrix for the IR chans
    if vis_chans:
        for i in range(len(chans)):
            R_xchan_s.values[0,:,:,i,i] = 1
    else:
        #
        # Note that Harmonisation is uncorrelated in channel space
        #
        R_xchan_s.values[0,:,:,:,:] = 1
        Temp_array = np.zeros((len(R_xline_s.coords['n_c']),\
                                   len(R_xline_s.coords['n_c'])))
        Temp_array[:,:] = np.identity(len(R_xline_s.coords['n_c']))
        R_xchan_s.values[1,:,:,:,:] = Temp_array[np.newaxis,np.newaxis,:,:]
        if not common:
            #
            # Add last effect if not common (systematic)
            #
            R_xchan_s.values[2,:,:,:,:] = Temp_array[np.newaxis,np.newaxis,:,:]

    # Map uncertainties (which are constant in the T, Counts space).
    # All these are averaged over the smoothing scale (+/-)
    # Elements
    # n_c, n_s, n_l, n_e
    #
    # First one is the ICT temperature one
    if vis_chans:
        # noise term only
        for i in range(len(chans)):
            U_xelem_s.values[i,0,:,:] = data.cal_cnts_noise[chans[i]]
    else:
        U_xelem_s.values[:,0,:,:] = \
            np.sqrt(data.ICT_Temperature_Uncertainty**2+\
                        data.PRT_Uncertainty**2)

        if common:
            for i in range(len(chans)):
                if chans[i] == 3:
                    newarray = copy_over_C(data.ch3b_harm,\
                                               U_xelem_s.coords['n_l'],\
                                               U_xelem_s.coords['n_e'])
                elif chans[i] == 4:
                    newarray = copy_over_C(data.ch4_harm,\
                                               U_xelem_s.coords['n_l'],\
                                               U_xelem_s.coords['n_e'])
                elif chans[i] == 5:
                    newarray = copy_over_C(data.ch5_harm,\
                                               U_xelem_s.coords['n_l'],\
                                               U_xelem_s.coords['n_e'])
                U_xelem_s.values[i,1,:,:] = newarray[:,:]
        else:
            # Second is the Space view one
            for i in range(len(chans)):
                U_xelem_s.values[i,1,:,:] = data.cal_cnts_noise[chans[i]]
                
            # Third is the ICT view one
            for i in range(len(chans)):
                U_xelem_s.values[i,2,:,:] = data.cal_cnts_noise[chans[i]]

    # Cross line case
    # Elements
    # n_c, n_s, n_e, n_l
    #
    # For vis just av noise, IR three component
    #
    if vis_chans:
        for i in range(len(chans)):
            U_xline_s.values[i,0,:,:] = data.cal_cnts_noise[chans[i]]
    else:
        U_xline_s.values[:,0,:,:] = \
            np.sqrt(data.ICT_Temperature_Uncertainty**2+\
                        data.PRT_Uncertainty**2)

        if common:
            for i in range(len(chans)):
                if chans[i] == 3:
                    newarray = copy_over_C(data.ch3b_harm,\
                                               U_xline_s.coords['n_l'],\
                                               U_xline_s.coords['n_e'],\
                                               inverse=True)
                elif chans[i] == 4:
                    newarray = copy_over_C(data.ch4_harm,\
                                               U_xline_s.coords['n_l'],\
                                               U_xline_s.coords['n_e'],\
                                               inverse=True)
                elif chans[i] == 5:
                    newarray = copy_over_C(data.ch5_harm,\
                                               U_xline_s.coords['n_l'],\
                                               U_xline_s.coords['n_e'],\
                                               inverse=True)
                U_xline_s.values[i,1,:,:] = newarray[:,:]
        else:
            # Second is the Space view one
            for i in range(len(chans)):
                U_xline_s.values[i,1,:,:] = data.cal_cnts_noise[chans[i]]

            # Third is the ICT view one
            for i in range(len(chans)):
                U_xline_s.values[i,2,:,:] = data.cal_cnts_noise[chans[i]]

    # Uncertainties for channel to channel (systematic)
    # Elements
    # n_l, n_e, n_s, n_c
    #
    # Only ICT temperature is cross channel
    #
    # But in CURUC all are considered to match to stored uncertainties
    # in FCDR file
    #
    # Note have to remember first 2/3 channels are vis chans so no
    # temperature uncertainty
    #
    if vis_chans:
        pass
    else:
        U_xchan_s.values[:,:,0,:] = \
            np.sqrt(data.ICT_Temperature_Uncertainty**2+\
                        data.PRT_Uncertainty**2)
        if  common:
            for i in range(len(chans)):
                if chans[i] == 3:
                    newarray = copy_over_C(data.ch3b_harm,\
                                               U_xchan_s.coords['n_l'],\
                                               U_xchan_s.coords['n_e'])
                elif chans[i] == 4:
                    newarray = copy_over_C(data.ch4_harm,\
                                               U_xchan_s.coords['n_l'],\
                                               U_xchan_s.coords['n_e'])
                elif chans[i] == 5:
                    newarray = copy_over_C(data.ch5_harm,\
                                               U_xchan_s.coords['n_l'],\
                                               U_xchan_s.coords['n_e'])
                U_xchan_s.values[:,:,1,i] = newarray[:,:]
        else:
            for i in range(len(chans)):
                U_xchan_s.values[:,:,1,i] = data.cal_cnts_noise[chans[i]]
            # Only IR channels as this is noise on ICT counts
            for i in range(len(chans)):
                U_xchan_s.values[:,:,2,i] = data.cal_cnts_noise[chans[i]]

    # Uncertainties for channel to channel (independent) - zero
    # Note single pixel noise here
    for i in range(len(chans)):
        U_xchan_i.values[:,:,:,i] = data.cnts_noise[chans[i]]
        
    # Map sensitivities using coordinates
    # This has to use the coordinates to make correctly as the sensitivities
    # change pixel to pixel
    # 3.7 micron channel
    if vis_chans:
        #
        # Visible channel case now - only for CS averaging no X channel
        #
        if ch3a_version:
            C_xelem_s.values[:,0,:,:] = \
                copy_C3_vis(data.dRe1_over_dCS,data.dRe2_over_dCS,data.dRe3a_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans)

            C_xline_s.values[:,0,:,:] = \
                copy_C3_vis(data.dRe1_over_dCS,data.dRe2_over_dCS,data.dRe3a_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True)

        else: # Don't have channel 1.6 and no X channel
            C_xelem_s.values[:,0,:,:] = \
                copy_C2_vis(data.dRe1_over_dCS,data.dRe2_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans)

            C_xline_s.values[:,0,:,:] = \
                copy_C2_vis(data.dRe1_over_dCS,data.dRe2_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True)
    else:
        # 3.7,11 and 12 micron channels present
        if data.ch5_there and not ch3a_version:
            C_xelem_s.values[:,0,:,:] = \
                copy_C3(data.dBT3_over_dT,data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans)
            if common:
                C_xelem_s.values[:,1,:,:] = 1
            else:
                C_xelem_s.values[:,1,:,:] = \
                    copy_C3(data.dBT3_over_dCS,data.dBT4_over_dCS,data.dBT5_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans)
                C_xelem_s.values[:,2,:,:] = \
                    copy_C3(data.dBT3_over_dCICT,data.dBT4_over_dCICT,\
                                data.dBT5_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans)

            C_xline_s.values[:,0,:,:] = \
                copy_C3(data.dBT3_over_dT,data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,inverse=True)
            if common:
                C_xline_s.values[:,1,:,:] = 1
            else:
                C_xline_s.values[:,1,:,:] = \
                    copy_C3(data.dBT3_over_dCS,data.dBT4_over_dCS,data.dBT5_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True)
                C_xline_s.values[:,2,:,:] = \
                    copy_C3(data.dBT3_over_dCICT,data.dBT4_over_dCICT,\
                                data.dBT5_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True)

            # Now X channel
            C_xchan_s.values[0,:,:,:] = \
                copy_C3(data.dBT3_over_dT,data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,xchan=True)
            if common:
                C_xchan_s.values[1,:,:,:] = 1
            else:
                C_xchan_s.values[1,:,:,:] = \
                    copy_C3(data.dBT3_over_dCS,data.dBT4_over_dCS,data.dBT5_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,xchan=True)
                C_xchan_s.values[2,:,:,:] = \
                    copy_C3(data.dBT3_over_dCICT,data.dBT4_over_dCICT,\
                                data.dBT5_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,xchan=True)

            #
            # Independent effects
            #
            C_xchan_i.values[0,:,:,:] = \
                copy_C3(data.dBT3_over_dT,data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,xchan=True)

        elif not ch3a_version: # Don't have channel 5 but have 3.7

            C_xelem_s.values[:,0,:,:] = \
                copy_C2(data.dBT3_over_dT,data.dBT4_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans)
            if common:
                C_xelem_s.values[:,1,:,:] = 1
            else:
                C_xelem_s.values[:,1,:,:] = \
                    copy_C2(data.dBT3_over_dCS,data.dBT4_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans)
                C_xelem_s.values[:,2,:,:] = \
                    copy_C2(data.dBT3_over_dCICT,data.dBT4_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans)
                
            C_xline_s.values[:,0,:,:] = \
                copy_C2(data.dBT3_over_dT,data.dBT4_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,inverse=True)
            if common:
                C_xline_s.values[:,1,:,:] = 1
            else:
                C_xline_s.values[:,1,:,:] = \
                    copy_C2(data.dBT3_over_dCS,data.dBT4_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True)
                C_xline_s.values[:,2,:,:] = \
                    copy_C2(data.dBT3_over_dCICT,data.dBT4_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True)
            
            # Now X channel
            C_xchan_s.values[0,:,:,:] = \
                copy_C2(data.dBT3_over_dT,data.dBT4_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,xchan=True)
            if common:
                C_xchan_s.values[1,:,:,:] = 1
            else:
                C_xchan_s.values[1,:,:,:] = \
                    copy_C2(data.dBT3_over_dCS,data.dBT4_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,xchan=True)
                C_xchan_s.values[2,:,:,:] = \
                    copy_C2(data.dBT3_over_dCICT,data.dBT4_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,xchan=True)
            
            C_xchan_i.values[0,:,:,:] = \
                copy_C2(data.dBT3_over_dT,data.dBT4_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,xchan=True)

        else:
            # Channel 11 and 12 only (no 3.7 micron channel)
            C_xelem_s.values[:,0,:,:] = \
                copy_C2(data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,ch3a=True)
            if common:
                C_xelem_s.values[:,1,:,:] = 1
            else:
                C_xelem_s.values[:,1,:,:] = \
                    copy_C2(data.dBT4_over_dCS,data.dBT5_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,ch3a=True)
                C_xelem_s.values[:,2,:,:] = \
                    copy_C2(data.dBT4_over_dCICT,data.dBT5_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,ch3a=True)
                
            C_xline_s.values[:,0,:,:] = \
                copy_C2(data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,inverse=True,ch3a=True)
            if common:
                C_xline_s.values[:,1,:,:] = 1
            else:
                C_xline_s.values[:,1,:,:] = \
                    copy_C2(data.dBT4_over_dCS,data.dBT5_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True,ch3a=True)
                C_xline_s.values[:,2,:,:] = \
                    copy_C2(data.dBT4_over_dCICT,data.dBT5_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,inverse=True,ch3a=True)
            
            # Now X channel
            C_xchan_s.values[0,:,:,:] = \
                copy_C2(data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,xchan=True,ch3a=True)
            if common:
                C_xchan_s.values[1,:,:,:] = 1
            else:
                C_xchan_s.values[1,:,:,:] = \
                    copy_C2(data.dBT4_over_dCS,data.dBT5_over_dCS,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,xchan=True,ch3a=True)
                C_xchan_s.values[2,:,:,:] = \
                    copy_C2(data.dBT4_over_dCICT,data.dBT5_over_dCICT,\
                                C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                                chans,xchan=True,ch3a=True)
            
            C_xchan_i.values[0,:,:,:] = \
                copy_C2(data.dBT4_over_dT,data.dBT5_over_dT,\
                            C_xelem_s.coords['n_l'],C_xelem_s.coords['n_e'],\
                            chans,xchan=True,ch3a=True)

    # make mask data (xarray bool)
    # Keep all channels (dtype='?' means boolean)
    mask1 = xarray.DataArray(np.zeros(nchans,dtype='?'),dims=['n_c'])

    # Setup mask for bad lines
    mask2 = xarray.DataArray(np.zeros(len(R_xline_s.coords['n_l']),dtype='?'),\
                                 dims=['n_l'])
    
    #
    # Check for bad scan lines and lines with bad TLs
    #
    scan_qual = bad_scan_quality(data.scan_qual)
    if vis_chans:
        if ch3a_version:
            index = check_bad_data_3(R_xline_s.coords['n_l'].values,\
                                         R_xline_s.coords['n_e'].values,\
                                         scan_qual,\
                                         data.dRe1_over_dCS,\
                                         data.dRe2_over_dCS,\
                                         data.dRe3a_over_dCS)
        else:
            index = check_bad_data_no3(R_xline_s.coords['n_l'].values,\
                                           R_xline_s.coords['n_e'].values,\
                                           scan_qual,\
                                           data.dRe1_over_dCS,\
                                           data.dRe2_over_dCS)
    else:
        if data.ch5_there and not ch3a_version:
            index = check_bad_data_5(R_xline_s.coords['n_l'].values,\
                                         R_xline_s.coords['n_e'].values,\
                                         scan_qual,\
                                         data.dBT3_over_dT,\
                                         data.dBT4_over_dT,\
                                         data.dBT5_over_dT,\
                                         data.dBT3_over_dCS,\
                                         data.dBT4_over_dCS,\
                                         data.dBT5_over_dCS,\
                                         data.dBT3_over_dCICT,\
                                         data.dBT4_over_dCICT,\
                                         data.dBT5_over_dCICT)
        elif not ch3a_version:
            index = check_bad_data_no5(R_xline_s.coords['n_l'].values,\
                                           R_xline_s.coords['n_e'].values,\
                                           scan_qual,\
                                           data.dBT3_over_dT,\
                                           data.dBT4_over_dT,\
                                           data.dBT3_over_dCS,\
                                           data.dBT4_over_dCS,\
                                           data.dBT3_over_dCICT,\
                                           data.dBT4_over_dCICT)
        else:
            index = check_bad_data_no5(R_xline_s.coords['n_l'].values,\
                                           R_xline_s.coords['n_e'].values,\
                                           scan_qual,\
                                           data.dBT4_over_dT,\
                                           data.dBT5_over_dT,\
                                           data.dBT4_over_dCS,\
                                           data.dBT5_over_dCS,\
                                           data.dBT4_over_dCICT,\
                                           data.dBT5_over_dCICT)
    mask2.values[index] = True

    # 
    # Replace TINY numbers with scanline median and
    # Fill masked values with nan's
    # Should be done in the CURUC code but is only done for a subset of
    # arrays (I think). Leads to nan's in outputs
    #
    U_xelem_s_new,U_xline_s_new,U_xchan_i_new,U_xchan_s_new,\
                     C_xelem_s_new,C_xline_s_new,C_xchan_i_new,\
                     C_xchan_s_new = \
                     replace_TINY(U_xelem_s,U_xline_s,U_xchan_i,U_xchan_s,\
                                      C_xelem_s,C_xline_s,C_xchan_i,C_xchan_s,\
                                      mask=mask2.values)
    # Per line
    if not vis_chans and not common:
        for i in range(U_xchan_s.values.shape[0]):
            # Per element
            for j in range(U_xchan_s.values.shape[1]):
                # Per effect
                for k in range(U_xchan_s.values.shape[2]):
                    # Per channel
                    array = np.zeros(4+U_xchan_s.values.shape[3]+\
                                         C_xchan_s.values.shape[3]+\
                                         U_xchan_s_new.values.shape[3]+\
                                         C_xchan_s_new.values.shape[3],\
                                         dtype=np.float32)
                    array[0] = i # scanlines
                    array[1] = j # element
                    array[2] = k # effect
                    if mask2.values[i]:
                        array[3] = 1
                    else:
                        array[3] = 0
                    offset=4
                    array[offset:offset+U_xchan_s.values.shape[3]] = \
                        U_xchan_s.values[i,j,k,:]
                    offset=offset+U_xchan_s.values.shape[3]
                    array[offset:offset+C_xchan_s.values.shape[3]] = \
                        C_xchan_s.values[k,i,j,:]
                    offset=offset+C_xchan_s.values.shape[3]
                    array[offset:offset+U_xchan_s_new.values.shape[3]] = \
                        U_xchan_s_new.values[i,j,k,:]
                    offset=offset+U_xchan_s_new.values.shape[3]
                    array[offset:offset+C_xchan_s_new.values.shape[3]] = \
                        C_xchan_s_new.values[k,i,j,:]
    gd = np.isfinite(U_xelem_s.values) 
    # Now run CURUC
    ny = int(data.ch1.shape[0]/line_skip)
    if 0 == ny:
        ny = 1
    nx = int(data.ch1.shape[1]/elem_skip)
    if 0 == nx:
        nx = 1
    xline_length, xelem_length, xchan_corr_i, xchan_corr_s, xl_all, xe_all = \
        met.apply_curuc(R_xelem_s, R_xline_s, R_xchan_i, R_xchan_s,\
                            U_xelem_s, U_xline_s, \
                            U_xchan_s, U_xchan_i,\
                            C_xelem_s, C_xline_s, \
                            C_xchan_s, C_xchan_i,\
                            coords,mask1,mask2,return_vectors=True,\
                            interpolate_lengths=True,\
                            cutoff_l=ny,cutoff_e=nx)    

    return xline_length, xelem_length, xchan_corr_i, xchan_corr_s, \
        xl_all, xe_all

#
# Get SRF information for a given AVHRR
#
def get_srf(noaa,allchans):

    srf_dir = \
        '/gws/nopw/j04/fiduceo/Users/jmittaz/FCDR/Mike/FCDR_AVHRR/SRF/data/'

    #
    # Remove visible channels as they are not controlled by a FIDUCEO
    # process and therefore we can't know what was used
    #
    gd = (allchans >= 3)
    chans = allchans[gd]

    #
    # Get filenames
    #
    if noaa == 'TIROSN':
        srf_file_wave = srf_dir+'tiros-n_wave.dat'
        srf_file_srf = srf_dir+'tiros-n_srf.dat'
        lut_radiance = srf_dir+'tiros-n_rad.dat'
        lut_bt = srf_dir+'tiros-n_bt.dat'
        inchans = [3,4]
    elif noaa == 'NOAA06':
        srf_file_wave = srf_dir+'noaa06_wave.dat'
        srf_file_srf = srf_dir+'noaa06_srf.dat'
        lut_radiance = srf_dir+'noaa06_rad.dat'
        lut_bt = srf_dir+'noaa06_bt.dat'
        inchans = [3,4]
    elif noaa == 'NOAA07':
        srf_file_wave = srf_dir+'noaa07_wave.dat'
        srf_file_srf = srf_dir+'noaa07_srf.dat'
        lut_radiance = srf_dir+'noaa07_rad.dat'
        lut_bt = srf_dir+'noaa07_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA08':
        srf_file_wave = srf_dir+'noaa08_wave.dat'
        srf_file_srf = srf_dir+'noaa08_srf.dat'
        lut_radiance = srf_dir+'noaa08_rad.dat'
        lut_bt = srf_dir+'noaa08_bt.dat'
        inchans = [3,4]
    elif noaa == 'NOAA09':
        srf_file_wave = srf_dir+'noaa09_wave.dat'
        srf_file_srf = srf_dir+'noaa09_srf.dat'
        lut_radiance = srf_dir+'noaa09_rad.dat'
        lut_bt = srf_dir+'noaa09_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA10':
        srf_file_wave = srf_dir+'noaa10_wave.dat'
        srf_file_srf = srf_dir+'noaa10_srf.dat'
        lut_radiance = srf_dir+'noaa10_rad.dat'
        lut_bt = srf_dir+'noaa10_bt.dat'
        inchans = [3,4]
    elif noaa == 'NOAA11':
        srf_file_wave = srf_dir+'noaa11_wave.dat'
        srf_file_srf = srf_dir+'noaa11_srf.dat'
        lut_radiance = srf_dir+'noaa11_rad.dat'
        lut_bt = srf_dir+'noaa11_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA12':
        srf_file_wave = srf_dir+'noaa12_wave.dat'
        srf_file_srf = srf_dir+'noaa12_srf.dat'
        lut_radiance = srf_dir+'noaa12_rad.dat'
        lut_bt = srf_dir+'noaa12_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA14':
        srf_file_wave = srf_dir+'noaa14_wave.dat'
        srf_file_srf = srf_dir+'noaa14_srf.dat'
        lut_radiance = srf_dir+'noaa14_rad.dat'
        lut_bt = srf_dir+'noaa14_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA15':
        srf_file_wave = srf_dir+'noaa15_wave.dat'
        srf_file_srf = srf_dir+'noaa15_srf.dat'
        lut_radiance = srf_dir+'noaa15_rad.dat'
        lut_bt = srf_dir+'noaa15_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA16':
        srf_file_wave = srf_dir+'noaa16_wave.dat'
        srf_file_srf = srf_dir+'noaa16_srf.dat'
        lut_radiance = srf_dir+'noaa16_rad.dat'
        lut_bt = srf_dir+'noaa16_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA17':
        srf_file_wave = srf_dir+'noaa17_wave.dat'
        srf_file_srf = srf_dir+'noaa17_srf.dat'
        lut_radiance = srf_dir+'noaa17_rad.dat'
        lut_bt = srf_dir+'noaa17_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA18':
        srf_file_wave = srf_dir+'noaa18_wave.dat'
        srf_file_srf = srf_dir+'noaa18_srf.dat'
        lut_radiance = srf_dir+'noaa18_rad.dat'
        lut_bt = srf_dir+'noaa18_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'NOAA19':
        srf_file_wave = srf_dir+'noaa19_wave.dat'
        srf_file_srf = srf_dir+'noaa19_srf.dat'
        lut_radiance = srf_dir+'noaa19_rad.dat'
        lut_bt = srf_dir+'noaa19_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'METOPA':
        srf_file_wave = srf_dir+'metopa_wave.dat'
        srf_file_srf = srf_dir+'metopa_srf.dat'
        lut_radiance = srf_dir+'metopa_rad.dat'
        lut_bt = srf_dir+'metopa_bt.dat'
        inchans = [3,4,5]
    elif noaa == 'METOPB':
        srf_file_wave = srf_dir+'metopb_wave.dat'
        srf_file_srf = srf_dir+'metopb_srf.dat'
        lut_radiance = srf_dir+'metopb_rad.dat'
        lut_bt = srf_dir+'metopb_bt.dat'
        inchans = [3,4,5]
    else:
        raise Exception('Cannot find noaa name for SRF')

    #
    # Read in SRF values themselves
    #    
    wave = np.loadtxt(srf_file_wave)
    srf = np.loadtxt(srf_file_srf)

    #
    # Read in lookup tables
    #
    radiance = np.loadtxt(lut_radiance)
    bt = np.loadtxt(lut_bt)

    #
    # Only select channels that are being used
    #
    start,end = inchans.index(chans[0]),len(chans)

    out_wave = wave[start:end,:]
    out_srf = srf[start:end,:]
    out_radiance = radiance[start:end,:]
    out_radiance = out_radiance.transpose()
    out_bt = bt[start:end,:]
    out_bt = out_bt.transpose()

    # Set 0's in srf to NaN
    gd = (out_wave == 0)
    if np.sum(gd) > 0:
        out_wave[gd] = float('nan')
        out_srf[gd] = float('nan')

    return out_wave,out_srf,out_radiance,out_bt

#
# Write MonteCarlo ensemble output (L1)
#
def write_ensemble(file_out,file_uuid,data,ocean_only=False):

    ch1_mc = np.copy(data.ch1_MC)
    gd = (np.abs(ch1_mc) > 1.0000)
    if np.sum(gd) > 0:
        ch1_mc[gd] = float('nan')
    ch2_mc = np.copy(data.ch2_MC)
    gd = (np.abs(ch2_mc) > 1.0000)
    if np.sum(gd) > 0:
        ch2_mc[gd] = float('nan')
    ch3a_mc = np.copy(data.ch3a_MC)
    gd = (np.abs(ch3a_mc) > 1.0000)
    if np.sum(gd) > 0:
        ch3a_mc[gd] = float('nan')
    ch3_mc = np.copy(data.ch3_MC)
    gd = (np.abs(ch3_mc) > 30.000)
    if np.sum(gd) > 0:
        ch3_mc[gd] = float('nan')
    ch4_mc = np.copy(data.ch4_MC)
    gd = (np.abs(ch4_mc) > 30.000)
    if np.sum(gd) > 0:
        ch4_mc[gd] = float('nan')
    ch5_mc = np.copy(data.ch5_MC)
    gd = (np.abs(ch5_mc) > 30.000)
    if np.sum(gd) > 0:
        ch5_mc[gd] = float('nan')

    #
    # If ocean only then use reduced resolution output to save space
    #
    if ocean_only:

        gd = np.isfinite(ch1_mc)
        if np.abs(ch1_mc[gd]).max()/0.0006 < 127:
            d1 = xarray.DataArray(ch1_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int8',\
                                                    'add_offset':0.,\
                                                    'scale_factor':0.0006,\
                                                    '_FillValue':-128,\
                                                    'valid_min':-127,\
                                                    'valid_max':127,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'reflectance',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        else:
            d1 = xarray.DataArray(ch1_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int16',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-05,\
                                                    '_FillValue':-32768,\
                                                    'valid_min':-10000,\
                                                    'valid_max':10000,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'reflectance',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        gd = np.isfinite(ch2_mc)
        if np.abs(ch2_mc[gd]).max()/0.0006 < 127:
            d2 = xarray.DataArray(ch2_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int8',\
                                                    'add_offset':0.,\
                                                    'scale_factor':0.0006,\
                                                    '_FillValue':-128,\
                                                    'valid_min':-127,\
                                                    'valid_max':127,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'reflectance',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        else:
            d2 = xarray.DataArray(ch2_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int16',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-05,\
                                                    '_FillValue':-32768,\
                                                    'valid_min':-10000,\
                                                    'valid_max':10000,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'reflectance',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        gd = np.isfinite(ch3a_mc)
        if np.abs(ch3a_mc[gd]).max()/0.0006 < 127:
            d3a = xarray.DataArray(ch3a_mc,dims=('nMC','y','x'),\
                                       encoding={'dtype':'int8',\
                                                     'add_offset':0.,\
                                                     'scale_factor':0.0006,\
                                                     '_FillValue':-128,\
                                                     'valid_min':-127,\
                                                     'valid_max':127,\
                                                     'zlib':True,\
                                                     'complevel':9,\
                                                     'shuffle':True},\
                                       attrs={'units':'reflectance',\
                                                  'coordinates':'longitude latitude',\
                                                  'long_name':'MonteCarlo delta from FCDR'}\
                                       )
        else:
            d3a = xarray.DataArray(ch3a_mc,dims=('nMC','y','x'),\
                                       encoding={'dtype':'int16',\
                                                     'add_offset':0.,\
                                                     'scale_factor':1e-05,\
                                                     '_FillValue':-32768,\
                                                     'valid_min':-10000,\
                                                     'valid_max':10000,\
                                                     'zlib':True,\
                                                     'complevel':9,\
                                                     'shuffle':True},\
                                       attrs={'units':'reflectance',\
                                                  'coordinates':'longitude latitude',\
                                                  'long_name':'MonteCarlo delta from FCDR'}\
                                   )
        gd = np.isfinite(ch3_mc)
        if np.abs(ch3_mc[gd]).max()/1e-2 < 127:
            d3 = xarray.DataArray(ch3_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int8',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-02,\
                                                    '_FillValue':-128,\
                                                    'valid_min':-127,\
                                                    'valid_max':127,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'K',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        else:
            d3 = xarray.DataArray(ch3_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int16',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-02,\
                                                    '_FillValue':-32768,\
                                                    'valid_min':-30000,\
                                                    'valid_max':30000,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'K',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        gd = np.isfinite(ch4_mc)
        if np.abs(ch4_mc[gd]).max()/1e-2 < 127:
            d4 = xarray.DataArray(ch4_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int8',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-02,\
                                                    '_FillValue':-128,\
                                                    'valid_min':-127,\
                                                    'valid_max':127,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'K',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        else:
            d4 = xarray.DataArray(ch4_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int16',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-02,\
                                                    '_FillValue':-32768,\
                                                    'valid_min':-30000,\
                                                    'valid_max':30000,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'K',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        gd = np.isfinite(ch5_mc)
        if np.abs(ch4_mc[gd]).max()/1e-2 < 127:
            d5 = xarray.DataArray(ch5_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int8',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-02,\
                                                    '_FillValue':-128,\
                                                    'valid_min':-127,\
                                                    'valid_max':127,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'K',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
        else:
            d5 = xarray.DataArray(ch5_mc,dims=('nMC','y','x'),\
                                      encoding={'dtype':'int16',\
                                                    'add_offset':0.,\
                                                    'scale_factor':1e-02,\
                                                    '_FillValue':-32768,\
                                                    'valid_min':-30000,\
                                                    'valid_max':30000,\
                                                    'zlib':True,\
                                                    'complevel':9,\
                                                    'shuffle':True},\
                                      attrs={'units':'K',\
                                                 'coordinates':'longitude latitude',\
                                                 'long_name':'MonteCarlo delta from FCDR'}\
                                      )
    else:
        d1 = xarray.DataArray(ch1_mc,dims=('nMC','y','x'),\
                                  encoding={'dtype':'int16',\
                                                'add_offset':0.,\
                                                'scale_factor':1e-05,\
                                                '_FillValue':-32768,\
                                                'valid_min':-10000,\
                                                'valid_max':10000,\
                                                'zlib':True,\
                                                'complevel':9,\
                                                'shuffle':True},\
                                  attrs={'units':'reflectance',\
                                             'coordinates':'longitude latitude',\
                                             'long_name':'MonteCarlo delta from FCDR'}\
                                  )
        d2 = xarray.DataArray(ch2_mc,dims=('nMC','y','x'),\
                                  encoding={'dtype':'int16',\
                                                'add_offset':0.,\
                                                'scale_factor':1e-05,\
                                                '_FillValue':-32768,\
                                                'valid_min':-10000,\
                                                'valid_max':10000,\
                                                'zlib':True,\
                                                'complevel':9,\
                                                'shuffle':True},\
                                  attrs={'units':'reflectance',\
                                             'coordinates':'longitude latitude',\
                                             'long_name':'MonteCarlo delta from FCDR'}\
                                  )
        d3a = xarray.DataArray(ch3a_mc,dims=('nMC','y','x'),\
                                   encoding={'dtype':'int16',\
                                                 'add_offset':0.,\
                                                 'scale_factor':1e-05,\
                                                 '_FillValue':-32768,\
                                                 'valid_min':-10000,\
                                                 'valid_max':10000,\
                                                 'zlib':True,\
                                                 'complevel':9,\
                                                 'shuffle':True},\
                                   attrs={'units':'reflectance',\
                                              'coordinates':'longitude latitude',\
                                              'long_name':'MonteCarlo delta from FCDR'}\
                                   )
        d3 = xarray.DataArray(ch3_mc,dims=('nMC','y','x'),\
                                  encoding={'dtype':'int16',\
                                                'add_offset':0.,\
                                                'scale_factor':1e-03,\
                                                '_FillValue':-32768,\
                                                'valid_min':-30000,\
                                                'valid_max':30000,\
                                                'zlib':True,\
                                                'complevel':9,\
                                                'shuffle':True},\
                                  attrs={'units':'K',\
                                             'coordinates':'longitude latitude',\
                                             'long_name':'MonteCarlo delta from FCDR'}\
                                  )
        d4 = xarray.DataArray(ch4_mc,dims=('nMC','y','x'),\
                                  encoding={'dtype':'int16',\
                                                'add_offset':0.,\
                                                'scale_factor':1e-03,\
                                                '_FillValue':-32768,\
                                                'valid_min':-30000,\
                                                'valid_max':30000,\
                                                'zlib':True,\
                                                'complevel':9,\
                                                'shuffle':True},\
                                  attrs={'units':'K',\
                                             'coordinates':'longitude latitude',\
                                             'long_name':'MonteCarlo delta from FCDR'}\
                                  )
        d5 = xarray.DataArray(ch5_mc,dims=('nMC','y','x'),\
                                  encoding={'dtype':'int16',\
                                                'add_offset':0.,\
                                                'scale_factor':1e-03,\
                                                '_FillValue':-32768,\
                                                'valid_min':-30000,\
                                                'valid_max':30000,\
                                                'zlib':True,\
                                                'complevel':9,\
                                                'shuffle':True},\
                                  attrs={'units':'K',\
                                             'coordinates':'longitude latitude',\
                                             'long_name':'MonteCarlo delta from FCDR'}\
                                  )
        
    if ocean_only:
        ds = xarray.Dataset(data_vars={'Ch1_MC':d1,'Ch2_MC':d2,'Ch3a_MC':d3a,\
                                           'Ch3b_MC':d3,'Ch4_MC':d4,'Ch5_MC':d5},\
                                attrs={'Conventions':"CF-1.6",\
                                           'licence':"This dataset is released for use under CC-BY licence (https://creativecommons.org/licenses/by/4.0/) and was developed in the EC FIDUCEO project \"Fidelity and Uncertainty in Climate Data Records from Earth Observations\". Grant Agreement: 638822.",\
                                           'institution':"University of Reading",\
                                           'title':data.version+" version of AVHRR Fundamental Climate Data Record Ensemble",\
                                           'sensor':"AVHRR",\
                                           'platform':data.noaa_string,\
                                           'software_version':data.version,\
                                           'origin_FCDR':file_out,\
                                           'origin_FCDR_UUID':file_uuid,\
                                           'MC_Seed':data.montecarlo_seed,\
                                           'UUID':'{0}'.format(uuid.uuid4()),\
                                           'Ensemble_Type':'Ocean_Only'})
    else:
        ds = xarray.Dataset(data_vars={'Ch1_MC':d1,'Ch2_MC':d2,'Ch3a_MC':d3a,\
                                           'Ch3b_MC':d3,'Ch4_MC':d4,'Ch5_MC':d5},\
                                attrs={'Conventions':"CF-1.6",\
                                           'licence':"This dataset is released for use under CC-BY licence (https://creativecommons.org/licenses/by/4.0/) and was developed in the EC FIDUCEO project \"Fidelity and Uncertainty in Climate Data Records from Earth Observations\". Grant Agreement: 638822.",\
                                           'institution':"University of Reading",\
                                           'title':data.version+" version of AVHRR Fundamental Climate Data Record Ensemble",\
                                           'sensor':"AVHRR",\
                                           'platform':data.noaa_string,\
                                           'software_version':data.version,\
                                           'origin_FCDR':file_out,\
                                           'origin_FCDR_UUID':file_uuid,\
                                           'MC_Seed':data.montecarlo_seed,\
                                           'UUID':'{0}'.format(uuid.uuid4()),\
                                           'Ensemble_Type':'All_Data'})

    file_ensemble = os.path.splitext(file_out)[0]+'_Ensemble.nc'
    ds.to_netcdf(file_ensemble)

def ensemble_orig_netcdf(fileout,file_uuid,data):

    file_ensemble = os.path.splitext(file_out)[0]+'_Ensemble.nc'
    ncid = netCDF4.Dataset(file_ensemble,'w')

    dim_nx = ncid.createDimension('x',size=data.nx)
    dim_ny = ncid.createDimension('y',size=data.ny)
    dim_nmc = ncid.createDimension('nMC',size=data.nmc)

    ch1 = ncid.createVariable('Ch1_MC','i2',('nMC','y','x'),zlib=True,\
                                  complevel=6,shuffle=True,fill_value=-32768)
    ch1.units = "percent"
    ch1.coordinates = "longitude latitude"
    ch1.long_name = "MonteCarlo delta from FCDR"
    ch1.valid_max = 10000
    ch1.valid_min = -10000
    ch1.add_offset = 0.
    ch1.scale_factor = 1.e-05

    ch2 = ncid.createVariable('Ch2_MC','i2',('nMC','y','x'),zlib=True,\
                                  complevel=6,shuffle=True,fill_value=-32768)
    ch2.units = "percent"
    ch2.coordinates = "longitude latitude"
    ch2.long_name = "MonteCarlo delta from FCDR"
    ch2.valid_max = 10000
    ch2.valid_min = -10000
    ch2.add_offset = 0.
    ch2.scale_factor = 1.e-05

    ch3a = ncid.createVariable('Ch3a_MC','i2',('nMC','y','x'),zlib=True,\
                                  complevel=6,shuffle=True,fill_value=-32768)
    ch3a.units = "percent"
    ch3a.coordinates = "longitude latitude"
    ch3a.long_name = "MonteCarlo delta from FCDR"
    ch3a.valid_max = 10000
    ch3a.valid_min = -10000
    ch3a.add_offset = 0.
    ch3a.scale_factor = 1.e-05

    ch3b = ncid.createVariable('Ch3b_MC','i2',('nMC','y','x'),zlib=True,\
                                  complevel=6,shuffle=True,fill_value=-32768)
    ch3b.units = "K"
    ch3b.coordinates = "longitude latitude"
    ch3b.long_name = "MonteCarlo delta from FCDR"
    ch3b.valid_max = 30000
    ch3b.valid_min = -30000
    ch3b.add_offset = 0.
    ch3b.scale_factor = 1.e-03

    ch4 = ncid.createVariable('Ch4_MC','i2',('nMC','y','x'),zlib=True,\
                                  complevel=6,shuffle=True,fill_value=-32768)
    ch4.units = "K"
    ch4.coordinates = "longitude latitude"
    ch4.long_name = "MonteCarlo delta from FCDR"
    ch4.valid_max = 30000
    ch4.valid_min = -30000
    ch4.add_offset = 0.
    ch4.scale_factor = 1.e-03

    ch5 = ncid.createVariable('Ch5_MC','i2',('nMC','y','x'),zlib=True,\
                                  complevel=6,shuffle=True,fill_value=-32768)
    ch5.units = "K"
    ch5.coordinates = "longitude latitude"
    ch5.long_name = "MonteCarlo delta from FCDR"
    ch5.valid_max = 30000
    ch5.valid_min = -30000
    ch5.add_offset = 0.
    ch5.scale_factor = 1.e-03

    ch1[:,:,:] = ch1_mc
    ch2[:,:,:] = ch2_mc
    ch3a[:,:,:] = ch3a_mc
    ch3b[:,:,:] = ch3_mc
    ch4[:,:,:] = ch4_mc
    ch5[:,:,:] = ch5_mc

    ncid.Conventions = "CF-1.6"
    ncid.licence = "This dataset is released for use under CC-BY licence (https://creativecommons.org/licenses/by/4.0/) and was developed in the EC FIDUCEO project \"Fidelity and Uncertainty in Climate Data Records from Earth Observations\". Grant Agreement: 638822."
    ncid.institution = "University of Reading"
    ncid.title = data.version+" version of AVHRR Fundamental Climate Data Record Ensemble"
    ncid.sensor = "AVHRR"
    ncid.platform = data.noaa_string
    ncid.software_version = data.version
    ncid.origin_FCDR = file_out
    ncid.origin_FCDR_UUID = file_uuid
    ncid.MC_Seed = data.montecarlo_seed
    # UUID for MC file
    ncid.UUID = '{0}'.format(uuid.uuid4())
    
    Ncid.close()

#
# Calculate CURUC etc. and output file. Note changes behaviour
# dependent on channel set
#
def main_outfile(data,ch3a_version,fileout='None',split=False,gbcs_l1c=False,\
                     ocean_only=False):

    # Run CURUC to get CURUC values (lenths, vectors and chan cross 
    # correlations)
    if data.noaa_string in ['NOAA06','NOAA08','NOAA10']:
        # Setup CURUC for 2 channel IR AVHRR
        chans = np.array([0,1,3,4],dtype=np.int8)
    elif data.noaa_string in ['NOAA07','NOAA09','NOAA11','NOAA12','NOAA14']:
        # Setup CURUC for 3 channel IR AVHRR
        chans = np.array([0,1,3,4,5],dtype=np.int8)
    elif data.noaa_string in ['NOAA15','NOAA16','NOAA17','NOAA18',\
                                  'NOAA19','METOPA','METOPB','METOPC']:
        # Setup CURUC for 2 or 3 channel IR AVHRR dependnet on ch3a
        if ch3a_version:
            chans = np.array([0,1,2,4,5],dtype=np.int8)
        else:
            chans = np.array([0,1,3,4,5],dtype=np.int8)
    else:
        raise Exception('noaa_string not found')
    inchans = np.sort(chans)
    #
    # Make two sets of chans - one visible, one IR
    #
    gd = (inchans <= 2)
    vis_chans = inchans[gd]
    gd = (inchans >= 3)
    ir_chans = inchans[gd]
    #
    # Run CURUC for vis chans only
    #
    vis_xline_length, vis_xelem_length, vis_xchan_corr_i, \
        vis_xchan_corr_s, vis_xl_all, vis_xe_all = \
        run_CURUC(data,vis_chans,vis_chans=True,common=False,\
                      line_skip=5,elem_skip=25,ch3a_version=ch3a_version)
    #
    # Run CURUC for IR chans only - not common
    #
    ir_xline_length, ir_xelem_length, ir_xchan_corr_i, \
        ir_xchan_corr_s, ir_xl_all, ir_xe_all = \
        run_CURUC(data,ir_chans,vis_chans=False,common=False,\
                      line_skip=5,elem_skip=25,ch3a_version=ch3a_version)
    #
    # Run CURUC for IR chans only - common effects
    #
    com_xline_length, com_xelem_length, com_xchan_corr_i, \
        com_xchan_corr_s, com_xl_all, com_xe_all = \
        run_CURUC(data,ir_chans,vis_chans=False,common=True,\
                      line_skip=5,elem_skip=25,ch3a_version=ch3a_version)

    xline_length = np.copy(vis_xline_length.values)
    xline_length = np.append(xline_length,ir_xline_length.values,axis=0)

    xelem_length = np.copy(vis_xelem_length.values)
    xelem_length = np.append(xelem_length,ir_xelem_length.values,axis=0)

    xl_all = np.copy(vis_xl_all.values)
    xl_all = np.append(xl_all,ir_xl_all.values,axis=1)

    xe_all = np.copy(vis_xe_all.values)
    xe_all = np.append(xe_all,ir_xe_all.values,axis=1)

    length = np.zeros(xl_all.shape[1],dtype=np.int16)
    for i in range(xl_all.shape[0]):
        for j in range(xl_all.shape[1]):
            if xl_all[i,j] > 0:
                length[j] = i

    max_len = length.max()
    corr_l = xl_all[0:max_len+2,:]

    # Get SRF and lookup tables
    srf_x,srf_y,lut_rad,lut_bt = get_srf(data.noaa_string,chans)

# MT: 09-11-2017: define sensor specific channel_correlation_matrix (ccm)
# JM: Now merge separate CURUC runs (vis, IR structured, IR common)
    noch3a=False
    noch5=False
    if data.noaa_string in ['NOAA06','NOAA08','NOAA10']:
        # Run CURUC for 2 channel IR AVHRR
        inS_s = np.array([[ir_xchan_corr_s.values[0,0],\
                             ir_xchan_corr_s.values[0,1]],\
                            [ir_xchan_corr_s.values[1,0],\
                                 ir_xchan_corr_s.values[1,1]]])
        # Run CURUC for 2 channel IR AVHRR
        inS_c = np.array([[com_xchan_corr_s.values[0,0],\
                             com_xchan_corr_s.values[0,1]],\
                            [com_xchan_corr_s.values[1,0],\
                                 com_xchan_corr_s.values[1,1]]])
        inS_i = np.array([[1.,0.,],[0.,1.]])
        start=3
        stop=5
        noch3a=True
        noch5=True
    elif data.noaa_string in ['NOAA07','NOAA09','NOAA11','NOAA12','NOAA14']:
        inS_s = np.array([[ir_xchan_corr_s.values[0,0],\
                             ir_xchan_corr_s.values[0,1],\
                             ir_xchan_corr_s.values[0,2]],\
                            [ir_xchan_corr_s.values[1,0],\
                                 ir_xchan_corr_s.values[1,1],\
                                 ir_xchan_corr_s.values[1,2]],\
                            [ir_xchan_corr_s.values[2,0],\
                                 ir_xchan_corr_s.values[2,1],\
                                 ir_xchan_corr_s.values[2,2]]])
        inS_c = np.array([[com_xchan_corr_s.values[0,0],\
                             com_xchan_corr_s.values[0,1],\
                             com_xchan_corr_s.values[0,2]],\
                            [com_xchan_corr_s.values[1,0],\
                                 com_xchan_corr_s.values[1,1],\
                                 com_xchan_corr_s.values[1,2]],\
                            [com_xchan_corr_s.values[2,0],\
                                 com_xchan_corr_s.values[2,1],\
                                 com_xchan_corr_s.values[2,2]]])
        inS_i = np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        start=3
        stop=6
        noch3a=True
    elif data.noaa_string in ['NOAA15','NOAA16','NOAA17','NOAA18','NOAA19','METOPA','METOPB','METOPC']:
        if not ch3a_version:
            inS_i = np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
            inS_s = np.array([[ir_xchan_corr_s.values[0,0],\
                               ir_xchan_corr_s.values[0,1],\
                               ir_xchan_corr_s.values[0,2]],\
                              [ir_xchan_corr_s.values[1,0],\
                               ir_xchan_corr_s.values[1,1],\
                               ir_xchan_corr_s.values[1,2]],\
                              [ir_xchan_corr_s.values[2,0],\
                               ir_xchan_corr_s.values[2,1],\
                               ir_xchan_corr_s.values[2,2]]])
            inS_c = np.array([[com_xchan_corr_s.values[0,0],\
                               com_xchan_corr_s.values[0,1],\
                               com_xchan_corr_s.values[0,2]],\
                              [com_xchan_corr_s.values[1,0],\
                               com_xchan_corr_s.values[1,1],\
                               com_xchan_corr_s.values[1,2]],\
                              [com_xchan_corr_s.values[2,0],\
                               com_xchan_corr_s.values[2,1],\
                               com_xchan_corr_s.values[2,2]]])
        else:
            inS_i = np.array([[0.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
            inS_s = np.array([[0,0,0],\
                                [0,ir_xchan_corr_s.values[0,0],\
                                     ir_xchan_corr_s.values[0,1]],\
                                [0,ir_xchan_corr_s.values[1,0],\
                                     ir_xchan_corr_s.values[1,1]]])
            inS_c = np.array([[0,0,0],\
                                [0,com_xchan_corr_s.values[0,0],\
                                     com_xchan_corr_s.values[0,1]],\
                                [0,com_xchan_corr_s.values[1,0],\
                                     com_xchan_corr_s.values[1,1]]])
        start=3
        stop=6

    S_c = np.identity(6)
    S_s = np.identity(6)
    S_i = np.identity(6)
    if noch3a:
        S_c[2,2]=0.
        S_s[2,2]=0.
        S_i[2,2]=0.
    if noch5:
        S_c[5,5]=0.
        S_s[5,5]=0.
        S_i[5,5]=0.
    S_c[start:stop,start:stop] = inS_c
    S_s[start:stop,start:stop] = inS_s
    S_i[start:stop,start:stop] = inS_i

    # Either write L1C with chan covariance or FIDUCEO easy FCDR
    if gbcs_l1c:
        l1c.write_gbcs_l1c(fileout,data,S_s)
    else:
        writer = FCDRWriter()

        # get a template for sensor name in EASY format, supply product height
        # The scan-width is set automatically
        # Update now gives srf_size for SRF
        #                  corr_dx for correlation vector for elements
        #                  corr_dy for correlation vector scanline direction
        #                  lut_size for radiance conversion to BT lokkup table
        dataset = writer.createTemplateEasy("AVHRR", data.ny, \
                                                srf_size=srf_x.shape[1],\
                                                corr_dx=data.lat.shape[1],\
                                                corr_dy=len(corr_l),\
                                                lut_size=lut_rad.shape[0])

        # set some mandatory global attributes. Writing will fail if not all of them are filled
        dataset.attrs["institution"] = "University of Reading"
        dataset.attrs["title"] = data.version+" version of AVHRR Fundamental Climate Data Records"
        dataset.attrs["source"] = data.sources
        dataset.attrs["history"] = ""
        dataset.attrs["references"] = "CDF_FCDR_File Spec"
        dataset.attrs["comment"] = "This version is a "+data.version+" one and does not contain the final complete uncertainty model though many error effects have been included."
        dataset.attrs['sensor'] = "AVHRR"
        dataset.attrs['platform'] = data.noaa_string
        dataset.attrs['software_version'] = data.version
        if split:
            dataset.attrs['Ch3a_Ch3b_split_file'] = 'TRUE'
        else:
            dataset.attrs['Ch3a_Ch3b_split_file'] = 'FALSE'
        if ch3a_version:
            dataset.attrs['Ch3a_only'] = 'TRUE'
            dataset.attrs['Ch3b_only'] = 'FALSE'
        else:
            dataset.attrs['Ch3a_only'] = 'FALSE'
            dataset.attrs['Ch3b_only'] = 'TRUE'
        file_uuid = '{0}'.format(uuid.uuid4())
        dataset.attrs['UUID'] = file_uuid

        # write real data to the variables. All variables initially contain "_FillValue".
        # Not writing to the whole array is completely OK

        dataset.variables["latitude"].data = data.lat
        dataset.variables["longitude"].data = data.lon
        dataset.variables["Time"].data = data.time
        dataset.variables["satellite_zenith_angle"].data = data.satza
        dataset.variables["solar_zenith_angle"].data = data.solza
        dataset.variables["relative_azimuth_angle"].data = data.relaz
        dataset.variables["Ch1"].data = data.ch1
        dataset.variables["Ch2"].data = data.ch2
        if data.ch3a_there:
            dataset.variables["Ch3a"].data = data.ch3a
        dataset.variables["Ch3b"].data = data.ch3b
        dataset.variables["Ch4"].data = data.ch4
        if data.ch5_there:
            dataset.variables["Ch5"].data = data.ch5
# MT: 30-10-2017: uncertainty variable name change in line with FCDR-CDR file format spec fv1.1.1
        dataset.variables["u_independent_Ch1"].data = data.u_random_ch1
        dataset.variables["u_independent_Ch2"].data = data.u_random_ch2
        if data.ch3a_there:
            dataset.variables["u_independent_Ch3a"].data = data.u_random_ch3a
        dataset.variables["u_independent_Ch3b"].data = data.u_random_ch3b
        dataset.variables["u_independent_Ch4"].data = data.u_random_ch4
        if data.ch5_there:
            dataset.variables["u_independent_Ch5"].data = data.u_random_ch5   
        dataset.variables["u_structured_Ch1"].data = data.u_non_random_ch1
        dataset.variables["u_structured_Ch2"].data = data.u_non_random_ch2
        if data.ch3a_there:
            dataset.variables["u_structured_Ch3a"].data = data.u_non_random_ch3a
        dataset.variables["u_structured_Ch3b"].data = data.u_non_random_ch3b
        dataset.variables["u_structured_Ch4"].data = data.u_non_random_ch4
        if data.ch5_there:
            dataset.variables["u_structured_Ch5"].data = data.u_non_random_ch5
        dataset.variables["u_common_Ch1"].data = data.u_common_ch1
        dataset.variables["u_common_Ch2"].data = data.u_common_ch2
        if data.ch3a_there:
            dataset.variables["u_common_Ch3a"].data = data.u_common_ch3a
        dataset.variables["u_common_Ch3b"].data = data.u_common_ch3b
        dataset.variables["u_common_Ch4"].data = data.u_common_ch4
        if data.ch5_there:
            dataset.variables["u_common_Ch5"].data = data.u_common_ch5
# MT: 18-10-2017: added quality flag fields
        dataset.variables["quality_scanline_bitmask"].data = data.scan_qual
        dataset.variables["quality_channel_bitmask"].data = data.chan_qual

# Update for reader version 1.1.5 and now version 2.1
        dataset.variables["channel_correlation_matrix_common"].data = S_c
        dataset.variables["channel_correlation_matrix_structured"].data = S_s
        dataset.variables["channel_correlation_matrix_independent"].data = S_i
        elem_corr = np.zeros((data.lat.shape[1],stop-start))
        elem_corr[:,:] = 1.
        dataset.variables["cross_element_correlation_coefficients"].\
            data[:,start:stop] = elem_corr
        dataset.variables["cross_line_correlation_coefficients"].\
            data[0:corr_l.shape[0],0] = corr_l[:,0]
        dataset.variables["cross_line_correlation_coefficients"].\
            data[0:corr_l.shape[0],1] = corr_l[:,1]
        if data.ch3a_there:
            dataset.variables["cross_line_correlation_coefficients"].\
                data[0:corr_l.shape[0],2] = corr_l[:,2]
            dataset.variables["cross_line_correlation_coefficients"].\
                data[0:corr_l.shape[0],4] = corr_l[:,3]
            dataset.variables["cross_line_correlation_coefficients"].\
                data[0:corr_l.shape[0],5] = corr_l[:,4]
        else:
            dataset.variables["cross_line_correlation_coefficients"].\
                data[0:corr_l.shape[0],3] = corr_l[:,2]
            dataset.variables["cross_line_correlation_coefficients"].\
                data[0:corr_l.shape[0],4] = corr_l[:,3]
            if data.ch5_there:
                dataset.variables["cross_line_correlation_coefficients"].\
                    data[0:corr_l.shape[0],5] = corr_l[:,4]
        
# JM: 05/07/2018: Added in SRF data and rad->BT etc. lookup tables
        dataset.variables["SRF_weights"].data[start:stop,:] = srf_y
        dataset.variables["SRF_wavelengths"].data[start:stop,:] = srf_x
        dataset.variables["lookup_table_BT"].data[:,start:stop] = lut_bt
        dataset.variables["lookup_table_radiance"].data[:,start:stop] = lut_rad

        # Traceability back to original Level 1B file and scanline
        dataset.variables["scanline_map_to_origl1bfile"].data[:] = \
            data.orig_scanline
        dataset.variables["scanline_origl1b"].data[:] = data.scanline

        # dump it to disk, netcdf4, medium compression
        # writing will fail when the target file already exists
        if 'None' == fileout:
            # Change noaa_string to something that includes the possibility
            # of a split file
            if split:
                if ch3a_version:
                    ch_string='C3A'
                else:
                    ch_string='C3B'
            else:
                ch_string='ALL'
            if data.noaa_string == 'TIROSN':
                noaa_string='TRN'+ch_string
            elif data.noaa_string == 'NOAA06':
                noaa_string='N06'+ch_string
            elif data.noaa_string == 'NOAA07':
                noaa_string='N07'+ch_string
            elif data.noaa_string == 'NOAA08':
                noaa_string='N08'+ch_string
            elif data.noaa_string == 'NOAA09':
                noaa_string='N09'+ch_string
            elif data.noaa_string == 'NOAA10':
                noaa_string='N10'+ch_string
            elif data.noaa_string == 'NOAA11':
                noaa_string='N11'+ch_string
            elif data.noaa_string == 'NOAA12':
                noaa_string='N12'+ch_string
            elif data.noaa_string == 'NOAA14':
                noaa_string='N14'+ch_string
            elif data.noaa_string == 'NOAA15':
                noaa_string='N15'+ch_string
            elif data.noaa_string == 'NOAA16':
                noaa_string='N16'+ch_string
            elif data.noaa_string == 'NOAA17':
                noaa_string='N17'+ch_string
            elif data.noaa_string == 'NOAA18':
                noaa_string='N18'+ch_string
            elif data.noaa_string == 'NOAA19':
                noaa_string='N19'+ch_string
            elif data.noaa_string == 'METOPA':
                noaa_string='MTA'+ch_string
            elif data.noaa_string == 'METOPB':
                noaa_string='MTB'+ch_string
            else:
                print(data.noaa_string)
                raise Exception('Cannot match data.noaa_string')
            file_out = writer.create_file_name_FCDR_easy('AVHRR',noaa_string,\
                                                             data.date_time[0],\
                                                             data.date_time[-1],\
                                                             data.version)
            #
            # If montecarlo then output this file as well
            #
            if data.montecarlo:
                write_ensemble(file_out,file_uuid,data,ocean_only=ocean_only)

        else:
            if split:
                if ch3a_version:
                    file_out = 'ch3a_'+fileout
                else:
                    file_out = 'ch3b_'+fileout
            else:
                file_out = fileout
        writer.write(dataset, file_out)

#
# Copy data into data class based on filter
#
class copy_to_data(object):

    def copy(self,data,gd):
        self.nx = data.nx
        self.ny = np.sum(gd)
        self.ch3a_there = data.ch3a_there
        self.ch5_there = data.ch5_there
        self.lat = data.lat[gd,:]
        self.lon = data.lon[gd,:]
        self.time = data.time[gd]
        self.date_time=[]
        for i in range(len(gd)):
            if gd[i]:
                self.date_time.append(data.date_time[i])
        self.satza = data.satza[gd,:]
        self.solza = data.solza[gd,:]
        self.relaz = data.relaz[gd,:]
        self.ch1 = data.ch1[gd,:]
        self.ch2 = data.ch2[gd,:]
        if self.ch3a_there:
            self.ch3a = data.ch3a[gd,:]
        self.ch3b = data.ch3b[gd,:]
        self.ch4 = data.ch4[gd,:]
        if self.ch5_there:
            self.ch5 = data.ch5[gd,:]
        self.u_random_ch1 = data.u_random_ch1[gd,:]
        self.u_random_ch2 = data.u_random_ch2[gd,:]
        if self.ch3a_there:
            self.u_random_ch3a = data.u_random_ch3a[gd,:]
        self.u_random_ch3b = data.u_random_ch3b[gd,:]
        self.u_random_ch4 = data.u_random_ch4[gd,:]
        if self.ch5_there:
            self.u_random_ch5 = data.u_random_ch5[gd,:]
        self.u_non_random_ch1 = data.u_non_random_ch1[gd,:]
        self.u_non_random_ch2 = data.u_non_random_ch2[gd,:]
        if self.ch3a_there:
            self.u_non_random_ch3a = data.u_non_random_ch3a[gd,:]
        self.u_non_random_ch3b = data.u_non_random_ch3b[gd,:]
        self.u_non_random_ch4 = data.u_non_random_ch4[gd,:]
        if self.ch5_there:
            self.u_non_random_ch5 = data.u_non_random_ch5[gd,:]
        self.u_common_ch1 = data.u_common_ch1[gd,:]
        self.u_common_ch2 = data.u_common_ch2[gd,:]
        if self.ch3a_there:
            self.u_common_ch3a = data.u_common_ch3a[gd,:]
        self.u_common_ch3b = data.u_common_ch3b[gd,:]
        self.u_common_ch4 = data.u_common_ch4[gd,:]
        if self.ch5_there:
            self.u_common_ch5 = data.u_common_ch5[gd,:]
        self.scan_qual = data.scan_qual[gd]
        self.chan_qual = data.chan_qual[gd,:]
        self.dRe1_over_dCS = data.dRe1_over_dCS[gd,:]
        self.dRe2_over_dCS = data.dRe2_over_dCS[gd,:]
        self.dRe3a_over_dCS = data.dRe3a_over_dCS[gd,:]
        self.dBT3_over_dT = data.dBT3_over_dT[gd,:]
        self.dBT4_over_dT = data.dBT4_over_dT[gd,:]
        self.dBT5_over_dT = data.dBT5_over_dT[gd,:]
        self.dBT3_over_dCS = data.dBT3_over_dCS[gd,:]
        self.dBT4_over_dCS = data.dBT4_over_dCS[gd,:]
        self.dBT5_over_dCS = data.dBT5_over_dCS[gd,:]
        self.dBT3_over_dCICT = data.dBT3_over_dCICT[gd,:]
        self.dBT4_over_dCICT = data.dBT4_over_dCICT[gd,:]
        self.dBT5_over_dCICT = data.dBT5_over_dCICT[gd,:]
        self.scanline = data.scanline[gd]
        self.orig_scanline = data.orig_scanline[gd]
        self.badNav = data.badNav[gd]
        self.badCal = data.badCal[gd]
        self.badTime = data.badTime[gd]
        self.missingLines = data.missingLines[gd]
        self.solar3 = data.solar3[gd]
        self.solar4 = data.solar4[gd]
        self.solar5 = data.solar5[gd]

        self.ch3b_harm = data.ch3b_harm[gd,:]
        self.ch4_harm = data.ch4_harm[gd,:]
        self.ch5_harm = data.ch5_harm[gd,:]

        self.orbital_temperature = data.orbital_temperature
        self.cal_cnts_noise = data.cal_cnts_noise[:]
        self.cnts_noise = data.cnts_noise[:]
        self.spatial_correlation_scale = data.spatial_correlation_scale
        self.ICT_Temperature_Uncertainty = data.ICT_Temperature_Uncertainty
        self.PRT_Uncertainty = data.PRT_Uncertainty
        self.noaa_string = data.noaa_string
        self.sources = data.sources
        self.version = data.version

        self.montecarlo = data.montecarlo
        if data.montecarlo:
            self.montecarlo_seed = data.montecarlo_seed
            self.ch1_MC = data.ch1_MC[:,gd,:]
            self.ch2_MC = data.ch2_MC[:,gd,:]
            self.ch3a_MC = data.ch3a_MC[:,gd,:]
            self.ch3_MC = data.ch3_MC[:,gd,:]
            self.ch4_MC = data.ch4_MC[:,gd,:]
            self.ch5_MC = data.ch5_MC[:,gd,:]
            self.nmc = self.ch1_MC.shape[0]

    def __init__(self,data,gd):

        self.copy(data,gd)

#
# Mask data into data class based on filter
#
class mask_data(object):

    def mask(self,data,gd):
        self.nx = np.copy(data.nx)
        self.ny = np.copy(data.ny)
        self.ch3a_there = np.copy(data.ch3a_there)
        self.ch5_there = np.copy(data.ch5_there)
        self.lat = np.copy(data.lat[:,:])
        self.lon = np.copy(data.lon[:,:])
        self.time = np.copy(data.time[:])
        self.date_time=[]
        for i in range(len(gd)):
            self.date_time.append(data.date_time[i])
        self.satza = np.copy(data.satza[:,:])
        self.satza[gd,:] = float('nan')
        self.solza = np.copy(data.solza[:,:])
        self.solza[gd,:] = float('nan')
        self.relaz = np.copy(data.relaz[:,:])
        self.relaz[gd,:] = float('nan')
        self.ch1 = np.copy(data.ch1[:,:])
        self.ch1[gd,:] = float('nan')
        self.ch2 = np.copy(data.ch2[:,:])
        self.ch2[gd,:] = float('nan')
        if self.ch3a_there:
            self.ch3a = np.copy(data.ch3a[:,:])
            self.ch3a[gd,:] = float('nan')
        self.ch3b = np.copy(data.ch3b[:,:])
        self.ch3b[gd,:] = float('nan')
        self.ch4 = np.copy(data.ch4[:,:])
        self.ch4[gd,:] = float('nan')
        if self.ch5_there:
            self.ch5 = np.copy(data.ch5[:,:])
            self.ch5[gd,:] = float('nan')
        self.u_random_ch1 = np.copy(data.u_random_ch1[:,:])
        self.u_random_ch1[gd,:] = float('nan')
        self.u_random_ch2 = np.copy(data.u_random_ch2[:,:])
        self.u_random_ch2[gd,:] = float('nan')
        if self.ch3a_there:
            self.u_random_ch3a = np.copy(data.u_random_ch3a[:,:])
            self.u_random_ch3a[gd,:] = float('nan')
        self.u_random_ch3b = np.copy(data.u_random_ch3b[:,:])
        self.u_random_ch3b[gd,:] = float('nan')
        self.u_random_ch4 = np.copy(data.u_random_ch4[:,:])
        self.u_random_ch4[gd,:] = float('nan')
        if self.ch5_there:
            self.u_random_ch5 = np.copy(data.u_random_ch5[:,:])
            self.u_random_ch5[gd,:] = float('nan')
        self.u_non_random_ch1 = np.copy(data.u_non_random_ch1[:,:])
        self.u_non_random_ch1[gd,:] = float('nan')
        self.u_non_random_ch2 = np.copy(data.u_non_random_ch2[:,:])
        self.u_non_random_ch2[gd,:] = float('nan')
        if self.ch3a_there:
            self.u_non_random_ch3a = np.copy(data.u_non_random_ch3a[:,:])
            self.u_non_random_ch3a[gd,:] = float('nan')
        self.u_non_random_ch3b = np.copy(data.u_non_random_ch3b[:,:])
        self.u_non_random_ch3b[gd,:] = float('nan')
        self.u_non_random_ch4 = np.copy(data.u_non_random_ch4[:,:])
        self.u_non_random_ch4[gd,:] = float('nan')
        if self.ch5_there:
            self.u_non_random_ch5 = np.copy(data.u_non_random_ch5[:,:])
            self.u_non_random_ch5[gd,:] = float('nan')
        self.u_common_ch1 = np.copy(data.u_common_ch1[:,:])
        self.u_common_ch1[gd,:] = float('nan')
        self.u_common_ch2 = np.copy(data.u_common_ch2[:,:])
        self.u_common_ch2[gd,:] = float('nan')
        if self.ch3a_there:
            self.u_common_ch3a = np.copy(data.u_common_ch3a[:,:])
            self.u_common_ch3a[gd,:] = float('nan')
        self.u_common_ch3b = np.copy(data.u_common_ch3b[:,:])
        self.u_common_ch3b[gd,:] = float('nan')
        self.u_common_ch4 = np.copy(data.u_common_ch4[:,:])
        self.u_common_ch4[gd,:] = float('nan')
        if self.ch5_there:
            self.u_common_ch5 = np.copy(data.u_common_ch5[:,:])
            self.u_common_ch5[gd,:] = float('nan')
        #
        # set quality to bad
        #
        self.scan_qual = np.copy(data.scan_qual[:])
        self.scan_qual[gd] = 1
        self.chan_qual = np.copy(data.chan_qual[:,:])
        self.chan_qual[gd,:] = 1
        self.dRe1_over_dCS = np.copy(data.dRe1_over_dCS[:,:])
        self.dRe1_over_dCS[gd,:] = float('nan')
        self.dRe2_over_dCS = np.copy(data.dRe2_over_dCS[:,:])
        self.dRe2_over_dCS[gd,:] = float('nan')
        self.dRe3a_over_dCS = np.copy(data.dRe3a_over_dCS[:,:])
        self.dRe3a_over_dCS[gd,:] = float('nan')
        self.dBT3_over_dT = np.copy(data.dBT3_over_dT[:,:])
        self.dBT3_over_dT[gd,:] = float('nan')
        self.dBT4_over_dT = np.copy(data.dBT4_over_dT[:,:])
        self.dBT4_over_dT[gd,:] = float('nan')
        self.dBT5_over_dT = np.copy(data.dBT5_over_dT[:,:])
        self.dBT5_over_dT[gd,:] = float('nan')
        self.dBT3_over_dCS = np.copy(data.dBT3_over_dCS[:,:])
        self.dBT3_over_dCS[gd,:] = float('nan')
        self.dBT4_over_dCS = np.copy(data.dBT4_over_dCS[:,:])
        self.dBT4_over_dCS[gd,:] = float('nan')
        self.dBT5_over_dCS = np.copy(data.dBT5_over_dCS[:,:])
        self.dBT5_over_dCS[gd,:] = float('nan')
        self.dBT3_over_dCICT = np.copy(data.dBT3_over_dCICT[:,:])
        self.dBT3_over_dCICT[gd,:] = float('nan')
        self.dBT4_over_dCICT = np.copy(data.dBT4_over_dCICT[:,:])
        self.dBT4_over_dCICT[gd,:] = float('nan')
        self.dBT5_over_dCICT = np.copy(data.dBT5_over_dCICT[:,:])
        self.dBT5_over_dCICT[gd,:] = float('nan')
        self.scanline = np.copy(data.scanline[:])
        self.scanline[gd] = 255
        self.orig_scanline = np.copy(data.orig_scanline[:])
        self.orig_scanline[gd] = -32767
        self.badNav = np.copy(data.badNav[:])
        self.badNav[gd] = 0
        self.badCal = np.copy(data.badCal[:])
        self.badCal[gd] = 0
        self.badTime = np.copy(data.badTime[:])
        self.badTime[gd] = 0
        self.missingLines = np.copy(data.missingLines[:])
        self.missingLines[gd] = 1
        self.solar3 = np.copy(data.solar3[:])
        self.solar3[gd] = 0
        self.solar4 = np.copy(data.solar4[:])
        self.solar4[gd] = 0
        self.solar5 = np.copy(data.solar5[:])
        self.solar5[gd] = 0

        self.ch3b_harm = np.copy(data.ch3b_harm[:,:])
        self.ch3b_harm[gd,:] = float('nan')
        self.ch4_harm = np.copy(data.ch4_harm[:,:])
        self.ch4_harm[gd,:] = float('nan')
        self.ch5_harm = np.copy(data.ch5_harm[:,:])
        self.ch5_harm[gd,:] = float('nan')

        self.orbital_temperature = np.copy(data.orbital_temperature)
        self.cal_cnts_noise = np.copy(data.cal_cnts_noise[:])
        self.cnts_noise = np.copy(data.cnts_noise[:])
        self.spatial_correlation_scale = np.copy(data.spatial_correlation_scale)
        self.ICT_Temperature_Uncertainty = np.copy(data.ICT_Temperature_Uncertainty)
        self.PRT_Uncertainty = np.copy(data.PRT_Uncertainty)
        self.noaa_string = data.noaa_string
        self.sources = data.sources
        self.version = data.version
 
        self.montecarlo = data.montecarlo
        if data.montecarlo:
            self.montecarlo_seed = data.montecarlo_seed
            self.ch1_MC = np.copy(data.ch1_MC)
            self.ch1_MC[:,gd,:] = float('nan')
            self.ch2_MC = np.copy(data.ch2_MC)
            self.ch2_MC[:,gd,:] = float('nan')
            self.ch3a_MC = np.copy(data.ch3a_MC)
            self.ch3a_MC[:,gd,:] = float('nan')
            self.ch3_MC = np.copy(data.ch3_MC)
            self.ch3_MC[:,gd,:] = float('nan')
            self.ch4_MC = np.copy(data.ch4_MC)
            self.ch4_MC[:,gd,:] = float('nan')
            self.ch5_MC = np.copy(data.ch5_MC)
            self.ch5_MC[:,gd,:] = float('nan')
            self.nmc = self.ch1_MC.shape[0]
        #
        # Top and Tail data if needed - using scan_qual flag
        # Original start/end time already filtered to have good data only
        #
        ok=False
        ggd = np.zeros(len(gd),dtype=np.bool)
        ggd[:] = True
        for i in range(len(self.scan_qual)):
            if 1 == self.scan_qual[i] or self.time[i] < 0 or \
                    ~np.isfinite(self.time[i]):
                ggd[i] = False
                ok=True
            else:
                break
        for i in range(len(self.scan_qual)-1,0,-1):
            if 1 == self.scan_qual[i] or self.time[i] < 0 or \
                    ~np.isfinite(self.time[i]):
                ggd[i] = False
                ok=True
            else:
                break

        if ok:
            self.nx = data.nx
            self.ny = np.sum(ggd)
            self.lat = self.lat[ggd,:]
            self.lon = self.lon[ggd,:]
            self.time = self.time[ggd]
            date_time=[]
            for i in range(len(ggd)):
                if ggd[i]:
                    date_time.append(self.date_time[i])
            self.date_time = date_time[:]
            self.satza = self.satza[ggd,:]
            self.solza = self.solza[ggd,:]
            self.relaz = self.relaz[ggd,:]
            self.ch1 = self.ch1[ggd,:]
            self.ch2 = self.ch2[ggd,:]
            if self.ch3a_there:
                self.ch3a = self.ch3a[ggd,:]
            self.ch3b = self.ch3b[ggd,:]
            self.ch4 = self.ch4[ggd,:]
            if self.ch5_there:
                self.ch5 = self.ch5[ggd,:]
            self.u_random_ch1 = self.u_random_ch1[ggd,:]
            self.u_random_ch2 = self.u_random_ch2[ggd,:]
            if self.ch3a_there:
                self.u_random_ch3a = self.u_random_ch3a[ggd,:]
            self.u_random_ch3b = self.u_random_ch3b[ggd,:]
            self.u_random_ch4 = self.u_random_ch4[ggd,:]
            if self.ch5_there:
                self.u_random_ch5 = self.u_random_ch5[ggd,:]
            self.u_non_random_ch1 = self.u_non_random_ch1[ggd,:]
            self.u_non_random_ch2 = self.u_non_random_ch2[ggd,:]
            if self.ch3a_there:
                self.u_non_random_ch3a = self.u_non_random_ch3a[ggd,:]
            self.u_non_random_ch3b = self.u_non_random_ch3b[ggd,:]
            self.u_non_random_ch4 = self.u_non_random_ch4[ggd,:]
            if self.ch5_there:
                self.u_non_random_ch5 = self.u_non_random_ch5[ggd,:]
            self.u_common_ch1 = self.u_common_ch1[ggd,:]
            self.u_common_ch2 = self.u_common_ch2[ggd,:]
            if self.ch3a_there:
                self.u_common_ch3a = self.u_common_ch3a[ggd,:]
            self.u_common_ch3b = self.u_common_ch3b[ggd,:]
            self.u_common_ch4 = self.u_common_ch4[ggd,:]
            if self.ch5_there:
                self.u_common_ch5 = self.u_common_ch5[ggd,:]
            self.scan_qual = self.scan_qual[ggd]
            self.chan_qual = self.chan_qual[ggd,:]
            self.dRe1_over_dCS = self.dRe1_over_dCS[ggd,:]
            self.dRe2_over_dCS = self.dRe2_over_dCS[ggd,:]
            self.dRe3a_over_dCS = self.dRe3a_over_dCS[ggd,:]
            self.dBT3_over_dT = self.dBT3_over_dT[ggd,:]
            self.dBT4_over_dT = self.dBT4_over_dT[ggd,:]
            self.dBT5_over_dT = self.dBT5_over_dT[ggd,:]
            self.dBT3_over_dCS = self.dBT3_over_dCS[ggd,:]
            self.dBT4_over_dCS = self.dBT4_over_dCS[ggd,:]
            self.dBT5_over_dCS = self.dBT5_over_dCS[ggd,:]
            self.dBT3_over_dCICT = self.dBT3_over_dCICT[ggd,:]
            self.dBT4_over_dCICT = self.dBT4_over_dCICT[ggd,:]
            self.dBT5_over_dCICT = self.dBT5_over_dCICT[ggd,:]
            self.scanline = self.scanline[ggd]
            self.orig_scanline = self.orig_scanline[ggd]
            self.badNav = self.badNav[ggd]
            self.badCal = self.badCal[ggd]
            self.badTime = self.badTime[ggd]
            self.missingLines = self.missingLines[ggd]
            self.solar3 = self.solar3[ggd]
            self.solar4 = self.solar4[ggd]
            self.solar5 = self.solar5[ggd]

            self.ch3b_harm = self.ch3b_harm[ggd,:]
            self.ch4_harm = self.ch4_harm[ggd,:]
            self.ch5_harm = self.ch5_harm[ggd,:]

            if self.montecarlo:
                self.ch1_MC = self.ch1_MC[:,ggd,:]
                self.ch2_MC = self.ch2_MC[:,ggd,:]
                self.ch3a_MC = self.ch3a_MC[:,ggd,:]
                self.ch3_MC = self.ch3_MC[:,ggd,:]
                self.ch4_MC = self.ch4_MC[:,ggd,:]
                self.ch5_MC = self.ch5_MC[:,ggd,:]
                self.nmc = self.ch1_MC.shape[0]

    def __init__(self,data,gd):

        self.mask(data,gd)

#
# Split out data with and without ch3a data (use ch3b being there or not)
#
def get_split_data_remove(data,ch3a=False):

    if ch3a:
        gd = (data.ch3a_there_int == 1)
    else:
        gd = (data.ch3a_there_int == 0)
#    try:
#        gd = np.zeros(data.ch3a_there_int.shape[0],dtype='?')
#        if ch3a:
#            for i in range(len(gd)):
#                gd[i] = not np.any(np.isfinite(data.ch3b[i,:])) 
#        else:
#            for i in range(len(gd)):
#                gd[i] = np.any(np.isfinite(data.ch3b[i,:])) 
#        
#    except:
#        raise Exception('Cannot find c3a data when trying to split')

    newdata = copy_to_data(data,gd)
    
    return newdata

def get_split_data(data,ch3a=False):

    #
    # Find where the data needs to be made NaNs
    #
    if ch3a:
        gd = (data.ch3a_there_int == 0)
    else:
        gd = (data.ch3a_there_int == 1)
#    try:
#        gd = np.zeros(data.ch3a_there_int.shape[0],dtype='?')
#        if ch3a:
#            for i in range(len(gd)):
#                gd[i] = not np.any(np.isfinite(data.ch3b[i,:])) 
#        else:
#            for i in range(len(gd)):
#                gd[i] = np.any(np.isfinite(data.ch3b[i,:])) 
#        
#    except:
#        raise Exception('Cannot find c3a data when trying to split')

    newdata = mask_data(data,gd)
    
    return newdata

#
# Top level routine to output FCDR
#
def main(file_in,fileout='None',ocean_only=False):

    data = read_netcdf(file_in)

    #
    # If we have c3a data then have to split file to 2 channel and 3 channel
    # cases within data
    #
    if data.ch3a_there:
        #
        # Have to split orbit into two to ensure CURUC works
        #        
        data1 = get_split_data(data,ch3a=True)
        if data1.ny >= 1280:
            main_outfile(data1,ch3a_version=True,fileout=fileout,split=True,\
                             ocean_only=ocean_only)
        data2 = get_split_data(data,ch3a=False)
        if data2.ny >= 1280:
            main_outfile(data2,ch3a_version=False,fileout=fileout,split=True,\
                             ocean_only=ocean_only)
    else:
        main_outfile(data,ch3a_version=False,fileout=fileout,\
                         ocean_only=ocean_only)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process FIDUCEO FCDR data.')

    
    parser.add_argument('input_file', nargs=1,\
                            help='Input temporary netCDF file with all variables')    

    parser.add_argument('--output',nargs=1,\
                            help='L1C output format')

    parser.add_argument('--ocean',action='store_true',\
                            help='Output ocean_only data for ensemble')

    args = parser.parse_args()
    
    try:
        outfile = args.output[0]
        outfile_there = True
    except:
        outfile_there = False

    try:
        ocean = args.ocean
    except:
        ocean = False

    if outfile_there:
        if ocean:
            main(args.input_file[0],fileout=outfile,ocean_only=True)
        else:
            main(args.input_file[0],fileout=outfile,ocean_only=False)
    else:
        if ocean:
            main(args.input_file[0],ocean_only=True)
        else:
            main(args.input_file[0],ocean_only=False)

#    usage = "usage: %prog [options] arg1 arg2"
#    parser = OptionParser(usage=usage)
#    (options, args) = parser.parse_args()
#    
#    if len(args) != 1 and len(args) != 2:
#        parser.error("incorrect number of arguments")
#    
#    if len(args) == 1:
#        main(args[0])
#    elif len(args) == 2:
#        main(args[0],fileout=args[1])

