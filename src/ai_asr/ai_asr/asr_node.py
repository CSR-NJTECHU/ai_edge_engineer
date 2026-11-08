"""ROS 2 ASR 服务节点：FunASR (paraformer-zh) 离线中文识别。

服务接口保持不变，方便沿用教程里的调用方式：

    ros2 service call /ai/recognize_audio std_srvs/srv/Trigger "{}"

节点参数分两类：
* 教程原有参数 ``audio_path`` / ``model_path`` / ``output_path``；
  其中 ``model_path`` 的含义变了 —— 现在指本地 FunASR 模型目录，留空则按
  ``model_name`` 在线下载。
* 新增参数 ``model_name`` / ``model_cache_dir`` / ``use_vad`` / ``use_punc``
  / ``device`` / ``batch_size_s`` / ``hotword`` / ``preload``。

识别逻辑在 :mod:`ai_asr.funasr_engine`，本文件只做 ROS 2 的封装。
"""

import os

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from ai_asr.funasr_engine import FunAsrEngine, probe_wav


class ASRNode(Node):
    def __init__(self):
        super().__init__("asr_node")

        # ---- 教程原有参数 ----
        self.declare_parameter("audio_path", "")
        self.declare_parameter("model_path", "")
        self.declare_parameter("output_path", "")

        # ---- FunASR 参数 ----
        self.declare_parameter("model_name", "paraformer-zh")
        self.declare_parameter("model_cache_dir", "")
        self.declare_parameter("vad_model", "fsmn-vad")
        self.declare_parameter("punc_model", "ct-punc")
        self.declare_parameter("use_vad", True)
        self.declare_parameter("use_punc", True)
        self.declare_parameter("device", "cpu")
        self.declare_parameter("batch_size_s", 300.0)
        self.declare_parameter("hotword", "")
        self.declare_parameter("preload", True)

        self.engine = FunAsrEngine(
            model=self.get_parameter("model_name").value,
            model_path=self.get_parameter("model_path").value,
            vad_model=self.get_parameter("vad_model").value,
            punc_model=self.get_parameter("punc_model").value,
            use_vad=self.get_parameter("use_vad").value,
            use_punc=self.get_parameter("use_punc").value,
            device=self.get_parameter("device").value,
            cache_dir=self.get_parameter("model_cache_dir").value,
            logger=self.get_logger(),
        )

        if self.get_parameter("preload").value:
            try:
                self.engine.load()
            except Exception as error:  # 加载失败不要退出节点，等服务请求时再报错
                self.get_logger().error(f"启动时加载模型失败: {error}")

        self.srv = self.create_service(
            Trigger,
            "/ai/recognize_audio",
            self.handle_recognize,
        )
        self.get_logger().info("ASR Service 节点已启动，等待请求...")

    def _check_audio_format(self, audio_path: str) -> None:
        try:
            info = probe_wav(audio_path)
        except Exception:
            self.get_logger().warning("不是标准 WAV 文件，交给 FunASR 自行解码")
            return

        self.get_logger().info(
            f"音频信息: {info['sample_rate']}Hz / {info['channels']}声道 / "
            f"{info['bit_depth']}bit / {info['duration']:.2f}s"
        )
        if (
            info["channels"] != 1
            or info["sample_rate"] != 16000
            or info["bit_depth"] != 16
        ):
            self.get_logger().warning(
                "音频格式非 16kHz/16bit/单声道，FunASR 会自动重采样，但准确率可能下降"
            )

    def handle_recognize(self, request, response):
        audio_path = self.get_parameter("audio_path").value
        output_path = self.get_parameter("output_path").value
        batch_size_s = self.get_parameter("batch_size_s").value
        hotword = self.get_parameter("hotword").value

        if not audio_path:
            response.success = False
            response.message = "audio_path 参数为空"
            self.get_logger().error(response.message)
            return response

        if not os.path.exists(audio_path):
            response.success = False
            response.message = f"录音文件不存在: {audio_path}"
            self.get_logger().error(response.message)
            return response

        try:
            self._check_audio_format(audio_path)
            text, elapsed = self.engine.recognize(
                audio_path, batch_size_s=batch_size_s, hotword=hotword
            )
            self.get_logger().info(
                f"识别成功（耗时 {elapsed:.2f}s）: {text}"
            )

            if output_path:
                output_directory = os.path.dirname(output_path)
                if output_directory:
                    os.makedirs(output_directory, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as output_file:
                    output_file.write(text)
                self.get_logger().info(f"结果已保存至: {output_path}")

            response.success = True
            response.message = text
        except Exception as error:
            response.success = False
            response.message = f"识别过程发生异常: {error}"
            self.get_logger().error(response.message)

        return response


def main(args=None):
    rclpy.init(args=args)
    node = ASRNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
