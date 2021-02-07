#!/usr/bin/env pypy
#coding:utf-8
from __future__ import unicode_literals
import os
import select
import shutil
import sys
import fcntl
import time
import subprocess
import commands
import prompt_toolkit
import argparse
import traceback
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

'''
environments of wrapper
'''
work_dir = "/home/da2din9o/kafl/"
exec_bin = "/bin/bash"

'''
environments of QEMU-PT
'''
qemu_exec_bin = work_dir + "kAFL-1/qemu-5.0.0/x86_64-softmmu/qemu-system-x86_64"
qemu_exec_bin_i386 = work_dir + "kAFL-1/qemu-5.0.0/i386-softmmu/qemu-system-i386"

kafl_ubuntu_img = {
    "hda_image" : "/home/jungu/kafl/snapshots/ubuntu-16.04.4-x86_64/overlay_0.qcow2",
    "hdb_image" : "/home/jungu/kafl/snapshots/ubuntu-16.04.4-x86_64/ram.qcow2"
}

#win7 x86
kafl_win7x86_img = {
    "hda_image" : work_dir + "snapshots/win7x86_user/overlay_0.qcow2",
    "cdrom" : "/home/da2din9o/timeplayer/disk/cn_windows_7_ultimate_x86_dvd_x15-65907.iso",
    "hdb_image" : work_dir + "snapshots/win7x86_user/ram_0.qcow2"
}

kafl_win7_img = {
    #win7_image = "/home/jungu/kafl/snapshots/win7_x64/overlay_0.qcow2"
    "hda_image" :  "/home/jungu/kafl/images/win7_x64.qcow2",
    "cdrom" : "/home/jungu/kafl/images/7601_win7sp1_x64.iso",
    "hdb_image" : "/home/jungu/kafl/snapshots/win7_x64/ram.qcow2",
}

kafl_win8_img = {
    #win8_image = work_dir + "disk/win81_x64.qcow2"
    #win8_cdrom = work_dir + "disk/Win8.1_English_x64.iso"
    "hda_image" : work_dir + "snapshots/win8_x64/overlay_0.qcow2",
    "hdb_image" : work_dir + "snapshots/win8_x64/ram_0.qcow2"
}

kafl_win8_user_img = {
    "hda_image" : work_dir + "snapshots/win8_x64_user/overlay_0.qcow2",
    "hdb_image" : work_dir + "snapshots/win8_x64_user/ram_0.qcow2"
}

kafl_win10x64_img = {
    #"hda_image" : "/home/da2din9o/timeplayer/disk/win10_x64_pre_19041.qcow2",
    "hda_image" : work_dir + "snapshots/win10x64/overlay_0.qcow2",
    "hdb_image" : work_dir + "snapshots/win10x64/ram_0.qcow2"
    #"cdrom" : "/home/da2din9o/timeplayer/disk/cn_windows_7_ultimate_x86_dvd_x15-65907.iso",
}

base_tap = "tap-"
base_shm = "sz02-shm_"
vnc_base_port = 15900
vnc_default_port = 5900
vnc_port = "15900"
#qemu_image = "/disk1/tpimages/ubuntu_14_04_x86_clean.qcow2"
#qemu_image = "/home/jungu/timeplayer/disk/ubuntu_14_04_x86_clean.qcow2"
#qemu_args = ["-m", "2048", "-vnc", "0:"+vnc_port+",password", "-monitor", "stdio", "-usbdevice", "tablet", "-netdev", "tap,ifname="+tap_dev+",id=net0,script=no,downscript=no", "-device", "rtl8139,netdev=net0"]
#qemu_args.insert(0, qemu_exec_bin)

#ls /dev/shm/""" + base + """$i &> /dev/null || break
def get_valid_pal_order(base):
    cmd = """
    for((i=1;i<100;i++))
    do
        ps -ef | grep qemu | grep pal_order=${i}, &> /dev/null || break
    done

    if [ $i -eq 100 ]
    then
        echo -1
    else
        echo $i
    fi
    """
    pal_order = subprocess.check_output(cmd, shell=True, executable='/bin/bash')
    pal_order = int(pal_order.strip())
    if pal_order > 0:
        return pal_order
    else:
        print "failed to get valid pal_order"
        sys.exit(1)

