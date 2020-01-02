#!/usr/bin/python
import smbus
import math
import time
from utils import *
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

# Register
power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c

bus = smbus.SMBus(1) # bus = smbus.SMBus(0) fuer Revision 1
address = 0x68       # via i2cdetect
RATE = 0.05

def read_byte(reg):
    return bus.read_byte_data(address, reg)
 
def read_word(reg):
    h = bus.read_byte_data(address, reg)
    l = bus.read_byte_data(address, reg+1)
    value = (h << 8) + l
    return value
 
def read_word_2c(reg):
    val = read_word(reg)
    if (val >= 0x8000):
        return -((65535 - val) + 1)
    else:
        return val
 
def dist(a,b):
    return math.sqrt((a*a)+(b*b))
 
def get_y_rotation(x,y,z):
    radians = math.atan2(x, dist(y,z))
    return -math.degrees(radians)
 
def get_x_rotation(x,y,z):
    radians = math.atan2(y, dist(x,z))
    return math.degrees(radians)

def get_z_rotation(x,y,z):
    radians = math.atan2(z, dist(x,y))
    return math.degrees(radians)

class IIR(object):
    """first order"""
    __slots__ = ('rate', 'y_1', '_rate')
    def __init__(self, rate=0.1):
        self.rate = rate
        self._rate = 1 - rate
        self.y_1 = 0

    def run(self, x):
        self.y_1 = self.rate * x +  self._rate * self.y_1
        return self.y_1

FILE = 'data.csv'
HEADER = "time,acc_x,acc_y,acc_z,gyro_x,gyro_y,gyro_z,acc_x_raw,acc_y_raw,acc_z_raw,gyro_x_raw,gyro_y_raw,gyro_z_raw\n"
FORMAT = "{},{},{},{},{},{},{},{},{},{},{},{},{}\n"


def run():

    map = plt.figure()
    map_ax = Axes3D(map)
    map_ax.autoscale(enable=True, axis='both', tight=True)

    # # # Setting the axes properties
    map_ax.set_xlim3d([-2, 2])
    map_ax.set_ylim3d([-2, 2])
    map_ax.set_zlim3d([-2, 2])

    xl, = map_ax.plot3D([0], [0], [0])
    yl, = map_ax.plot3D([0], [0], [0])
    zl, = map_ax.plot3D([0], [0], [0])

    xl.set_color("red")
    yl.set_color("blue")
    zl.set_color("green")

    iir_gx = IIR()
    iir_gy = IIR()
    iir_gz = IIR()
    iir_ax = IIR()
    iir_ay = IIR()
    iir_az = IIR()

    # f = open(FILE, 'w')
    # f.write(HEADER)
    while (1):
        # Aktivieren, um das Modul ansprechen zu koennen
        try:
            bus.write_byte_data(address, power_mgmt_1, 0)
            time.sleep(RATE)
             
            # print "Gyroscope"
            # print "--------"

            gyroscope_xout = read_word_2c(0x43) # Roll
            gyroscope_yout = read_word_2c(0x45) # Pitch
            gyroscope_zout = read_word_2c(0x47) # Yaw
            gyroscope_xout = iir_gx.run(gyroscope_xout)
            gyroscope_yout = iir_gy.run(gyroscope_yout)
            gyroscope_zout = iir_gz.run(gyroscope_zout)
            gyroscope_xout_norm = gyroscope_xout / 131
            gyroscope_yout_norm = gyroscope_yout / 131
            gyroscope_zout_norm = gyroscope_zout / 131
            # print "gyroscope_xout(Roll) : ", ("%5d" % gyroscope_xout), " norm: ", gyroscope_xout_norm
            # print "gyroscope_yout(Pitch): ", ("%5d" % gyroscope_yout), " norm: ", gyroscope_yout_norm
            # print "gyroscope_zout(Yaw)  : ", ("%5d" % gyroscope_zout), " norm: ", gyroscope_zout_norm
             
            # print
            # print "Accelerometer"
            # print "---------------------"


            accel_xout = read_word_2c(0x3b)
            accel_yout = read_word_2c(0x3d)
            accel_zout = read_word_2c(0x3f)
            accel_xout = iir_ax.run(accel_xout)
            accel_yout = iir_ay.run(accel_yout)
            accel_zout = iir_az.run(accel_zout)

            accel_xout_norm = accel_xout / 16384.0
            accel_yout_norm = accel_yout / 16384.0
            accel_zout_norm = accel_zout / 16384.0

             
            # print "accel_xout: ", ("%6d" % accel_xout), " norm: ", accel_xout_norm
            # print "accel_yout: ", ("%6d" % accel_yout), " norm: ", accel_yout_norm
            # print "accel_zout: ", ("%6d" % accel_zout), " norm: ", accel_zout_norm
             
            # print "X Rotation: " , get_x_rotation(accel_xout_norm, accel_yout_norm, accel_zout_norm)
            # print "Y Rotation: " , get_y_rotation(accel_xout_norm, accel_yout_norm, accel_zout_norm)
            # print "Z Rotation: " , get_z_rotation(accel_xout_norm, accel_yout_norm, accel_zout_norm)

            # line = FORMAT.format(time.time(),
            #                      accel_xout_norm, accel_yout_norm, accel_zout_norm,
            #                      gyroscope_xout_norm, gyroscope_yout_norm, gyroscope_zout_norm,
            #                      accel_xout, accel_yout, accel_zout,
            #                      gyroscope_xout, gyroscope_yout, gyroscope_zout)
            # f.write(line)
            xyz = get_3d_dir_vector(np.array([accel_xout_norm,accel_yout_norm,accel_zout_norm]))
            update_line(xl, yl, zl, xyz)
            plt.show(block=False)
            plt.pause(RATE)

        except IOError as e:
            print(e)

        except:
            # f.close()
            print("exit!")
            exit(0)

run()