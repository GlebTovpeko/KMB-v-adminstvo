#!/bin/bash
echo "TIMESTAMP | CODE | LATENCY" && while true; do start=$(date +%s%3N); code=$(curl -o /dev/null -s -w "%{http_code}" https://ya.ru); rt=$(($(date +%s%3N)-start)); echo "$(date '+%H:%M:%S') |  $code | ${rt}ms"; sleep 1; done
