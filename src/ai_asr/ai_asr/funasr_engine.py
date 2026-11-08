"""FunASR 推理封装（纯 Python，不依赖 ROS 2）。

把「加载模型 + 识别音频」这两件事从 ROS 节点里拆出来，好处是：

* 阶段 2 可以先用 `scripts/test_funasr.py` 单独验证 FunASR 能不能识别中文，
  不需要装 ROS 2，出问题容易定位。
* 阶段 4 的 `ai_asr/asr_node.py` 只负责 ROS 2 的服务、参数和日志，
  识别逻辑全部复用这里的 :class:`FunAsrEngine`。

默认模型是达摩院 FunASR 的 `paraformer-zh`（离线非自回归中文模型），
配合 `fsmn-vad`（静音切分）和 `ct-punc`（标点恢复）使用，
这样长音频会被自动分段，输出文字自带逗号、句号。
"""

from __future__ import annotations

import os
import re
import time
import wave

# 汉字 / 中文标点区间。Paraformer 的字级别输出会在中文字之间带空格
# （例如 "你 好"），需要清理成 "你好"；但 "ROS 2" 这种英文+数字的空格必须保留。
_CJK = r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]"
_CJK_SPACE = re.compile(rf"(?<={_CJK})[ \t\u2581]+(?={_CJK})")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
# 逐字母拼读的大写缩写："R O S 2" -> "ROS 2"。要求是「单字母+空格」的连续串，
# 且后面紧跟一个孤立字母。副作用：英文里相邻的单字母词会被并起来
# （"A B is fine" -> "AB is fine"）；本项目的输入是中文语音，可以接受。
_SPELL_ACRONYM = re.compile(r"(?<![A-Za-z])(?:[A-Za-z] )+(?=[A-Za-z](?![A-Za-z]))")


def normalize_text(text: str) -> str:
    """整理 FunASR 原始输出：去掉分隔符 ``▁``、中文字之间的空格，合并拼读缩写。"""
    text = text.replace("\u2581", "")
    text = _CJK_SPACE.sub("", text)
    text = _SPELL_ACRONYM.sub(lambda match: match.group().replace(" ", ""), text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


def probe_wav(path: str) -> dict:
    """读取 WAV 头，返回采样率 / 声道 / 位深 / 时长，用于日志和格式检查。"""
    with wave.open(path, "rb") as audio_file:
        channels = audio_file.getnchannels()
        sample_rate = audio_file.getframerate()
        bit_depth = audio_file.getsampwidth() * 8
        duration = audio_file.getnframes() / float(sample_rate) if sample_rate else 0.0
    return {
        "channels": channels,
        "sample_rate": sample_rate,
        "bit_depth": bit_depth,
        "duration": duration,
    }


class FunAsrEngine:
    """封装 FunASR ``AutoModel``，提供 ``load()`` 与 ``recognize()``。"""

    def __init__(
        self,
        model: str = "paraformer-zh",
        model_path: str = "",
        vad_model: str = "fsmn-vad",
        punc_model: str = "ct-punc",
        use_vad: bool = True,
        use_punc: bool = True,
        device: str = "cpu",
        cache_dir: str = "",
        logger=None,
    ) -> None:
        """
        :param model: 模型名，会联网从 ModelScope 下载权重。
        :param model_path: 已下载好的本地模型目录；非空时优先于 ``model``。
        :param cache_dir: 权重缓存目录，写入 ``MODELSCOPE_CACHE``；留空用默认路径。
        :param logger: 任何带 ``info`` / ``warning`` / ``error`` 方法的对象，
            节点会传入 ROS 2 的 ``self.get_logger()``；为空则用 ``print``。
        """
        self.model = model_path.strip() if model_path else model.strip()
        if not self.model:
            raise ValueError("model 和 model_path 不能同时为空")

        self.vad_model = vad_model
        self.punc_model = punc_model
        self.use_vad = bool(use_vad)
        self.use_punc = bool(use_punc)
        self.device = device or "cpu"
        self.cache_dir = cache_dir
        self._logger = logger

        self.auto_model = None
        self.load_seconds = 0.0

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _log(self, level: str, message: str) -> None:
        if self._logger is not None:
            getattr(self._logger, level, self._logger.info)(message)
        else:
            print(f"[{level}] {message}")

    def _apply_cache_dir(self) -> None:
        """必须在 import funasr 之前设置缓存目录，否则权重会跑到 ~/.cache。"""
        if not self.cache_dir:
            return
        absolute = os.path.abspath(os.path.expanduser(self.cache_dir))
        os.makedirs(absolute, exist_ok=True)
        os.environ.setdefault("MODELSCOPE_CACHE", absolute)
        self._log("info", f"模型缓存目录: {absolute}")

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #
    def load(self):
        """加载模型；重复调用只会加载一次。"""
        if self.auto_model is not None:
            return self.auto_model

        self._apply_cache_dir()
        try:
            from funasr import AutoModel
        except ImportError as error:
            self._log(
                "error",
                f"导入 funasr 失败: {error}。请确认已激活虚拟环境并 pip install funasr。",
            )
            raise

        kwargs = {"model": self.model, "device": self.device, "disable_update": True}
        if self.use_vad and self.vad_model:
            kwargs["vad_model"] = self.vad_model
        if self.use_punc and self.punc_model:
            kwargs["punc_model"] = self.punc_model

        self._log("info", f"正在加载 FunASR 模型: {self.model} (device={self.device})")
        started = time.perf_counter()
        try:
            self.auto_model = AutoModel(**kwargs)
        except TypeError as error:
            # 老版本 FunASR 可能不认识 disable_update / device 参数
            self._log("warning", f"当前 FunASR 版本参数不兼容，重试精简参数: {error}")
            for key in ("disable_update", "device"):
                kwargs.pop(key, None)
            self.auto_model = AutoModel(**kwargs)

        self.load_seconds = time.perf_counter() - started
        self._log(
            "info",
            f"模型加载完成（vad={self.use_vad}, punc={self.use_punc}, "
            f"耗时 {self.load_seconds:.1f}s）",
        )
        return self.auto_model

    @staticmethod
    def _first_text(result) -> str:
        """FunASR 返回 list[dict]；兼容个别版本直接返回字符串列表。"""
        if not result:
            return ""
        item = result[0] if isinstance(result, (list, tuple)) else result
        if isinstance(item, dict):
            return str(item.get("text", ""))
        return str(item)

    def recognize(self, audio_path: str, batch_size_s: float = 300.0, hotword: str = ""):
        """识别一个音频文件，返回 ``(文字, 推理秒数)``。"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        model = self.load()
        kwargs: dict = {"input": audio_path, "batch_size_s": float(batch_size_s)}
        if hotword:
            kwargs["hotword"] = hotword

        started = time.perf_counter()
        result = model.generate(**kwargs)
        elapsed = time.perf_counter() - started

        text = normalize_text(self._first_text(result))
        if not text:
            self._log("warning", "模型返回空结果，请检查音频是否有声音 / 采样率是否 16kHz")
        return text, elapsed
