import glob
import os

from setuptools import setup

package_name = "ai_asr"
share_directory = os.path.join("share", package_name)

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        (
            os.path.join("share", "ament_index", "resource_index", "packages"),
            ["resource/" + package_name],
        ),
        (share_directory, ["package.xml"]),
        (os.path.join(share_directory, "launch"), glob.glob("launch/*.py")),
    ],
    # 运行时依赖：ROS 2 侧由 package.xml 描述，Python 侧由 requirements.txt 描述。
    # sherpa-onnx 已经换成 FunASR(paraformer-zh)。
    install_requires=[
        "setuptools",
        "numpy",
        "funasr",
        "torch",
        "torchaudio",
        "modelscope",
        "soundfile",
    ],
    zip_safe=True,
    maintainer="chen-shurui",
    maintainer_email="chen-shurui@todo.todo",
    description="ROS 2 ASR node: FunASR paraformer-zh offline Chinese speech-to-text",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "asr_node = ai_asr.asr_node:main",
        ],
    },
)
