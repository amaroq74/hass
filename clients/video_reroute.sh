/usr/bin/ffmpeg -rtsp_transport tcp -i rtsp://view:lolhak@172.16.20.5:554/h264Preview_02_sub \
  -acodec copy \
  -vcodec copy \
  -hls_list_size 2 \
  -hls_init_time 1 \
  -hls_time 1 \
  -hls_flags delete_segments  \
  -flags -global_header \
  /amaroq/www/default/cameras/gate.m3u8