def get_valid_vnc_port(base_port):
    cmd = """
    for((i=1;i<10;i++))
    do
        netstat -ant | grep """ + str(base_port) +"""{i} &> /dev/null || break
    done

    if [ $i -eq 10 ]
    then
        echo -1
    else
        echo $i
    fi
    """
    order = subprocess.check_output(cmd, shell=True, executable='/bin/bash')
    order = int(order.strip())
    if order > 0:
        return base_port + order
    else:
        print "failed to get valid vnc port"
        sys.exit(1)

def get_valid_tap(base):
    cmd = """
    for((i=2;i<50;i++))
    do
        ip link list tap-$i | grep 'state DOWN' >/dev/null 2>&1  &&  x=$i && break
    done

    if [ $i -eq 50 ]
    then
        echo -1
    else
        echo $i
    fi
    """
    tap_dev = int(subprocess.check_output(cmd, shell=True, executable='/bin/bash').strip())
    if tap_dev > 0:
        return base + str(tap_dev)
    else:
        return None


def do_start_vm(t_env, sub_stdin=subprocess.PIPE, sub_stdout=subprocess.PIPE, sub_stderr=subprocess.PIPE, dp_args=None):
    '''
    Constructs the argument of panda
    '''
    qemu_replay    = "-replay"

    if t_env.tap:
        tap_dev = base_tap + str(t_env.tap)
    else:
        tap_dev = get_valid_tap(base_tap)

    if t_env.vnc_port:
        vnc_port = str(t_env.vnc_port);
    else:
        vnc_port = str(get_valid_vnc_port(vnc_base_port) - vnc_default_port);

    global qemu_exec_bin

    if (t_env.os == "ubuntu"):
        kafl_img = kafl_ubuntu_img
    elif (t_env.os == "win7x86"):
        kafl_img = kafl_win7x86_img
        qemu_exec_bin = qemu_exec_bin_i386
    elif (t_env.os == "win7"):
        kafl_img = kafl_win7_img
    elif (t_env.os == "win8"):
        kafl_img = kafl_win8_img
    elif (t_env.os == "win8_user"):
        kafl_img = kafl_win8_user_img
    elif (t_env.os == "win10"):
        kafl_img = kafl_win10x64_img
    else:
        print "Unknow os version"
        return;

    qemu_args = [qemu_exec_bin,
            #"-smp", str(t_env.smp),
            "-m", "2048",
            #"-vnc", "0:"+vnc_port+",password",
            "-monitor", "stdio",
            #"-serial", "mon:stdio",
            "-enable-kvm",
            "-netdev", "tap,ifname="+tap_dev+",id=net0,script=no,downscript=no",
            "-device", "rtl8139,netdev=net0"]

    qemu_args += [
            "-machine", "q35",
            "-device", "usb-tablet", "-machine", "usb=on,type=pc,accel=kvm"]

    guest_args = list(qemu_args)

    guest_args.append("-hdb")
    guest_args.append(kafl_img["hdb_image"])
    guest_args.append("-hda")
    guest_args.append(kafl_img["hda_image"])
    #guest_args.append("-cdrom")
    #guest_args.append(win7x86_cdrom)
    #guest_args.append("-boot")
    #guest_args.append("d")

    if dp_args:
        for arg in dp_args.split():
            guest_args.append(arg)

    """
    os.execvp(qemu_exec_bin, guest_args)
    """
    print "args of subprocess:", " ".join(guest_args)
    return subprocess.Popen(guest_args, stdin=sub_stdin, stdout=sub_stdout, stderr=sub_stderr)

def main():
    parser = argparse.ArgumentParser(description="Differential testing for accessmenting infoleak vul", add_help=False)
    parser.add_argument("--os", type=str, default="win10", help="win7/ubuntu")
    parser.add_argument("--tap", type=int, help="the serial number of tap-dev be used")
    parser.add_argument("--smp", type=int, default=4, help="the serial number of tap-dev be used")
    parser.add_argument("--vnc_port", type=int, help="vnc port of qemu")
    parser.add_argument("--gtk", type=bool, default=True, help="vnc port of qemu")
    parser.add_argument("--overlay", type=int, default=0, help="overlay file ordinal")
    parser.add_argument("--q_arg", type=str, help="arguments of qemu")

    t_env = parser.parse_args()

    r_instance = do_start_vm(t_env, None, None, None, dp_args=t_env.q_arg);
    r_instance.wait()
    return

if __name__ == "__main__":
    main()
    #print get_valid_pal_order(base_shm)

