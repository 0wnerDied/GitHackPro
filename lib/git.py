#!/usr/bin/env python
# coding:utf-8

"""
Copyright (c) 2017 BugScan (http://www.bugscan.net)
Copyright (C) 2024 0wnerDied <z1281552865@gmail.com>
See the file 'LICENCE' for copying permission
"""

import binascii
import collections
import mmap
import os
import re
import struct
import subprocess
import zlib
from lib.common import (
    check,
    mkdir_p,
    readFile,
    writeFile,
)
from lib.data import (
    paths,
    logger,
    target,
)
from lib.request import (
    request_data,
    wget,
)
from lib.settings import DEBUG


def init():
    logger.info("Initialize Git")
    cmd = ["git", "config", "--global", "init.defaultBranch", "master"]
    ret = subprocess.call(cmd)
    if ret != 0:
        logger.warning("Configure Error")
        return False
    process = subprocess.Popen(
        ["git", "init", paths.GITHACK_DIST_TARGET_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()
    if stderr:
        logger.error(f"Initialize Git Error: {stderr.decode('utf-8')}")


def clone():
    logger.info("Clone")
    cmd = ["git", "clone", target.TARGET_GIT_URL, paths.GITHACK_DIST_TARGET_PATH]
    ret = subprocess.call(cmd)
    if ret != 0:
        mkdir_p(paths.GITHACK_DIST_TARGET_PATH)
        logger.warning("Clone Error")
        return False
    return True


def valid_git_repo():
    logger.info("Valid Repository")
    process = subprocess.Popen(
        ["git", "-C", paths.GITHACK_DIST_TARGET_PATH, "reset"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()
    if stderr:
        logger.info("Valid Repository Fail")
        return False
    logger.success("Valid Repository Success")
    return True


def clone_from_list(name):
    if name[0] == "/":
        name = name[1:]
    tmppath = os.path.join(paths.GITHACK_DIST_TARGET_GIT_PATH, name)
    if tmppath[-1] == "/" and not os.path.exists(tmppath):
        os.makedirs(tmppath)
    if not os.path.isdir(tmppath):
        readorwget(name)
        return
    page = request_data(f"{target.TARGET_GIT_URL}{name}")
    files = re.findall(r'<a href="(.+?)"', page, re.M | re.I)
    for f in files:
        if f == "../":
            continue
        newname = os.path.join(name, f)
        clone_from_list(newname)


def refresh_files():
    readorwget("packed-refs", True)
    readorwget("config", True)
    readorwget("HEAD", True)


def clone_from_cache():
    logger.info("Cache files")
    refresh_files()
    readorwget("COMMIT_EDITMSG")
    readorwget("ORIG_HEAD")
    readorwget("description")
    readorwget("info/exclude")
    readorwget("FETCH_HEAD")
    readorwget("refs/heads/master")
    readorwget("refs/remote/master")
    refs = readorwget("HEAD")[5:-1]
    readorwget("index")
    readorwget("logs/HEAD", True)
    HEAD_HASH = readorwget(refs.decode())
    readorwget(f"logs/refs/heads/{refs.split(b'/')[-1].decode()}")

    if HEAD_HASH:
        cache_commits(HEAD_HASH.replace(b"\n", b""))

    readorwget("logs/refs/remote/master")
    readorwget("logs/refs/stash")
    STASH_HASH = readorwget("refs/stash")
    if STASH_HASH:
        cache_commits(STASH_HASH.replace(b"\n", b""))

    cache_objects()


def readorwget(filename, refresh=False):
    filepath = os.path.join(paths.GITHACK_DIST_TARGET_GIT_PATH, filename)
    if refresh or not os.path.exists(filepath):
        logger.info(filename)
        wget(filename)
    else:
        if DEBUG:
            logger.info(f"[Skip] File {filename} already exists.")
    if not os.path.exists(filepath):
        return None
    return readFile(filepath)


def parse_refs(data):
    try:
        fetch_heads = re.findall(r"([a-z0-9]{40})\trefs/heads/(.+?)\n", data, re.M)
        FETCH_HEAD = ""
        for index in fetch_heads:
            writeFile(
                os.path.join(
                    paths.GITHACK_DIST_TARGET_GIT_PATH,
                    f"refs/remotes/origin/{index[1]}",
                ),
                f"{index[0]}\n",
            )
            FETCH_HEAD += f"{index[0]}\tnot-for-merge\t'{index[1]}' of {target.TARGET_GIT_URL[:-5]}\n"

        config = f"""[core]
        repositoryformatversion = 0
        filemode = true
        bare = false
        logallrefupdates = true
        ignorecase = true
        precomposeunicode = true
    [remote "origin"]
        url = {target.TARGET_GIT_URL[:-1]}
        fetch = +refs/heads/*:refs/remotes/origin/*
    """
        writeFile(os.path.join(paths.GITHACK_DIST_TARGET_GIT_PATH, "config"), config)
    except Exception as e:
        logger.warning("Parse refs Fail")


def clone_pack():
    logger.info("Clone pack data.")
    packdata = readorwget("objects/info/packs")
    if packdata:
        packs = re.findall(r"P pack-([a-z0-9]{40}).pack\n", packdata)
        for pack in packs:
            readorwget(f"objects/pack/pack-{pack}.idx")
            readorwget(f"objects/pack/pack-{pack}.pack")
    logger.info("Clone pack data end.")


def cache_commits(starthash):
    logger.info("Fetch Commit Objects")
    indexhash = [starthash]
    while indexhash:
        tmp = []
        for i in indexhash:
            if DEBUG:
                logger.info(f"Fetch Commit Objects: {i}")
            data = get_objects(i)
            try:
                objdata = zlib.decompress(data)
                if objdata[:4] == b"tree":
                    trees = parse_tree(objdata[objdata.find(b"\x00") + 1 :])
                    tmp.extend(trees)
            except Exception as e:
                pass
            (obj, parents) = parse_commit(data, i)
            if parents:
                tmp.extend(parents)
            if obj is None:
                continue
            data = get_objects(obj)
            try:
                objdata = zlib.decompress(data)
                if objdata[:4] == b"tree":
                    trees = parse_tree(objdata[objdata.find(b"\x00") + 1 :])
                    tmp.extend(trees)
            except Exception as e:
                pass
        indexhash = tmp
    logger.info("Fetch Commit Objects End")


def parse_tree(text, strict=False):
    count = 0
    retVal = []
    l = len(text)
    while count < l:
        mode_end = text.index(b" ", count)
        mode_text = text[count:mode_end]
        if strict and mode_text.startswith(b"0"):
            logger.warning(f"Invalid mode '{mode_text}'")
            break
        try:
            mode = int(mode_text, 8)
        except ValueError:
            logger.warning(f"Invalid mode '{mode_text}'")
            break
        name_end = text.index(b"\0", mode_end)
        name = text[mode_end + 1 : name_end]
        count = name_end + 21
        sha = text[name_end + 1 : count]
        if len(sha) != 20:
            logger.warning("Sha has invalid length")
            break
        hexsha = sha_to_hex(sha)
        retVal.append(hexsha)
    return retVal


def sha_to_hex(sha):
    hexsha = binascii.hexlify(sha)
    assert len(hexsha) == 40, f"Incorrect length of sha1 string: {len(hexsha)}"
    return hexsha


def parse_commit(data, commithash):
    obj = None
    try:
        de_data = zlib.decompress(data)
        m = re.search(
            rb"commit \d+?\x00tree ([a-z0-9]{40})\n", de_data, re.M | re.S | re.I
        )
        if m:
            obj = m.group(1)
            if obj:
                logger.info("Get obj from commit : %s" % (obj.decode()))
            else:
                logger.info()
        parents = re.findall(b"parent ([a-z0-9]{40})\n", de_data, re.M | re.S | re.I)
    except Exception as e:
        parents = []
        if DEBUG:
            logger.warning(f"Decompress Commit({commithash}) Fail")
    return (obj, parents)


def get_objects(objhash):
    folder = os.path.join(
        paths.GITHACK_DIST_TARGET_GIT_PATH, f"objects/{objhash[:2].decode()}/"
    )
    if not os.path.exists(folder):
        mkdir_p(folder)
    data = readorwget(f"objects/{objhash[:2].decode()}/{objhash[2:].decode()}")
    return data


def cache_objects():
    for entry in parse_index(os.path.join(paths.GITHACK_DIST_TARGET_GIT_PATH, "index")):
        if "sha1" in entry.keys():
            try:
                data = get_objects(entry["sha1"])
                if data:
                    data = zlib.decompress(data)
                    data = re.sub(rb"blob \d+\00", b"", data)
                    target_dir = os.path.join(
                        paths.GITHACK_DIST_TARGET_PATH, os.path.dirname(entry["name"])
                    )
                    if target_dir and not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    with open(
                        os.path.join(paths.GITHACK_DIST_TARGET_PATH, entry["name"]),
                        "wb",
                    ) as f:
                        f.write(data)
            except Exception as e:
                logger.warning(f"Clone Objects({entry['sha1']}) Fail")


def parse_index(filename, pretty=True):
    """
    Analyze the index
    https://github.com/git/git/blob/master/Documentation/technical/index-format.txt
    """
    with open(filename, "rb") as o:
        f = mmap.mmap(o.fileno(), 0, access=mmap.ACCESS_READ)

        def read(format):
            # "All binary numbers are in network byte order."
            # Hence "!" = network order, big endian
            format = "! " + format
            bytes = f.read(struct.calcsize(format))
            return struct.unpack(format, bytes)[0]

        index = collections.OrderedDict()

        # 4-byte signature, b"DIRC"
        index["signature"] = f.read(4).decode("ascii")
        check(index["signature"] == "DIRC", "Not a Git index file")

        # 4-byte version number
        index["version"] = read("I")
        check(index["version"] in {2, 3}, f"Unsupported version: {index['version']}")

        # 32-bit number of index entries, i.e. 4-byte
        index["entries"] = read("I")

        yield index

        for n in range(index["entries"]):
            entry = collections.OrderedDict()

            entry["entry"] = n + 1

            entry["ctime_seconds"] = read("I")
            entry["ctime_nanoseconds"] = read("I")
            if pretty:
                entry["ctime"] = entry["ctime_seconds"]
                entry["ctime"] += entry["ctime_nanoseconds"] / 1000000000
                del entry["ctime_seconds"]
                del entry["ctime_nanoseconds"]

            entry["mtime_seconds"] = read("I")
            entry["mtime_nanoseconds"] = read("I")
            if pretty:
                entry["mtime"] = entry["mtime_seconds"]
                entry["mtime"] += entry["mtime_nanoseconds"] / 1000000000
                del entry["mtime_seconds"]
                del entry["mtime_nanoseconds"]

            entry["dev"] = read("I")
            entry["ino"] = read("I")

            # 4-bit object type, 3-bit unused, 9-bit unix permission
            entry["mode"] = read("I")
            if pretty:
                entry["mode"] = f"{entry['mode']:06o}"

            entry["uid"] = read("I")
            entry["gid"] = read("I")
            entry["size"] = read("I")

            entry["sha1"] = binascii.hexlify(f.read(20)).decode("ascii")
            entry["flags"] = read("H")

            # 1-bit assume-valid
            entry["assume-valid"] = bool(entry["flags"] & (0b10000000 << 8))
            # 1-bit extended, must be 0 in version 2
            entry["extended"] = bool(entry["flags"] & (0b01000000 << 8))
            # 2-bit stage (?)
            stage_one = bool(entry["flags"] & (0b00100000 << 8))
            stage_two = bool(entry["flags"] & (0b00010000 << 8))
            entry["stage"] = stage_one, stage_two
            # 12-bit name length, if the length is less than 0xFFF (else, 0xFFF)
            namelen = entry["flags"] & 0xFFF

            # 62 bytes so far
            entrylen = 62

            if entry["extended"] and (index["version"] == 3):
                entry["extra-flags"] = read("H")
                # 1-bit reserved
                entry["reserved"] = bool(entry["extra-flags"] & (0b10000000 << 8))
                # 1-bit skip-worktree
                entry["skip-worktree"] = bool(entry["extra-flags"] & (0b01000000 << 8))
                # 1-bit intent-to-add
                entry["intent-to-add"] = bool(entry["extra-flags"] & (0b00100000 << 8))
                entrylen += 2

            if namelen < 0xFFF:
                entry["name"] = f.read(namelen).decode("utf-8", "replace")
                entrylen += namelen
            else:
                name = []
                while True:
                    byte = f.read(1)
                    if byte == b"\x00":
                        break
                    name.append(byte)
                entry["name"] = b"".join(name).decode("utf-8", "replace")
                entrylen += 1

            padlen = (8 - (entrylen % 8)) or 8
            nuls = f.read(padlen)
            if set(nuls) != {0}:
                raise ValueError("padding contained non-NUL")

            yield entry

        f.close()
