import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

def vnorm(in_v):
    return np.array(in_v) / np.linalg.norm(in_v)

def get_3d_dir_vector(in_v):
    """
    @right hand rule
    @idx:0 - y_v
    @idx:1 - x_v
    @idx:2 - z_v
    """
    unit_v = np.zeros((4,3))
    unit_v[0,:] = vnorm(in_v)
    #print(unit_v[0,:],  vnorm(in_v))
    unit_v[2,:] = vnorm(np.cross(unit_v[0,:], [1, 0, 0]))
    #print(unit_v[2,:])
    unit_v[1,:] = np.cross(unit_v[0,:], unit_v[2,:])
    #print(unit_v[1,:])
    return unit_v


def update_line(xl, yl, zl, new_data):
    yl.set_xdata([0.,new_data[0,0]])
    yl.set_ydata([0.,new_data[0,1]])
    yl.set_3d_properties([0,new_data[0,2]])
    # plt.draw()
    xl.set_xdata([0.,new_data[2,0]])
    xl.set_ydata([0.,new_data[2,1]])
    xl.set_3d_properties([0,new_data[2,2]])
    # plt.draw()
    zl.set_xdata([0.,new_data[1,0]])
    zl.set_ydata([0.,new_data[1,1]])
    zl.set_3d_properties([0,new_data[1,2]])
    plt.draw()


def run_plot_data(num, data, rate=0.1):
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

    for i in range(num):
        # print("0 ===============>> ", data[i])
        xyz = get_3d_dir_vector(np.array(data[i]))
        # print(xyz)
        update_line(xl, yl, zl, xyz)
        print(np.linalg.norm(data[i]),np.linalg.norm(xyz[0,:]),np.linalg.norm(xyz[1,:]),np.linalg.norm(xyz[2,:]))

        # print("4 ===============>> ")
        plt.show(block=False)
        # print("5 ===============>> ")
        plt.pause(rate)
        # print("6 ===============>> ")


def read_csv(FILE, r=[1,7]):
    f = open(FILE, 'r')
    data = f.read().split('\n')
    data.pop()
    f.close()
    HEADER = data[0].split(',')
    content = []
    time_ = []
    for i in data[1:]:
        l = i.split(',')
        content.append([float(ii) for ii in l[r[0]:r[1]]])
        time_.append(float(l[0]))
    return content


def main():
    FILE = 'data.csv'
    rate = 0.02
    data = read_csv(FILE, r=[1,4])
    num = len(data)
    run_plot_data(num, data, rate)


if __name__ == '__main__':
    main()