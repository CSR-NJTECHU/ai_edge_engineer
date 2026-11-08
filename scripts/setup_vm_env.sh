#!/usr/bin/env bash
# 在 Ubuntu 26.04 虚拟机里一次性搭好「ROS 2 Lyrical + FunASR」环境（阶段 1 + 阶段 2 的准备）。
#
#   bash scripts/setup_vm_env.sh              # 默认走清华镜像，国内速度快
#   ROS2_APT_MIRROR=http://packages.ros.org/ros2/ubuntu bash scripts/setup_vm_env.sh
#
# 脚本可重复执行（幂等）。装完请重开终端，或手动 source 下面两个文件：
#   /opt/ros/lyrical/setup.bash
#   ~/ai_edge_engineer/.venv/bin/activate
set -euo pipefail

ROS_RELEASE="${ROS_RELEASE:-lyrical}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/ai_edge_engineer}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
# 国内建议: https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu
ROS2_APT_MIRROR="${ROS2_APT_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu}"
PIP_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
# CPU 版 PyTorch 体积小很多；有 NVIDIA 显卡按 https://pytorch.org 换 index
TORCH_INDEX="${TORCH_INDEX:-https://download.pytorch.org/whl/cpu}"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

step "0/6 基本信息"
. /etc/os-release
echo "系统  : $PRETTY_NAME"
echo "架构  : $(dpkg --print-architecture)"
echo "Python: $(python3 --version 2>&1)"
echo "项目  : $PROJECT_DIR"

step "1/6 系统依赖与 locale"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  locales ca-certificates curl gnupg lsb-release git \
  python3-dev python3-pip python3-venv python3-setuptools build-essential \
  ffmpeg libsndfile1
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

step "2/6 ROS 2 软件源"
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] $ROS2_APT_MIRROR $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
sudo apt-get update

step "3/6 ROS 2 $ROS_RELEASE + colcon + rosdep"
sudo apt-get install -y --no-install-recommends \
  "ros-$ROS_RELEASE-ros-base" \
  python3-colcon-common-extensions python3-rosdep
# ros-base 已含 ros2cli / rclpy / std_srvs，下面这些是调试常用补充
sudo apt-get install -y --no-install-recommends \
  "ros-$ROS_RELEASE-rviz2" 2>/dev/null || echo "(rviz2 可选，跳过)"

step "4/6 初始化 rosdep"
[ -f /etc/ros/rosdep/sources.list.d/20-default.list ] || sudo rosdep init || true
rosdep update --rosdistro "$ROS_RELEASE" || echo "(rosdep update 失败可稍后重试，不影响本包)"

step "5/6 Python 虚拟环境 + FunASR"
if [ ! -d "$VENV_DIR" ]; then
  # --system-site-packages 是关键：venv 里才能同时 import 到 apt 装的 rclpy 和 pip 装的 funasr
  python3 -m venv --system-site-packages "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install --index-url "$TORCH_INDEX" torch torchaudio
python -m pip install --index-url "$PIP_INDEX" -r "$PROJECT_DIR/requirements.txt"

step "6/6 写入 ~/.bashrc 自动加载"
if ! grep -q "opt/ros/$ROS_RELEASE/setup.bash" "$HOME/.bashrc"; then
  {
    echo ""
    echo "# >>> ai_edge_engineer: ROS 2 + FunASR >>>"
    echo "source /opt/ros/$ROS_RELEASE/setup.bash"
    echo "source $VENV_DIR/bin/activate"
    echo "# <<< ai_edge_engineer <<<"
  } >>"$HOME/.bashrc"
  echo "已追加到 ~/.bashrc，重开终端生效"
fi

step "验证"
# shellcheck disable=SC1091
source "/opt/ros/$ROS_RELEASE/setup.bash"
python -c "import rclpy; print('rclpy OK ->', rclpy.__file__)"
python -c "import torch, torchaudio; print('torch', torch.__version__, '/ torchaudio', torchaudio.__version__)"
python -c "import funasr; print('funasr', funasr.__version__)"
echo ""
echo "环境就绪。下一步: python3 scripts/test_funasr.py"
