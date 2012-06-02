#!/bin/bash

tar -cvf - --exclude 'repos/*' --exclude='*.o' /home/rafael/osvirt-funtest | xz -c -9 - > osvir-funtest`date +'%d-%m-%y'`.tar.xz
