// rescaling
// ffmpeg/doc/examples/scaling_video.c
// input streaming 
// 1. AVFormatContext = avformat_alloc_context()
// 2. err = avformat_open_input(&ic, is->filename, is->iformat, &format_opts);
// 2.5 avformat_seek_file ? av_find_best_stream ? stream_component_open ? avformat_seek_file ?
// 3. av_read_frame (pkt)
// 4. AVFrame *frame = av_frame_alloc()
// 5. av_guess_frame_rate
// 6. for ;; avcodec_receive_frame(ctx, frame)
//    avcodec_flush_buffers
//    av_packet_unref
// 7.
// zhuanlan.zhihu.com/p/36649781 (encoding)
// 1. read from yuv
// 2. output as h264
// 3. create encoder
// 4. open output stream
// 5. create frame and write
// https://blog.mi.hdm-stuttgart.de/index.php/2018/03/21/livestreaming-with-libav-tutorial-part-2/
// 

// https://www.itdaan.com/tw/4eec05e83d49defe9c1610ceb999e260
// v4l2-yuv to h264
// https://kkc.github.io/2019/01/12/ffmpeg-libav-decode-note/

// https://blog.csdn.net/fengbingchun/article/details/94712986
// raw video data to cv::Mat

extern "C"
{
#include "libavdevice/avdevice.h"
#include "libavcodec/avcodec.h"
#include "libavformat/avformat.h"
#include "libswscale/swscale.h"

#include "libavutil/imgutils.h"
#include "libavutil/pixfmt.h"
#include "libavutil/opt.h"

}

// encoder thread
//   open device
//   select encoder
//   encoder option
//   alloc encoder context
//   alloc frame context

typedef struct Decoder {
    AVPacket pkt;
    //PacketQueue *queue;
    AVCodecContext *avctx;
    int pkt_serial;
    int finished;
    int packet_pending;
    //SDL_cond *empty_queue_cond;
    int64_t start_pts;
    AVRational start_pts_tb;
    int64_t next_pts;
    AVRational next_pts_tb;
    //SDL_Thread *decoder_tid;
} Decoder;


// streaming thread

int find(int argc, char **argv, char *value)
{
    int i = 0;
    for (i = 0; i < argc; ++i) {
        if (strcmp(argv[i], value) == 0)
            return i;
    }
    return 0;
}

int setchar(int argc, char **argv, char *key, char *value)
{
    int i = 0;
    if ((i = find(argc, argv, key)) > 0) {
        if ((i + 1) < argc) {
            strcpy(value, argv[i]);
            return 0;
        }
    }
    return 1;
}

struct config {
    char encoder_name[32];
    char input_format[32];
    char input_device[32];
    int input_width;
    int input_height;
    int input_bitrate;
    float input_fps;
    int input_gop;
    char filename[32];
    void parse(int argc, char **args);
    void setup();
};

void config::parse(int argc, char** argv)
{
    setchar(argc, argv, "-c:v", encoder_name);
}

void config::setup()
{
    strcpy(encoder_name, "h264_omx");
    strcpy(input_format, "video4linux2");
    strcpy(input_device, "/dev/video0");
    strcpy(filename, "stream.264");
    input_width = 640;
    input_height = 480;
    input_bitrate = 2048000;
    input_fps = 30;
    input_gop = 30;
}

static void encode(AVCodecContext *enc_ctx, AVFrame *frame, AVPacket *pkt,
                   FILE *outfile)
{
    int ret;

    /* send the frame to the encoder */
    if (frame)
        printf("Send frame %3llu\n", frame->pts);

    ret = avcodec_send_frame(enc_ctx, frame);
    if (ret < 0) {
        fprintf(stderr, "Error sending a frame for encoding\n");
        exit(1);
    }

    while (ret >= 0) {
        ret = avcodec_receive_packet(enc_ctx, pkt);
        if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF)
            return;
        else if (ret < 0) {
            fprintf(stderr, "Error during encoding\n");
            exit(1);
        }

        printf("Write packet %3llu (size=%5d)\n", pkt->pts, pkt->size);
        fwrite(pkt->data, 1, pkt->size, outfile);
        av_packet_unref(pkt);
    }
}

