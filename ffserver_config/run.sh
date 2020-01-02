#!/bin/bash


while true; do
	ffmpeg -r 25 -s 640x480 -f video4linux2 -i /dev/video0 -g 50 http://localhost:8090/feed1.ffm
	#ffmpeg -r 15 -s 600x320 -f x11grab -i :0.0  http://localhost:8090/feed1.ffm
	sleep 5 
done
