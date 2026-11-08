"""ai_asr 的 launch 文件：一条命令启动 ASR 服务节点。

用法（在项目根目录，已 source ROS 2 与虚拟环境）：

    ros2 launch ai_asr asr_launch.py
    ros2 launch ai_asr asr_launch.py audio_path:=samples/test.wav output_path:=outputs/result.txt
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 默认按「当前工作目录 = 项目根目录」推导路径；
    # 也可以 export AI_EDGE_PROJECT=/path/to/ai_edge_engineer 覆盖。
    project_root = os.path.abspath(
        os.environ.get("AI_EDGE_PROJECT", os.getcwd())
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "audio_path",
                default_value=os.path.join(project_root, "samples", "test.wav"),
                description="待识别的 wav 文件路径",
            ),
            DeclareLaunchArgument(
                "output_path",
                default_value=os.path.join(project_root, "outputs", "result.txt"),
                description="识别文字保存路径，留空则只走服务返回值",
            ),
            DeclareLaunchArgument(
                "model_name",
                default_value="paraformer-zh",
                description="FunASR 模型名，也可换成 iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            ),
            DeclareLaunchArgument(
                "model_cache_dir",
                default_value=os.path.join(project_root, "models", "asr"),
                description="模型权重缓存目录（MODELSCOPE_CACHE），不要提交到 git",
            ),
            DeclareLaunchArgument("device", default_value="cpu"),
            DeclareLaunchArgument("use_vad", default_value="true"),
            DeclareLaunchArgument("use_punc", default_value="true"),
            DeclareLaunchArgument("batch_size_s", default_value="300.0"),
            DeclareLaunchArgument("hotword", default_value=""),
            DeclareLaunchArgument("preload", default_value="true"),
            Node(
                package="ai_asr",
                executable="asr_node",
                name="asr_node",
                output="screen",
                emulate_tty=True,
                parameters=[
                    {
                        "audio_path": LaunchConfiguration("audio_path"),
                        "output_path": LaunchConfiguration("output_path"),
                        "model_name": LaunchConfiguration("model_name"),
                        "model_cache_dir": LaunchConfiguration("model_cache_dir"),
                        "device": LaunchConfiguration("device"),
                        "use_vad": LaunchConfiguration("use_vad"),
                        "use_punc": LaunchConfiguration("use_punc"),
                        "batch_size_s": LaunchConfiguration("batch_size_s"),
                        "hotword": LaunchConfiguration("hotword"),
                        "preload": LaunchConfiguration("preload"),
                    }
                ],
            ),
        ]
    )
