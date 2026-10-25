import tempfile
import unittest
from pathlib import Path

from formatkae.core import Media, Options, build_command, effective_duration, output_path, parse_extra, time_seconds


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.media = Media(str(Path("样本.mp4").resolve()), duration=60, video="h264", audio="aac", width=1280, height=720)

    def test_time_and_crop(self):
        self.assertEqual(time_seconds("01:02:03.5"), 3723.5)
        self.assertEqual(effective_duration(self.media, Options(start="10", end="20")), 10)
        for value in ["-1", "nan", "inf", "00:60:00", "a:b", "1:2:3:4"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                time_seconds(value)
        with self.assertRaises(ValueError):
            Options(start="20", end="10").validate(self.media)

    def test_original_and_existing_outputs_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            media = Media(str(folder / "素材.mp4"))
            (folder / "素材.mp4").write_bytes(b"original")
            (folder / "素材_converted.mp4").write_bytes(b"existing")
            reserved = set()
            first = output_path(media, folder, "mp4", reserved)
            second = output_path(media, folder, "mp4", reserved)
            self.assertEqual(first.name, "素材_converted_1.mp4")
            self.assertEqual(second.name, "素材_converted_2.mp4")
            self.assertEqual((folder / "素材.mp4").read_bytes(), b"original")

    def test_extra_options_do_not_add_input_or_output(self):
        self.assertEqual(parse_extra('-metadata title="我的 视频" -vf "hflip" -shortest'), ["-metadata", "title=我的 视频", "-vf", "hflip", "-shortest"])
        for value in ['-i "another.mp4"', '-y', '-progress pipe:2', '-vf hflip output.mp4', 'output.mp4', '-metadata', '-/filter:v file', '-passlogfile secret']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_extra(value)

    def test_copy_rejects_filtering(self):
        with self.assertRaises(ValueError):
            Options(video_codec="copy", width=640).validate(self.media)
        with self.assertRaises(ValueError):
            Options(audio_codec="copy", volume=50).validate(self.media)

    def test_bad_parameters(self):
        for options in [Options(fps="0"), Options(fps="1/0"), Options(fps="nan"), Options(video_bitrate="-1M"), Options(custom_ext="../mp4", format="nut"), Options(sample_rate="abc"), Options(channels="9")]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                options.validate(self.media)

    def test_missing_streams(self):
        with self.assertRaises(ValueError):
            Options(format="mp3").validate(Media("silent.mp4", video="h264"))
        with self.assertRaises(ValueError):
            Options(format="gif").validate(Media("audio.wav", audio="pcm_s16le"))
        with self.assertRaises(ValueError):
            Options(format="mp3", audio_codec="禁用音频").validate(self.media)

    def test_command_and_unicode_paths(self):
        command = build_command(Path("ffmpeg.exe"), self.media, Options(width=640, start="1", end="3"), Path("中文 输出.mp4"))
        self.assertIn("scale=640:-2", command)
        self.assertEqual(command[command.index("-t") + 1], "2")
        self.assertIn(self.media.path, command)
        self.assertEqual(command[-1], "中文 输出.mp4")
        self.assertIn("-n", command)
        self.assertNotIn("-y", command)


if __name__ == "__main__":
    unittest.main()
