# coding:utf-8
# author:jason.li
import os
import hashlib
import zipfile

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


def check():
    cats = getCategory()
    # print(f'MatCategory:{cats}')

    mats = dict.fromkeys(cats)

    for cat in cats:
        mats[cat] = getMats(cat)

    err_sbsar = []
    err_thumb = []
    sbs_zips = []
    for k, v in mats.items():
        print(f'{k}: {v}')
        for n in v:
            fd = os.path.join(mat_source, k, n)
            # print(fd)
            sbsar = os.path.join(fd, '%s.sbsar' % n)
            if not os.path.exists(sbsar):
                err_sbsar.append(sbsar)

            thumb = os.path.join(fd, '%s.png' % n)
            if not os.path.exists(thumb):
                err_thumb.append(thumb)

            # has sbs
            sbs = os.path.join(fd, '%s.sbs' % n)
            sbszip = os.path.join(fd, '%s.zip' % n)
            if os.path.exists(sbszip):
                sbs_zips.append(sbszip)

            if os.path.exists(sbs) and not os.path.exists(sbszip):
                new_zip = zip_file(sbs)
                if os.path.exists(new_zip):
                    sbs_zips.append(new_zip)
                    print(f'new sbszip: {new_zip}')

    for e in err_sbsar:
        print(f'[ERR SBSAR] {e}')
    for e in err_thumb:
        print(f'[ERR THUMB] {e}')
    print(f'sbs count: {len(sbs_zips)}')
    for sbs in sbs_zips:
        print(f'[sbs] {sbs}')


if __name__ == '__main__':
    check()
