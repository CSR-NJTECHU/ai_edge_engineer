#!/usr/bin/env bash
# 阶段 5：调用 ROS 2 服务，做端到端验证（音频 -> 文字 -> result.txt）。
# 前提：另一个终端里节点已经起来（ros2 launch ai_asr asr_launch.py）。
set -euo pipefail

ROS_RELEASE="${ROS_RELEASE:-lyrical}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/ai_edge_engineer}"
OUTPUT="${1:-$PROJECT_DIR/outputs/result.txt}"

# shellcheck disable=SC1091
source "/opt/ros/$ROS_RELEASE/setup.bash"
# shellcheck disable=SC1091
source "$PROJECT_DIR/install/setup.bash"

echo "==> 节点与服务状态"
ros2 node list | grep -E "asr_node" || echo "   ! 没看到 asr_node，请先启动节点"
ros2 service list | grep -E "/ai/recognize_audio" || echo "   ! 没看到服务"

echo
echo "==> 调用 /ai/recognize_audio"
ros2 service call /ai/recognize_audio std_srvs/srv/Trigger "{}"

echo
echo "==> $OUTPUT 内容"
[ -f "$OUTPUT" ] && cat "$OUTPUT" && echo || echo "   (结果文件不存在，检查 output_path 参数)"
