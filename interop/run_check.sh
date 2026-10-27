#!/bin/bash
# Route-check a contact plan in ION and HDTN (Docker images interop/ion and interop/hdtn
# from bpv7-interop-matrix).
#
#   interop/run_check.sh <plan dir> <step seconds>
#
# Queries Earth (1) -> rover (200) and rover -> Earth every <step> seconds over the plan,
# then compares both with the plan in interop/check_routes.py.
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
PLAN=$1 STEP=$2
OUT=$PLAN/route_check
rm -rf "$OUT" && mkdir -p "$OUT"
HOST=$(pwd -W 2>/dev/null || pwd)
END=$(python -c "import json;print(int(max(c['end_s'] for c in json.load(open('$PLAN/contacts.json'))['contacts'])))")
TIMES=$(seq 0 "$STEP" "$END" | tr '\n' ' ')

# HDTN: its CGR library, as its router calls it
docker run --rm -v "$HOST:/m" --entrypoint bash interop/hdtn -c "
  cd /opt/HDTN
  I='-Icommon/cgr/include -Ibuild/common/cgr -Icommon/logger/include -Ibuild/common/logger -Icommon/util/include -Ibuild/common/util'
  g++ -std=c++17 -O1 \$I /m/interop/hdtn_route.cpp -o /tmp/r build/common/cgr/libcgr_lib.a \
    build/common/logger/liblog_lib.a build/common/util/libhdtn_util.a -lboost_filesystem -lboost_log \
    -lboost_log_setup -lboost_thread -lboost_regex -lboost_system -lpthread
  for sd in '1 200' '200 1'; do
    set -- \$sd
    /tmp/r /m/$PLAN/hdtn.json \$1 \$2 $TIMES 2>/dev/null | sed \"s/^/\$1 \$2 /\"
  done" > "$OUT/hdtn.txt"

# ION: a fresh node per query (cgrfetch on a node that has already answered one query
# returns no routes: its trace reports every contact as already visited), the plan loaded
# at T0, then cgrfetch for the send time
ion_queries() { # local neighbor dest
  docker run --rm -v "$HOST:/m" --entrypoint bash interop/ion -c "
    apt-get update -qq > /dev/null && apt-get install -y -qq graphviz > /dev/null 2>&1
    for t in $TIMES; do
      killm > /dev/null 2>&1; rm -rf /tmp/w; mkdir /tmp/w && cd /tmp/w
      printf '1 $1 %s\ns\nm horizon +0\n' \"''\" > n.ionrc
      ionadmin n.ionrc > /dev/null 2>&1
      t0=\$(date +%s); echo \$t0 > /m/$OUT/ion_$1_$3_\$t.t0
      ionadmin /m/$PLAN/ion.rc > /dev/null
      printf '1\na scheme ipn ipnfw ipnadminep\na endpoint ipn:$1.1 x\na protocol udp 1400 100\na induct udp 127.0.0.1:4556 udpcli\na outduct udp 127.0.0.1:4557 udpclo\ns\n' > n.bprc
      bpadmin n.bprc > /dev/null
      echo 'a plan $2 udp/127.0.0.1:4557' | ipnadmin > /dev/null
      sleep 1
      off=\$(( t0 + t - \$(date +%s) )); [ \$off -lt 0 ] && off=0
      timeout 60 cgrfetch -q -t \$off -e \$(( off + 216000 )) -d udp:127.0.0.1:4557 -o /m/$OUT/ion_$1_$3_\$t.json $3 > /dev/null 2>&1 || true
    done
    killm > /dev/null 2>&1 || true"
}
ion_queries 1 100 200
ion_queries 200 100 1
python interop/check_routes.py "$PLAN" "$OUT" "$OUT/hdtn.txt"
