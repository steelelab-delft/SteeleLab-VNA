#!/bin/sh

# Use this script to start the VNA Python server on the system that has the Zynq 7001 Soc (f.i. Red Pitaya).
# It is meant to be executed by cron. Example cron job:
# * * * * * /home/xilinx/slvna/project/server/sh/start_vna_server.sh >> /home/xilinx/slvna/log/vna_server.log 2>&1

alias date="date '+%Y-%m-%d %H:%M:%S'"

if [ "$(id -u)" != "0" ]; then
    echo "$(date) [SH] You must be root to run the VNA Python server"
    echo "$(date) [SH] since PYNQ requires \$(id -u) = 0; you have \$(id -u) = $(id -u)."
    echo "$(date) [SH] \`sudo\` unfortunately does not work."
    exit 1
fi

# Check if server port (defined in protocol.py) is currently in use.
DIR_WITH_PROTOCOL=$(dirname $(dirname $(readlink -f "$0")))
PORT=$(grep -E "TCP_PORT.*=" ${DIR_WITH_PROTOCOL}/protocol.py | sed "s/.*TCP_PORT.*=[^0-9]*//")
if lsof -Pi :"${PORT}" -sTCP:LISTEN -t >/dev/null; then
    exit 2 # Port in use; do not start server again.
fi

# Start VNA Python server-side program with priority -15.
echo "$(date) [SH] port :${PORT} not in use; starting Python server..."
. /etc/profile.d/xrt_setup.sh  # source xrt environment
nice -n -15 /usr/local/share/pynq-venv/bin/python "${DIR_WITH_PROTOCOL}"/main.py