int main(int argc, char **args)
{
    // init avcodec_init()
    // avcodec_register_all()
    // alloc queue context
    // start encoding thread => output to queue
    // start streaming thread => get data from queue

    // input container
	AVFormatContext *iFormatCtx;
    AVCodecParameters *iCodecParam;
    AVInputFormat *ifmt;

    // output container
    AVFormatContext *oFormatCtx;
    AVCodecParameters *oCodecParam;
    AVInputFormat *ofmt;
    AVStream* oVidStream;

    // input-decoder
    AVCodecContext *deCtx;
    AVCodec *deCodec;

    // output encoder
    AVCodecContext *enCtx;
	AVCodec *enCodec;

    uint8_t* picture_buf;
	AVPacket *pkt;
    AVPacket *enpkt;
	AVFrame *deFrame;
    AVFrame *enFrame;

    size_t i;
    int picture_size;
    int videoindex;
    int ret = 0;
    uint8_t endcode[] = { 0, 0, 1, 0xb7 };

	av_register_all();
	avformat_network_init();
	avdevice_register_all();
    avcodec_register_all();

    config cf;
    //cf.parse(argc, argv);
    cf.setup();

    iFormatCtx = avformat_alloc_context();
	ifmt = av_find_input_format(cf.input_format);

	if (avformat_open_input(&iFormatCtx, cf.input_device, ifmt, NULL)!=0) {
	printf("Couldn't open input stream!\n");
	return -1;
	}

	if (avformat_find_stream_info(iFormatCtx, NULL)<0) {
		printf("Couldn't find stream information.\n");
		return -1;
	}

	videoindex = -1;
	for (i = 0; i<iFormatCtx->nb_streams; i++) {
		if (iFormatCtx->streams[i]->codec->codec_type==AVMEDIA_TYPE_VIDEO) {
            iCodecParam = iFormatCtx->streams[i]->codecpar;
			videoindex=i;
			break;
		}
	}

    av_dump_format(iFormatCtx, 0, cf.input_device, 0);

	if (videoindex == -1 || iCodecParam == nullptr) {
		printf("Couldn't find a video stream!\n");
		return -1;
	}

    //deCodec = avcodec_find_decoder(iCodecParam->codec_id);
    //if (deCodec) {
    //    fprintf(stderr, "Decoder codec not found\n");
    //    exit(1);
    //}
    //deCtx = avcodec_alloc_context3(deCodec);
    //avcodec_parameters_to_context(deCtx, iCodecParam);
    //avcodec_open2(deCtx, deCodec, NULL);

    enCodec = avcodec_find_encoder_by_name(cf.encoder_name);
    if (!enCodec) {
        fprintf(stderr, "Encoder codec not found\n");
        exit(1);
    }
    enCtx = avcodec_alloc_context3(enCodec);
    enCtx->bit_rate=cf.input_bitrate;
    enCtx->width =cf.input_width;
    enCtx->height=cf.input_height;
    enCtx->time_base=(AVRational){1,(int)cf.input_fps};
    enCtx->framerate = (AVRational){(int)cf.input_fps, 1};
    enCtx->gop_size=30;
    enCtx->pix_fmt= AV_PIX_FMT_YUV420P;

    if (enCodec->id == AV_CODEC_ID_H264) {
        av_opt_set(enCtx->priv_data, "profile", "main", 0);
        av_opt_set_int(enCtx->priv_data, "zerocopy", 1, 0);
    }
    avcodec_open2(enCtx, enCodec, NULL);

    pkt = av_packet_alloc();
    deFrame = av_frame_alloc();

    enpkt = av_packet_alloc();
    enFrame = av_frame_alloc();
    enFrame->format = enCtx->pix_fmt;
    enFrame->width = enCtx->width;
    enFrame->height = enCtx->height;

    picture_size = avpicture_get_size(enCtx->pix_fmt, enCtx->width, enCtx->height);  
    picture_buf = (uint8_t *)av_malloc(picture_size);
    int y_size = enCtx->width * enCtx->height;  

    avpicture_fill((AVPicture *)enFrame, picture_buf, enCtx->pix_fmt, enCtx->width, enCtx->height);  
    //ret = av_frame_get_buffer(enFrame, 32);
    //if (ret < 0) {
    //    fprintf(stderr, "Could not allocate the video frame data\n");
    //    exit(1);
    //}
    //oVidStream = avformat_new_stream(oFormatCtx, 0);  
    //    oVidStream->time_base.num = 1;   
    //    oVidStream->time_base.den = cf.input_fps;    
      
    //if (oVidStream==NULL){  
    //    return -1;  
    //}  
    // write header for some file
    //avformat_write_header(oFormatCtx,NULL);  

    FILE *f = fopen(cf.filename, "wb");
    if (!f) {
        fprintf(stderr, "Could not open %s\n", cf.filename);
        exit(1);
    }
    int j=0;
    FILE *pgm = fopen("test.pgm", "wb");
    fprintf(pgm, "P5\n%d %d\n255\n", enCtx->width, enCtx->height);

    while (av_read_frame(iFormatCtx, pkt) >= 0) {
        if (pkt->stream_index != videoindex) {
            printf("Recv !vid pkt!\n");
            continue;
        }
        if (j == 0) {
            fwrite(pkt->data, enCtx->height*enCtx->width, 1, pgm);
            fclose(pgm);
        }
        printf("running %d\n", j);
        #if 1
        enFrame->data[0] = &pkt->data[0];          // Y  
        enFrame->data[1] = &pkt->data[0] + y_size;      // U   
        enFrame->data[2] = &pkt->data[0] + y_size*5/4;  // V 
        enFrame->pts=j++*(float)enCtx->time_base.den/((enCtx->time_base.num));
        #else  // from decoder
        //if (avcodec_send_packet(deCtx, pkt) == AVERROR(EAGAIN)) {
        //    int dummpy = 1;
        //    continue;
        //}

        //ret = avcodec_receive_frame(deCtx, deFrame);
        //if (ret >= 0)
        //    deFrame->pts = deFrame->pkt_dts; // frame->best_effort_timestamp?


        printf(
            "Frame %c (%d) pts %d dts %d key_frame %d [coded_picture_number %d, display_picture_number %d]",
            av_get_picture_type_char(deFrame->pict_type),
            deCtx->frame_number,
            deFrame->pts,
            deFrame->pkt_dts,
            deFrame->key_frame,
            deFrame->coded_picture_number,
            deFrame->display_picture_number
        );

        if (ret == AVERROR_EOF) {
            avcodec_flush_buffers(deCtx);
            goto close_all;
        }
        #endif

        ret = avcodec_send_frame(enCtx, enFrame);
        if (ret < 0) {
            fprintf(stderr, "Error sending a frame for encoding\n");
            exit(1);
        }
        while (ret >= 0) {
            ret = avcodec_receive_packet(enCtx, enpkt);
            if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF)
                continue;
            else if (ret < 0) {
                fprintf(stderr, "Error during encoding\n");
                exit(1);
            }

            printf("Write packet %llu (size=%5d)\n", enpkt->pts, enpkt->size);
            fwrite(enpkt->data, 1, enpkt->size, f);
            av_packet_unref(enpkt);
        }

    }


    fwrite(endcode, 1, sizeof(endcode), f);
    fclose(f);

close_all:

    avcodec_free_context(&enCtx);
    avcodec_free_context(&deCtx);
    avformat_free_context(iFormatCtx);
    avformat_free_context(oFormatCtx);
    av_frame_free(&deFrame);
    av_packet_free(&enpkt);
    av_packet_free(&pkt);

}
