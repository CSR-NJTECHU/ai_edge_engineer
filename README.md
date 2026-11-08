# AI Edge Engineer —— ROS 2 + FunASR 中文语音转文字

把一段录音（`samples/test.wav`）通过 ROS 2 服务转成中文文字（`outputs/result.txt`）。
识别引擎是阿里达摩院开源的 **FunASR `paraformer-zh`** 离线模型。

```
输入音频            ROS 2 ASR 节点           FunASR 模型            识别结果
samples/test.wav -> asr_node.py   ------>   paraformer-zh  ----> 「你好，欢迎学习 ROS 2！」
                     /ai/recognize_audio                          返回 Service + 存 result.txt
```

## 目录结构

```
ai_edge_engineer/
├── models/asr/            # FunASR 权重缓存（不提交 git）
├── samples/               # 测试音频：16kHz / 单声道 / 16bit PCM
│   ├── test.wav           # 2.55s「你好，欢迎学习 ROS 2！」
│   └── test_long.wav      # 9.35s 长音频，用于验证 VAD 分段
├── outputs/               # 识别结果 result.txt
├── scripts/
│   ├── setup_vm_env.sh    # 一键装 ROS 2 Lyrical + venv + FunASR
│   ├── test_funasr.py     # 不依赖 ROS，先验证模型能识别中文
│   └── call_asr_service.sh# 端到端调用服务并打印 result.txt
├── src/ai_asr/            # ROS 2 功能包（ament_python）
│   ├── ai_asr/
│   │   ├── funasr_engine.py  # 识别封装，纯 Python，无 ROS 依赖
│   │   └── asr_node.py       # ROS 2 服务节点
│   ├── launch/asr_launch.py
│   ├── package.xml / setup.py / setup.cfg
└── requirements.txt
```

## 运行环境

ROS 2 官方只在 **Ubuntu 26.04 (amd64/arm64)** 上为一代 LTS **Lyrical Luth** 提供二进制包，
macOS 属于 Tier 3（无二进制、要源码编译）。因此本项目在 **Ubuntu 26.04 虚拟机**里跑，
不要试图在 macOS 上原生安装 ROS 2。

## 五个阶段

### 阶段 1 —— 环境

```bash
bash scripts/setup_vm_env.sh
python3 -c "import rclpy; print('ROS 2 Python 环境正常')"
```

要点：venv 必须用 `--system-site-packages` 创建，否则同一个 Python 里
既要有 apt 装的 `rclpy`，又要有 pip 装的 `funasr`，两者会互相找不到。

### 阶段 2 —— 模型与离线识别

```bash
python3 scripts/test_funasr.py                      # 首次会下载约 1GB 权重
python3 scripts/test_funasr.py --audio samples/test_long.wav
```

期望看到 `[text ] 你好，欢迎学习 ROS 2！`。这一步不涉及 ROS，
能识别就说明模型和 Python 环境没问题。

### 阶段 3 —— 包配置

`package.xml` 依赖 `rclpy` / `std_srvs` / `launch` / `launch_ros`；
`setup.py` 把 `asr_node` 注册成 `console_scripts`，并把 `launch/asr_launch.py`
装到 `share/ai_asr/launch`。Python 依赖见 `requirements.txt`。

### 阶段 4 —— 节点代码

`asr_node.py` 暴露 `std_srvs/srv/Trigger` 服务 `/ai/recognize_audio`，
参数全部通过 ROS 2 parameter 配置：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `audio_path` | `""` | 待识别 wav 路径 |
| `output_path` | `""` | 非空则把文字写入该文件 |
| `model_name` | `paraformer-zh` | FunASR 模型名 |
| `model_path` | `""` | 本地模型目录，非空时优先于 `model_name` |
| `model_cache_dir` | `""` | 权重缓存目录，写入 `MODELSCOPE_CACHE` |
| `use_vad` / `use_punc` | `true` | 是否加载 `fsmn-vad` / `ct-punc` |
| `device` | `cpu` | 虚拟机没有 GPU 直通，保持 cpu |
| `batch_size_s` | `300.0` | 长音频分段批量大小（秒） |
| `hotword` | `""` | 热词，提升专有名词准确率 |
| `preload` | `true` | 启动即加载模型；`false` 则首次请求时加载 |

### 阶段 5 —— 编译与运行

```bash
cd ~/ai_edge_engineer
colcon build --packages-select ai_asr
source install/setup.bash

# 终端 A
ros2 launch ai_asr asr_launch.py
# 终端 B
bash scripts/call_asr_service.sh
```

也可以不带 launch：

```bash
ros2 run ai_asr asr_node --ros-args \
  -p audio_path:=$PWD/samples/test.wav \
  -p output_path:=$PWD/outputs/result.txt
```

## 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| `ModuleNotFoundError: No module named 'rclpy'` | 没 `source /opt/ros/lyrical/setup.bash`，或 venv 不是 `--system-site-packages` 建的 |
| `ModuleNotFoundError: No module named 'funasr'` | venv 没激活；`source ~/ai_edge_engineer/.venv/bin/activate` |
| FunASR 装不上 / torch 报错 | Python 需 3.8–3.12；先 `python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio` 再装 funasr |
| 首次运行卡在下载 | 权重约 1GB，走 ModelScope；可设 `MODELSCOPE_CACHE` 到空间大的目录 |
| 识别结果是乱码/空 | 采样率不是 16kHz，或音频静音；先用 `ffprobe`/`afinfo` 确认格式 |
| 服务调用超时 | 模型还在加载（`preload:=true` 时看日志有没有「模型加载完成」） |
