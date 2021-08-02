import glob
import os
import sys
import argparse
import cv2
import matplotlib.pyplot as plt
import numpy as np
import random
import time
import math
import queue

fourcc = cv2.VideoWriter_fourcc(*'DIVX')
out = cv2.VideoWriter('output.avi', fourcc, 30.0, (800,600))
try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

def region_of_interest(img, vertices, color3=(255, 255, 255), color1=255):  # ROI 셋팅
    mask = np.zeros_like(img)  # mask = img와 같은 크기의 빈 이미지
    if len(img.shape) > 2:  # Color 이미지(3채널)라면 :
        color = color3
    else:  # 흑백 이미지(1채널)라면 :
        color = color1
    # vertices에 정한 점들로 이뤄진 다각형부분(ROI 설정부분)을 color로채움
    cv2.fillPoly(mask, vertices, color)
    # 이미지와 color로 채워진 ROI를 합침
    ROI_image = cv2.bitwise_and(img, mask)
    return ROI_image



# 이미지에 직선을 그리는 함수
def draw_lines(img, lines, color=[255, 255, 255], thickness=2): # 선 그리기
    poss = []
    for line in lines:

        m = (line[1] - line[3]) / (line[2] - line[0])
        c = m * line[0] + line[1]


        x1 = int((c-600)/m)
        x2 = int((c-300)/m)
        cv2.line(img, (x1, 600), (x2, 300), color, thickness)
        pos = (c - 500)/m
        poss.append(pos)
    return poss

def draw_lines2(img, lines, color=[0, 0, 255], thickness=2): # 선 그리기
    for line in lines:
        x1 = line[0]
        y1 = line[1]
        x2 = line[2]
        y2 = line[3]
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)




# 허프변환
def hough_lines(img, rho, theta, threshold, min_line_len, max_line_gap):
    lines = cv2.HoughLinesP(img, rho, theta, threshold, np.array([]), minLineLength=min_line_len,
                            maxLineGap=max_line_gap)
    return lines


# 사각형을 2개 그리는 함수
# draw rectangle
def draw_rectangle(img, lpos, rpos, offset=0):
    cv2.rectangle(img, (lpos - 5, -5 + offset),
                  (lpos + 5, +5 + offset),
                  (0, 255, 0), 2)
    cv2.rectangle(img, (rpos - 5, -5 + offset),
                  (rpos + 5, +5 + offset),
                  (0, 255, 0), 2)
    return img


# 사각형을 1개 그리는 함수
def draw_rectangle2(img, pos, offset=0, color=[255, 0, 0]):
    cv2.rectangle(img, (pos - 5, -5 + offset),
                  (pos + 5, +5 + offset),
                  color, 2)
    return img


def canny(img, low_threshold, high_threshold):  # Canny 알고리즘
    return cv2.Canny(img, low_threshold, high_threshold)


def gaussian_blur(img, kernel_size):  # 가우시안 필터
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)


def weighted_img(img, initial_img, a=1, b=1, c=0):  # 두 이미지 operlap 하기
    return cv2.addWeighted(initial_img, a, img, b, c)

