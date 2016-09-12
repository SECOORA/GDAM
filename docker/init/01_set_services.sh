#!/bin/bash
set -e
. /etc/profile

if [ ! -z "$RUN_GDAM" ]; then
    mkdir -p /etc/service/gdam
    cp docker/gdam /etc/service/gdam/run
    chmod +x /etc/service/gdam/run
fi

if [ ! -z "$RUN_GDAM2NC" ]; then
    mkdir -p /etc/service/gdam2nc
    cp docker/gdam2nc /etc/service/gdam2nc/run
    chmod +x /etc/service/gdam2nc/run
fi

if [ ! -z "$RUN_NC2FTP" ]; then
    mkdir -p /etc/service/nc2ftp
    cp docker/nc2ftp /etc/service/nc2ftp/run
    chmod +x /etc/service/nc2ftp/run
fi
