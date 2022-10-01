import os
from pathlib import Path
from time import time
from typing import Union

import ffmpeg

from logger import logger


def current_milli_time():
    return round(time() * 1000)

class Video:
    def __init__(self, video_path: str) -> None:
        self.video_path: str = video_path
        try:
            self.probe: dict = ffmpeg.probe(self.video_path)
        except ffmpeg.Error as err:
            logger.error("ffmpeg stdout", err.stdout.decode())
            logger.error("ffmpeg stderr", err.stderr.decode())
            raise err
    
    @property
    def duration(self) -> float:
        return float(self.probe['format']['duration'])

    @property
    def audio_bitrate(self) -> float:
        return float(next((s for s in self.probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])

    def compress_video(self, size_upper_bound: int, output_file_name: str = None, two_pass=True) -> Union[Path, None]:
        """
        Compress video file to max-supported size.
        :param size_upper_bound: Max video size in KB.
        :param output_file_name: Name of the output file.
        :param two_pass: Set to True to enable two-pass calculation.

        REFERENCE: https://gist.github.com/ESWZY/a420a308d3118f21274a0bc3a6feb1ff
        """

        video_full_path = self.video_path
        file_name = output_file_name if output_file_name else f"{current_milli_time()}.mp4"

        # Adjust them to meet your minimum requirements (in bps), or maybe this function will refuse your video!
        total_bitrate_lower_bound = 11000
        min_audio_bitrate = 32000
        max_audio_bitrate = 256000
        min_video_bitrate = 100000

        try:
            # Bitrate reference: https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate
            if output_file_name:
                self.probe = ffmpeg.probe(output_file_name)
            # Video duration, in s.
            duration = self.duration
            # Audio bitrate, in bps.
            audio_bitrate = self.audio_bitrate
            # Target total bitrate, in bps.
            target_total_bitrate = (size_upper_bound * 1024 * 8) / (1.073741824 * duration)
            if target_total_bitrate < total_bitrate_lower_bound:
                print('Bitrate is extremely low! Stop compress!')
                return None

            # Best min size, in kB.
            best_min_size = (min_audio_bitrate + min_video_bitrate) * (1.073741824 * duration) / (8 * 1024)
            if size_upper_bound < best_min_size:
                print('Quality not good! Recommended minimum size:', '{:,}'.format(int(best_min_size)), 'KB.')
                # return None

            # Target audio bitrate, in bps.
            audio_bitrate = audio_bitrate

            # target audio bitrate, in bps
            if 10 * audio_bitrate > target_total_bitrate:
                audio_bitrate = target_total_bitrate / 10
                if audio_bitrate < min_audio_bitrate < target_total_bitrate:
                    audio_bitrate = min_audio_bitrate
                elif audio_bitrate > max_audio_bitrate:
                    audio_bitrate = max_audio_bitrate

            # Target video bitrate, in bps.
            video_bitrate = target_total_bitrate - audio_bitrate
            if video_bitrate < 1000:
                print('Bitrate {} is extremely low! Stop compress.'.format(video_bitrate))
                return None

            i = ffmpeg.input(video_full_path)
            if two_pass:
                ffmpeg.output(i, os.devnull,
                            **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
                            ).overwrite_output().run(quiet=True)
                ffmpeg.output(i, file_name,
                            **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac', 'b:a': audio_bitrate}
                            ).overwrite_output().run(quiet=True)
                
            else:
                ffmpeg.output(i, file_name,
                            **{'c:v': 'libx264', 'b:v': video_bitrate, 'c:a': 'aac', 'b:a': audio_bitrate}
                            ).overwrite_output().run(quiet=True)

            if os.path.getsize(file_name) <= size_upper_bound * 1024:
                return Path(file_name)
            elif os.path.getsize(file_name) < os.path.getsize(video_full_path):  # Do it again
                return self.compress_video(size_upper_bound, file_name)
            else:
                return None
        except FileNotFoundError as e:
            print('You do not have ffmpeg installed!', e)
            print('You can install ffmpeg by reading https://github.com/kkroening/ffmpeg-python/issues/251')
            return None

if __name__ == '__main__':
    vid = Video("http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4")
    vid.compress_video(12*1000)