steer_angle = 0
def process_image(image):
    global steer_angle


    image = np.array(image.raw_data)
    img = image.reshape((600,800,4))
    img = img[:,:,:3]
    hls =cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
    h,l,s = cv2.split(hls)
    #cv2.imshow('l',l)

    # gaussian blur 함수
    blur_img = gaussian_blur(l, 3)
    #canny edge detection 함수
    canny_img = canny(blur_img, 10, 100)
    # ROI를 위한 다각형 정의
    left_bottom = (0,600)
    left_top = (200,350)
    right_top = (600,350)
    right_bottom = (800,600)


    vertices = np.array(
        [[left_bottom, left_top, right_top, right_bottom]],
        dtype=np.int32)
    # ROI 함수 사용
    ROI_img = region_of_interest(canny_img, vertices)
    # hough로 인식한 직선들
    main_line = []
    final_line = []

    line_arr = hough_lines(ROI_img, 1, 1 * np.pi / 180, 30, 1, 10)

    line_arr = np.squeeze(line_arr)
    slope_degree = (np.arctan2(line_arr[:, 1] - line_arr[:, 3], line_arr[:, 0] - line_arr[:, 2]) * 180) / np.pi


    for line in line_arr:
        try:

            m = (line[1]-line[3])/(line[2]-line[0])
            c = m*line[0] + line[1]
            point = -m*400 + c
            if 270 < point < 330:
                main_line.append(line)
        except:
            print('line error')




    for i in range(len(main_line)):
        overlapped =False

        if abs(abs(slope_degree[i]) -90) > 20 and abs(abs(slope_degree[i]) -180) >40:
            if len(final_line) ==0:
                final_line.append(main_line[i])
            #차선사이의 거리 측정하여 가까우면 배제
            for j in final_line:
                area = abs((j[0] - main_line[i][0]) * (j[3] - main_line[i][1]) - (j[1] - main_line[i][1]) * (
                            j[2] - main_line[i][0]))
                length = ((j[0] - j[2]) **2 + (j[1] - j[3]) **2) **0.5
                dist = area / length
                if dist < 40:
                    overlapped =True
            if not overlapped:
                final_line.append(main_line[i])



    draw_rectangle2(ROI_img, left_bottom[0],left_bottom[1])
    draw_rectangle2(ROI_img, left_top[0], left_top[1])
    draw_rectangle2(ROI_img, right_top[0], right_top[1])
    draw_rectangle2(ROI_img, right_bottom[0], right_bottom[1])



    temp = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    poss = draw_lines(temp, final_line)
    draw_lines2(temp, main_line)

    poss = sorted(poss, key = lambda x : abs(x-400))

    if len(poss) >1:
        final_pos = [poss[0],poss[1]]
    elif len(poss) == 1:
        if poss[0] <400:
            final_pos = [poss[0],poss[0]+400]
        else:
            final_pos = [poss[0]-400,poss[0]]
    else:
        final_pos = [200,600]
    final_pos.sort()
    average_pos = sum(final_pos)/2

    if average_pos >400:
        if final_pos[0] + final_pos[1] > 800:
            print('right lane missing')
            average_pos = final_pos[0] + 200
        else:
            print('left lane missing')
            average_pos = final_pos[1]-200

    steer_angle = (average_pos - 400)/100


    result = weighted_img(temp,img)
    weighted_img(temp,img)


    out.write(result)  # 영상 데이터만 저장. 소리는 X


def get_speed(vehicle):

    vel = vehicle.get_velocity()

    return 3.6*math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)




class Autopilot():

    def __init__(self,vehicle):
        self.vehicle = vehicle
        self.world = vehicle.get_world()
        self.past_steering =self.vehicle.get_control().steer


    def run_step(self,steer_angle):


        control = carla.VehicleControl()



        control.hand_brake = False
        control.manual_gear_shift = False
        #self.past_steering = steering

        control.steer = steer_angle
        control.throttle = 0.5


        return control


def main():
    global steer_angle
    actor_list = []

    try:
        steer_angle = 0
        client = carla.Client('127.0.0.1',2000)
        client.set_timeout(5.0)
        client.load_world('Town04_Opt')
        print(client.get_available_maps())
        world = client.get_world()
        map = world.get_map()

        blueprint_library = world.get_blueprint_library()
        vehicle_bp = blueprint_library.filter('cybertruck')[0]
        spawnpoint = carla.Transform(carla.Location(x=-30,y=34,z = 13),carla.Rotation(pitch = 0, yaw = 0, roll = 0))
        vehicle = world.spawn_actor(vehicle_bp, spawnpoint)
        actor_list.append(vehicle)
        print(steer_angle)
        control_vehicle = Autopilot(vehicle)

        while True:


            camera_bp = blueprint_library.find('sensor.camera.rgb')
            camera_bp.set_attribute('image_size_x','800')
            camera_bp.set_attribute('image_size_y', '600')
            camera_bp.set_attribute('fov', '90')
            camera_transform = carla.Transform(carla.Location(x=2.5,z=1.7))

            camera = world.spawn_actor(camera_bp, camera_transform,attach_to = vehicle)

            try:
                camera.listen(lambda image: process_image(image))
            except:
                steer_angle = 0
            control_signal = control_vehicle.run_step(steer_angle)
            vehicle.apply_control(control_signal)

            actor_list.append(camera)


    finally:
        client.apply_batch([carla.command.DestroyActor(x) for x in actor_list])


if __name__ == '__main__':
    main()

