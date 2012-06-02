#!/bin/bash
skill -9 ./startqemu.sh
kill -9 `pidof qemu-system-x86_64`
rm -rf var/osimage-autotest/*
