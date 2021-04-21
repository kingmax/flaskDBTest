# coding:utf-8
# author:jason.li
import os
import hashlib
import zipfile
import py7zr
import tempfile
import xml.etree.ElementTree as ET
from models import *

# mat_source = 'E:\\mat'
mat_source = 'E:\\SubstanceSourceMaterial'

"""
Material入库设计::
    1.将所有substance mats放入待处理目录，要求：
        a.分二层目录，第一层为材质分类(MatCategory)
        b.第二层目录即对应每个材质, 文件夹命名与材质名保持一致
        c.每个材质目录中至少有以下二个文件:
            1.{name}.sbsar (材质文件本身, 计算它的md5)
            2.{name}.png   (缩略图)
            可能存在的文件有:
            3.{name}.zip    (打包sbs格式, 无论有无dependencies均打包为zip, 方便仅下载一个zip文件即可)
        *所有目录与文件名均为英文小写、不得包含空格及特殊字符(下划线除外)
        
    2.指定资源根目录,检查是否合规(可以同时计算md5,以便移除重复资源文件)
    
    3.获取有效资源列表,生成缩略图 (同时返回无效资源列表,包括与之对应的无效原因(是否缺少文件、是否重复等等))
    
    4.写入数据库
    
    5.可选copy资源到公司美术资源库目录 (或者部署网站的时候再手动处理)
"""


def normalize_folder_name(root_folder, only_remove_chars=[]):
    """默认移除路径中所有特殊字符(not isalnum),
    如果only_remove_chars不为空[],则仅移除指定的字符
    """
    # https://stackoverflow.com/questions/20535705/recursively-renaming-directory-file-structures-on-a-local-file-system
    ndict = {'dirs': '', 'files': ''}
    topdown = {'dirs': False, 'files': True}
    mode = 'dirs'
    # for root, dirs, files in os.walk(STATIC_FOLDER_TEXTURES, topdown=False):
    for root, ndict['dirs'], ndict['files'] in os.walk(root_folder, topdown[mode]):
        for name in ndict[mode]:
            new_name = ''
            if only_remove_chars:
                new_name = ''.join([c for c in name if c not in only_remove_chars])
            elif not name.isalnum():
                new_name = ''.join([c for c in name if c.isalnum()])
            if new_name:
                print(f'{os.path.join(root, name)}\n{os.path.join(root, new_name)}\n')
                os.rename(os.path.join(root, name), os.path.join(root, new_name))


def getSubFolderNames(root):
    return [fd.lower() for fd in os.listdir(root) if os.path.isdir(os.path.join(root, fd))]


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
            if identifier is not None:
                _id = identifier.get('v')
                if _id and _id.lower() == name:
                    attributes = graph.find('attributes')
                    if attributes is not None:
                        tags = attributes.find('tags')
                        if tags is not None:
                            v = tags.get('v')
                            if v:
                                ret = v.split(';')
                                found = True
                    # for a in attributes.iter('tags'):
                    #     v = a.get('v')
                    #     if v:
                    #         ret = v.split(';')
                    #         found = True
                    #         break

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
            matObj.md5 = get_md5(sbsar)
            # 将缩略图放入对应category目录下
            matObj._thumb = '%s\\%s.jpg' % (k, matObj.md5)
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
        if MatMD5.query.filter_by(md5=mat.md5).first():
            print(f'[EXIST] {mat.md5} {mat}')
            continue
        mat.setCategory(mat._cat)
        mat.setTags(mat._tags)
        mat.setMD5(mat.md5)
        db.session.add(mat)
    db.session.commit()
    print(mats)
    return mats


if __name__ == '__main__':
    normalize_folder_name(mat_source, only_remove_chars=[' ', '#', '-', "'"])

    # mats = put2db()
    # print(len(mats))
    # get_mat_tags(r'E:\mat\ceramic\ceramic_foam\ceramic_foam.sbs')
