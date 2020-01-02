#!/usr/bin/python
"""
https://longnight975551865.wordpress.com/2018/02/11/how-to-read-data-from-mpu9250/

https://github.com/MomsFriendlyRobotCompany/mpu9250/blob/master/mpu9250/mpu9250.py

https://www.raspberrypi.org/forums/viewtopic.php?t=190939
"""
import smbus
import math
import time
# Register
power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c

GYRO_CONFIG_AD = 0x1B
ACCEL_CONFIG_1_AD = 0x1C
ACCEL_CONFIG_2_AD = 0x1D
CONFIG_AD = 0x1A

bus = smbus.SMBus(1) # bus = smbus.SMBus(0) fuer Revision 1
address = 0x68       # via i2cdetect
AK8963_ADDRESS  = 0x0c
AK8963_ST1 = 0x02  #// data ready status bit 0
AK8963_ST2 = 0x09
AK8963_CNTL1 = 0x0a

def init_compass():
    __MPU6050_RA_INT_PIN_CFG = 0x37
    int_bypass = bus.read_byte_data(address, __MPU6050_RA_INT_PIN_CFG)
    bus.write_byte_data(address, __MPU6050_RA_INT_PIN_CFG, int_bypass | 0x02)
    bus.write_byte_data(AK8963_ADDRESS, AK8963_CNTL1, 0x16)

def setConfig():
    bus.write_byte_data(address, GYRO_CONFIG_AD, 0x08) # 0000 1000 in binary. Set the accel scale to 4g
    bus.write_byte_data(address, ACCEL_CONFIG_1_AD, 0x08) # 0000 1000 in binary. Set the gyro scale to 500 and FCHOICE_B
    bus.write_byte_data(address, ACCEL_CONFIG_2_AD, 0x05) # 0000 0101 in binary. Turn on the internal low-pass filter for accelerometer with 10.2Hz bandwidth
    bus.write_byte_data(address, CONFIG_AD, 0x05) # 0000 0101 in binary. Turn on the internal low-pass filter for gyroscope with 10Hz bandwidth
  
def read_byte(reg):
    return bus.read_byte_data(address, reg)
 
def read_word(reg):
    h = bus.read_byte_data(address, reg)
    l = bus.read_byte_data(address, reg+1)
    value = (h << 8) + l
    return value

