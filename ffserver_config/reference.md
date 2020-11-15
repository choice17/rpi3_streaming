## There are many streaming info

1. ffmpeg + vlc

https://sites.google.com/view/how2raspberrypi/streaming-video-with-vlc

2. build hw h264 encoder omx (rpi3) for ffmpeg 

https://gist.github.com/milankragujevic/bd38d796ea6eea27f229216d75d6c202
<details>
<summary>ffmpeg build</summary>
wget http://www.deb-multimedia.org/pool/main/d/deb-multimedia-keyring/deb-multimedia-keyring_2016.8.1_all.deb -O /tmp/deb-multimedia-keyring.deb
sudo dpkg -i /tmp/deb-multimedia-keyring.deb 
rm /tmp/deb-multimedia-keyring.deb
sudo sh -c 'echo "deb http://www.deb-multimedia.org stretch main non-free" >> /etc/apt/sources.list'
sudo apt update
sudo apt upgrade -y 
sudo apt install -y libfdk-aac-dev libomxil-bellagio-dev libx264-dev libasound2-dev libmp3lame-dev autoconf automake build-essential libfreetype6-dev libtool pkg-config texinfo zlib1g-dev git
cd ~
git clone git://source.ffmpeg.org/ffmpeg.git
cd ffmpeg/
./configure --enable-indev=alsa --arch=armel --target-os=linux --enable-gpl --enable-omx --enable-omx-rpi --enable-nonfree --enable-libfdk-aac --enable-libmp3lame  --disable-shared --enable-static
make -j4
sudo make install
</details>

## success command  

Machine rpi3B

ffmpeg 4.2 h264_omx + sdl2 
vlc

ffmpeg -f video4linux2 -framerate 30 -video_size 640x480 -i /dev/video0 -pix_fmt yuv420p -c h264_omx -f rawvideo - | cvlc -vvv stream:///dev/stdin --sout '#rtp{sdp=rtsp://192.168.1.147:8554/test}' :demux=h264
