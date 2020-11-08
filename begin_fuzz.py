#!/usr/bin/env python3.8
#coding:utf-8
from __future__ import unicode_literals
import os
import select
import shutil
import sys
import fcntl
import time
import subprocess
import prompt_toolkit
import argparse
import traceback
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

'''
environments of wrapper
'''
root_dir = "/home/da2din9o/kafl/"
exec_bin = "/bin/bash"

'''
environments of kafl
'''
fuzzer = root_dir + "kAFL-1/kAFL-Fuzzer/kafl_fuzz.py"
info = root_dir + "kAFL-1/kAFL-Fuzzer/kafl_info.py"

#ram_file = root_dir + "snapshots/win8_x64/ram.qcow2"
ram_file = root_dir + "snapshots/win8_x64/ram"
overlay_dir = root_dir + "snapshots/win8_x64/"

agent_info = root_dir + "guest_bin/info.exe"
agent_fuzzee = root_dir + "win8/font/fuzzee/font_fuzzee.exe"

seed_dir = root_dir + "win8/font/corpora/"

working_dir_info = root_dir + "work_dir/"
working_dir_fuzz = root_dir + "win8/font/work_dir/"
#working_dir_fuzz = root_dir + "work_dir/"

base_tap = "tap-"
ram = "2048"

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
    pal_order = subprocess.check_output(cmd, shell=True, executable=exec_bin)
    pal_order = int(pal_order.strip())
    if pal_order > 0:
        return pal_order
    else:
        print("failed to get valid pal_order")
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
    tap_dev = subprocess.check_output(cmd, shell=True, executable=exec_bin)
    tap_dev = int(tap_dev.strip())
    if tap_dev > 0:
        return base + str(tap_dev)
    else:
        return None

"""
@dq_args: Arguments of QEMU
@dp_args: Arguments of PANDA
./kafl_info.py -work_dir ~/kafl/work_dir -vm_dir ~/kafl/snapshots/win8_x64/ -vm_ram ~/kafl/snapshots/win8_x64/ram.qcow2 -agent ~/kafl/guest_bin/info.exe -mem 2048 -v -tp
"""
def do_fuzz(t_env, sub_stdin=subprocess.PIPE, sub_stdout=subprocess.PIPE, sub_stderr=subprocess.PIPE):
    '''
    Constructs the argument of kafl
    '''
    if t_env.tap:
        tap_dev = base_tap + str(t_env.tap)
    else:
        tap_dev = get_valid_tap(base_tap)

    kafl_args = []
    if t_env.info:
        agent = agent_info
        exec_bin = info
        working_dir = working_dir_info
    else:
        exec_bin = fuzzer
        agent = agent_fuzzee
        working_dir = working_dir_fuzz

    kafl_args = [
            exec_bin,
            "-vm_ram", ram_file,
            "-vm_dir", overlay_dir,
            "-work_dir", working_dir,
            "-agent", agent,
            "-mem", "2048",
            ]

    if not t_env.info:
        kafl_args += ["-seed_dir", seed_dir]

    kafl_args.append("-tp")
    if t_env.args:
        kafl_args += t_env.args.split()

    print("args of subprocess:", " ".join(kafl_args))
    return subprocess.Popen(kafl_args, stdin=sub_stdin, stdout=sub_stdout, stderr=sub_stderr)

def main():
    parser = argparse.ArgumentParser(description="Wrapper for kafl in timeplayer environment", add_help=False)
    parser.add_argument("--info", action='store_true', default=False, help="Verbose debug information")
    parser.add_argument("--args", type=str, help="Extra arguments of kafl")
    parser.add_argument("--tap", type=int, help="the serial number of tap-dev be used")

    t_env = parser.parse_args()

    r_instance = do_fuzz(t_env, None, None, None);
    r_instance.wait()
    return


if __name__ == "__main__":
    main()
    #print get_valid_pal_order(base_shm)

