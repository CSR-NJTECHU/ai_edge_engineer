# Samples

测试音频统一要求 **16kHz / 单声道 / 16bit PCM WAV**（FunASR 的前端就是这个规格，
非 16kHz 会被自动重采样，但准确率会掉）。

本目录已内置两条用 macOS `say` 合成、`afconvert` 转码生成的中文音频：

| 文件 | 时长 | 内容 |
| --- | --- | --- |
| `test.wav` | 2.55s | 你好，欢迎学习 ROS 2！ |
| `test_long.wav` | 9.35s | 你好，欢迎学习语音识别。今天我们把中文语音转文字接入机器人系统，这是第一段测试音频。 |

自己生成（macOS）：

```bash
say -v Tingting -o /tmp/a.aiff "你好，欢迎学习 ROS 2！"
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/a.aiff samples/test.wav
```

Linux 下用 ffmpeg 转码任意音频：

```bash
ffmpeg -i 输入.mp3 -ar 16000 -ac 1 -sample_fmt s16 samples/test.wav
```

真人口语数据（含噪声、口音）比合成语音更能检验模型效果，后续可以替换这里的文件。
