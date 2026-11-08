# ASR models

这里放 **FunASR** 的模型权重，不再使用 Sherpa-ONNX 的 `tokens.txt` / `model.onnx`。

* 什么都不用手动下载：`AutoModel(model="paraformer-zh", ...)` 首次运行会自动联网取权重。
* 缓存位置由 `MODELSCOPE_CACHE` 决定，本项目的 launch/脚本把它指向 `models/asr/`，
  实际路径形如 `models/asr/iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/`。
* 想离线部署：在有网机器上下好后整目录拷过来，然后把节点参数 `model_path`
  指到该目录（非空时优先于 `model_name`）。
* 权重体积约 1GB 且属于二进制产物，已在根目录 `.gitignore` 里排除，不要提交到 GitHub。

用到的三个模型：

| 名称 | 作用 | 大小（约） |
| --- | --- | --- |
| `paraformer-zh` | 中文离线识别主干 | ~880MB |
| `fsmn-vad` | 静音检测 / 长音频分段 | ~1MB |
| `ct-punc` | 给结果加逗号、句号 | ~300MB |
