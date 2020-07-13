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

ubuntu_hdb_image = "/home/jungu/kafl/snapshots/ubuntu-16.04.4-x86_64/ram.qcow2"
ubuntu_image = "/home/jungu/kafl/snapshots/ubuntu-16.04.4-x86_64/overlay_0.qcow2"

#win7_image = "/home/jungu/kafl/snapshots/win7_x64/overlay_0.qcow2"
win7_image = "/home/jungu/kafl/images/win7_x64.qcow2"
win7_cdrom = "/home/jungu/kafl/images/7601_win7sp1_x64.iso"
win7_hdb_image = "/home/jungu/kafl/snapshots/win7_x64/ram.qcow2"

#win8_image = work_dir + "disk/win81_x64.qcow2"
#win8_cdrom = work_dir + "disk/Win8.1_English_x64.iso"
win8_image = work_dir + "snapshots/win8_x64/overlay_0.qcow2"
win8_hdb_image = work_dir + "snapshots/win8_x64/ram.qcow2"

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
    if (t_env.os == "ubuntu"):
        guest_args.append("-hdb")
        guest_args.append(ubuntu_hdb_image)
        guest_args.append("-hda")
        guest_args.append(ubuntu_image)
    elif (t_env.os == "win7"):
        guest_args.append("-hdb")
        guest_args.append(win7_hdb_image)
        guest_args.append("-hda");
        guest_args.append(win7_image);
        guest_args.append("-cdrom")
        guest_args.append(win7_cdrom)
        guest_args.append("-boot")
        guest_args.append("d")
    elif (t_env.os == "win8"):
        guest_args.append("-hdb")
        guest_args.append(win8_hdb_image)
        guest_args.append("-hda");
        guest_args.append(win8_image);
        #guest_args.append("-cdrom")
        #guest_args.append(win8_cdrom)
        #guest_args.append("-boot")
        #guest_args.append("d")
    else:
        print "Unknow os version"
        return;

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
    parser.add_argument("--os", type=str, default="win8", help="win7/ubuntu")
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