def read_word_2l(reg):
    l = bus.read_byte_data(AK8963_ADDRESS, reg)
    h = bus.read_byte_data(AK8963_ADDRESS, reg+1)
    
    #l = bus.read_byte_data(AK8963_ADDRESS, reg)
    #h = bus.read_byte_data(AK8963_ADDRESS, reg+1)
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
    iir_gx = IIR()
    iir_gy = IIR()
    iir_gz = IIR()
    iir_ax = IIR()
    iir_ay = IIR()
    iir_az = IIR()
    iir_mx = IIR(0.5)
    iir_my = IIR(0.5)
    iir_mz = IIR(0.5)

    init_compass()

    f = open(FILE, 'w')
    f.write(HEADER)
    while (1):
        # Aktivieren, um das Modul ansprechen zu koennen
        try:
            bus.write_byte_data(address, power_mgmt_1, 0)
            time.sleep(0.1)
             
            print "Gyroscope"
            print "--------"

            gyroscope_xout = read_word_2c(0x43) # Roll
            gyroscope_yout = read_word_2c(0x45) # Pitch
            gyroscope_zout = read_word_2c(0x47) # Yaw
            gyroscope_xout = iir_gx.run(gyroscope_xout)
            gyroscope_yout = iir_gy.run(gyroscope_yout)
            gyroscope_zout = iir_gz.run(gyroscope_zout)
            gyroscope_xout_norm = gyroscope_xout / 131
            gyroscope_yout_norm = gyroscope_yout / 131
            gyroscope_zout_norm = gyroscope_zout / 131
            print "gyroscope_xout(Roll) : ", ("%5d" % gyroscope_xout), " norm: ", gyroscope_xout_norm
            print "gyroscope_yout(Pitch): ", ("%5d" % gyroscope_yout), " norm: ", gyroscope_yout_norm
            print "gyroscope_zout(Yaw)  : ", ("%5d" % gyroscope_zout), " norm: ", gyroscope_zout_norm
             
            print
            print "Accelerometer"
            print "---------------------"


            accel_xout = read_word_2c(0x3b) # acc_x
            accel_yout = read_word_2c(0x3d) # acc_y
            accel_zout = read_word_2c(0x3f) # acc_z
            accel_xout = iir_ax.run(accel_xout)
            accel_yout = iir_ay.run(accel_yout)
            accel_zout = iir_az.run(accel_zout)

            accel_xout_norm = accel_xout / 16384.0
            accel_yout_norm = accel_yout / 16384.0
            accel_zout_norm = accel_zout / 16384.0
             
            print "accel_xout: ", ("%6d" % accel_xout), " norm: ", accel_xout_norm
            print "accel_yout: ", ("%6d" % accel_yout), " norm: ", accel_yout_norm
            print "accel_zout: ", ("%6d" % accel_zout), " norm: ", accel_zout_norm
             
            print "X Rotation: " , get_x_rotation(accel_xout_norm, accel_yout_norm, accel_zout_norm)
            print "Y Rotation: " , get_y_rotation(accel_xout_norm, accel_yout_norm, accel_zout_norm)
            print "Z Rotation: " , get_z_rotation(accel_xout_norm, accel_yout_norm, accel_zout_norm)

            print
            print "Magnetrometer",  #"%6d" % bus.read_byte_data(AK8963_ADDRESS, AK8963_ST1)
            print "---------------------"

            #print "whoami %d" % bus.read_byte_data(AK8963_ADDRESS, 0x00)
            l = bus.read_i2c_block_data(AK8963_ADDRESS, 0x03, 7)
            #b = bus.read_byte_data(AK8963_ADDRESS, AK8963_ST2)
            #print(0, b)
            if not (l[6] & 0x6):
              mag_x = l[1] << 8 | l[0]#read_word_2l(0x03)
              mag_y = l[3] << 8 | l[2]#read_word_2l(0x05)
              mag_z = l[5] << 8 | l[4]#read_word_2l(0x07)
              mag_x = -((0xffff - mag_x) + 1) if mag_x & 0x8000 else mag_x
              mag_y = -((0xffff - mag_y) + 1) if mag_y & 0x8000 else mag_y
              mag_z = -((0xffff - mag_z) + 1) if mag_z & 0x8000 else mag_z
              #a = bus.read_byte_data(AK8963_ADDRESS, AK8963_ST1)
              mag_x = iir_mx.run(mag_x)
              mag_y = iir_my.run(mag_y)
              mag_z = iir_mz.run(mag_z)
              compass_angle = (math.degrees(math.atan2(mag_x, mag_y)) + 360) % 360
  
              print "mag_x: ", ("%6d" % mag_x)
              print "mag_y: ", ("%6d" % mag_y)
              print "mag_z: ", ("%6d" % mag_z)
              compass_points = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
              num_compass_points = len(compass_points)
              for ii in range(num_compass_points):

                angle_range_min = (360 * (ii - 0.5) / num_compass_points)
                angle_range_max = (360 * (ii + 0.5) / num_compass_points)

                if compass_angle > angle_range_min and compass_angle <= angle_range_max:
                  break
                else:
                  ii = 0 # Special case where max < min when north.
            
              print "compass angle", ("%03.2f" % compass_angle), compass_points[ii]
          
            line = FORMAT.format(time.time(),
                                 accel_xout_norm, accel_yout_norm, accel_zout_norm,
                                 gyroscope_xout_norm, gyroscope_yout_norm, gyroscope_zout_norm,
                                 accel_xout, accel_yout, accel_zout,
                                 gyroscope_xout, gyroscope_yout, gyroscope_zout)
            f.write(line)

        except IOError as e:
            print(e)

        except:
            f.close()
            print("exit!")
            exit(0)

run()