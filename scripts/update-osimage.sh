#!/bin/bash

cp osvirt-funtest/osvirt-funtest.cfg . 
rm -rf osvirt-funtest
tar -xJvf $1 
mv home/cabral/osvirt-funtest .
rm -rf home/cabral
rm -rf home
cp osvirt-funtest.cfg osvirt-funtest/
# enable mounting by any user without root password
# /usr/share/polkit-1/actions/org.freedesktop.udisks.policy
# <action id="org.freedesktop.udisks.filesystem-mount-system-internal"> 
# Look down a few lines under "default" and change "auth_admin" to "yes" like this.
# <allow_active>yes</allow_active>
udisks --mount /dev/sdb1
rm -rf osvirt-funtest/repos
ln -s /media/2C3C49753C493ADA/repos osvirt-funtest/repos
sed -i 's/cabral/rafael/' osvirt-funtest/osimage_autotest/testengine.py
sed -i 's/\/cabral/\/rafael/' osvirt-funtest/web/osvirt-funtest-web.py

KVM_LOADED=`/sbin/lsmod | grep kvm`
[ '$KVM_LOADED' == '' ] && sudo modprobe kvm_intel
