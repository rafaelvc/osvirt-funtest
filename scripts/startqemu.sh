#!/bin/bash

HDDIR=/home/rafael/osimage-autotest/repos/oshdimage
HDFILE=Mandriva-2011_default-install_i586.img
#ISODIR=/home/cabral/isotest
ISOFILE=Mandriva.2011.i586.1.iso

SERVERADDR=127.0.0.1
SERVERPORT=4445

[[ ! -d $HDDIR ]] && echo "HDDIR not found" && exit 1
#[[ ! -d $ISODIR ]] && echo "ISODIR not found" && exit 1

if [[ ! -f "$HDDIR/$HDFILE" ]]; then
    qemu-img create -f qcow2 "$HDDIR/$HDFILE" 8G
fi

#STD IMAGE
/usr/local/bin/qemu-system-x86_64 -m 1024 -qmp tcp:"$SERVERADDR":"$SERVERPORT",server -net nic,model=virtio,macaddr=52:54:00:13:34:56 -soundhw ac97 -vga cirrus -drive file="$HDDIR/$HDFILE",if=virtio -vnc "$SERVERADDR":99

# QMP
# /usr/local/bin/qemu-system-x86_64 -m 1024 -qmp tcp:"$SERVERADDR":"$SERVERPORT",server -net nic,model=virtio,macaddr=52:54:00:13:34:56 -soundhw ac97 -vga cirrus -S -drive file="$HDDIR/$HDFILE",if=virtio -boot cd -cdrom "$ISODIR/$ISOFILE" -vnc "$SERVERADDR":99

# MONITOR
# /usr/bin/qemu -m 1024 -monitor stdio -net nic,model=virtio,macaddr=52:54:00:13:34:56 -soundhw ac97 -vga cirrus -S -drive file="$HDDIR/hddisk",if=virtio -boot cd -cdrom "$ISODIR/Mandriva.2011.i586.1.iso" -vnc :99

# STD
# /usr/bin/qemu -m 1024 -net nic,model=virtio,macaddr=52:54:00:13:34:56 -soundhw ac97 -vga cirrus -S -drive file="$HDDIR/hddisk",if=virtio -boot cd -cdrom "$ISODIR/Mandriva.2011.i586.1.iso" -vnc :99

