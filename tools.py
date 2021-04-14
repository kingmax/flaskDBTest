# coding:utf-8
# author:jason.li
import os
import hashlib
import zipfile
import py7zr
import tempfile
import xml.etree.ElementTree as ET
from models import *

mat_source = 'E:\\mat'

"""
入库设计::
    1.将所有substance mats放入待处理目录，要求：
        a.分二层目录，第一层为材质分类(MatCategory)
        b.第二层目录即对应每个材质, 文件夹命名与材质名保持一致
        c.每个材质目录中至少有以下二个文件:
            1.{name}.sbsar (材质文件本身, 计算它的md5)
            2.{name}.png   (缩略图)
            可能存在的文件有:
            3.{name}.zip    (打包sbs格式, 无论有无dependencies均打包为zip, 方便仅下载一个zip文件即可)
        *所有目录与文件名均为英文小写、不得包含空格及特殊字符(下划线除外)
    2.
"""


def getSubFolderNames(root):
    return [fd for fd in os.listdir(root) if os.path.isdir(os.path.join(root, fd))]


def getCategory():
    return getSubFolderNames(mat_source)


def getMats(cat):
    root = os.path.join(mat_source, cat)
    return getSubFolderNames(root)


def zip_file(file):
    """zip *.sbs to *.zip"""
    head, tail = os.path.split(file)
    root, ext = os.path.splitext(file)
    out_zip = '%s.zip' % root
    # ZIP_LZMA 压缩率高一点比 ZIP_DEFLATED
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_LZMA) as myzip:
        myzip.write(file, arcname=tail)
    return out_zip


def get_mat_tags(sbs_or_sbsar_file):
    """get sbs or sbsar tags from *.sbs or *.sbsar file"""
    ret = []
    base, ext = os.path.splitext(sbs_or_sbsar_file)
    name = os.path.basename(base).lower()
    ext = ext.lower()

    if ext == '.sbs':
        print('get sbs tags')
        tree = ET.parse(sbs_or_sbsar_file)
        root = tree.getroot()
        found = False
        for graph in root.iter('graph'):
            if found:
                break
            identifier = graph.find('identifier')
            if identifier:
                _id = identifier.get('v')
                if _id and _id.lower() == name:
                    attributes = graph.find('attributes')
                    for a in attributes.iter('tags'):
                        v = a.get('v')
                        if v:
                            ret = v.split(';')
                            found = True
                            break

    elif ext == '.sbsar':
        print('get sbsar tags')
        tempDir = tempfile.gettempdir()
        target = ''
        with py7zr.SevenZipFile(sbs_or_sbsar_file, 'r') as z:
            ts = [f for f in z.getnames() if f.endswith('.xml')]
            print(ts)
            if not ts:
                print(f'[ERR]cannot get an .xml file')
                return []
            t = ts[0]
            z.extract(tempDir, t)
            target = os.path.join(tempDir, t)
        if os.path.exists(target):
            tree = ET.parse(target)
            root = tree.getroot()
            for graph in root.iter('graph'):
                pkgurl = graph.attrib.get('pkgurl')
                # pkgurl = "pkg://ceramic_foam_geometric"
                if pkgurl.endswith(name):
                    kws = graph.attrib.get('keywords')
                    if kws:
                        ret = kws.split(';')

    ret = [v.lower() for v in ret if v]
    return list(set(ret))


def get_md5(file):
    """if invalid return None"""
    try:
        return hashlib.md5(open(file, 'rb').read()).hexdigest()
    except Exception as ex:
        print(f'[GET_MD5] {ex}')
    return None


def check_get_mats():
    cats = getCategory()
    # print(f'MatCategory:{cats}')

    mats = dict.fromkeys(cats)

    for cat in cats:
        mats[cat] = getMats(cat)

    err_sbsar = []
    err_thumb = []
    sbs_zips = []
    matObjs = []
    for k, v in mats.items():
        print(f'{k}: {v}')
        for n in v:
            fd = os.path.join(mat_source, k, n)
            # print(fd)
            sbsar = os.path.join(fd, '%s.sbsar' % n)
            if not os.path.exists(sbsar):
                err_sbsar.append(sbsar)
                continue

            thumb = os.path.join(fd, '%s.png' % n)
            if not os.path.exists(thumb):
                err_thumb.append(thumb)

            # has sbs
            sbs = os.path.join(fd, '%s.sbs' % n)
            sbszip = os.path.join(fd, '%s.zip' % n)
            if os.path.exists(sbszip):
                sbs_zips.append(sbszip)

            if os.path.exists(sbs) and not os.path.exists(sbszip):
                sbszip = zip_file(sbs)
                if os.path.exists(sbszip):
                    sbs_zips.append(sbszip)
                    print(f'new sbszip: {sbszip}')

            tags = []
            if os.path.exists(sbs):
                print(f'get tags from sbs -> {sbs}')
                tags = get_mat_tags(sbs)
            elif os.path.exists(sbsar):
                print(f'get tags from sbsar -> {sbsar}')
                tags = get_mat_tags(sbsar)

            matObj = Material(name=n,
                              size=os.path.getsize(sbsar),
                              relative_path='%s\\%s' % (k, n),
                              has_sbszip=os.path.exists(sbszip),
                              )
            # addtion attrs
            matObj._cat = k
            matObj._tags = tags
            matObj._md5 = get_md5(sbsar)
            matObj._thumb = '%s\\%s.jpg' % (matObj.relative_path, matObj._md5)
            matObj.thumbnail = matObj._thumb
            matObjs.append(matObj)

    for e in err_sbsar:
        print(f'[ERR SBSAR] {e}')
    for e in err_thumb:
        print(f'[ERR THUMB] {e}')
    print(f'sbs count: {len(sbs_zips)}')
    for sbs in sbs_zips:
        print(f'[sbs] {sbs}')

    return matObjs


def put2db():
    mats = check_get_mats()
    for mat in mats:
        mat.setCategory(mat._cat)
        mat.setTags(mat._tags)
        mat.setMD5(mat._md5)
        db.session.add(mat)
    db.session.commit()
    print(mats)
    return mats


if __name__ == '__main__':
    put2db()
