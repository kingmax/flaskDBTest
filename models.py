# coding:utf-8
# author: jason.li

from app import db


######################################## Materials
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

# 定义顶级资源分类, 即网站顶级导航栏目, 注意定义顺序
ROOT_FOLDERS = [
    ('index', u'首页'),
    # 以下为真实存在的文件夹名, 不能为中文, 网站显示cn_name
    ('texture', u'贴图'),
    ('material', u'材质'),
    ('model', u'模型'),
    ('tool', u'工具'),
    ('reference', u'参考'),
    ('other', u'其它')
]


class C(object):
    """为Model类注入toDict方法"""

    def toDict(self):
        """convert db table row to dict"""
        d = {}
        for col in self.__table__.columns:
            d[col.name] = getattr(self, col.name, None)
        return d


class Root(db.Model, C):
    __tablename__ = 'root'

    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(32), unique=1, nullable=0)
    cn_name = db.Column(db.String(32), unique=1)
    # one -> many (Root <-> Material)
    materials = db.relationship('Material', back_populates='root')

    def __repr__(self):
        return '<Root {}>'.format(self.name)


class AssetMd5(db.Model, C):
    __tablename__ = 'asset_md5'

    id = db.Column(db.Integer, primary_key=1)
    md5 = db.Column(db.String(128), nullable=False, unique=1)
    # one <-> one (AssetMd5 <-> Material)
    material = db.relationship('Material', uselist=False, back_populates='md5')

    def __repr__(self):
        return '<AssetMd5 {}>'.format(self.md5)


def _mCat_next_id():
    return MatCategory.query.count() + 1


class MatCategory(db.Model, C):
    __tablename__ = 'mat_category'
    id = db.Column(db.Integer, primary_key=1, default=_mCat_next_id)
    name = db.Column(db.String(64), unique=1)
    # one -> many
    materials = db.relationship('Material', back_populates='category')

    def __repr__(self):
        return '<MatCategory {}>'.format(self.name)


# many <-> many
# secondary table for m to m
t_mat_tag = db.Table('t_mat_tag',
                     db.Column('mat_id', db.Integer, db.ForeignKey('material.id')),
                     db.Column('tag_id', db.Integer, db.ForeignKey('mat_tag.id'))
                     )


def _mTag_next_id():
    return MatTag.query.count() + 1


class MatTag(db.Model, C):
    __tablename__ = 'mat_tag'
    id = db.Column(db.Integer, primary_key=1, default=_mTag_next_id)
    name = db.Column(db.String(64), unique=1)
    # many <-> many
    materials = db.relationship('Material', secondary=t_mat_tag, back_populates='tags')

    def __repr__(self):
        return '<MatTag {}>'.format(self.name)


def _material_next_id():
    return Material.query.count() + 1


class Material(db.Model, C):
    __tablename__ = 'material'

    id = db.Column(db.Integer, primary_key=1, default=_material_next_id)
    # many -> one (Material -> MatCategory)
    cat_id = db.Column(db.Integer, db.ForeignKey('mat_category.id'))
    category = db.relationship('MatCategory', back_populates='materials')
    # many <-> many
    tags = db.relationship('MatTag', secondary=t_mat_tag, back_populates='materials')

    # filename, filetype, filesize
    name = db.Column(db.String(128), nullable=False)
    type = db.Column(db.String(8), server_default='.sbsar')
    size = db.Column(db.Integer)
    relative_path = db.Column(db.String(512))
    has_sbszip = db.Column(db.Boolean, default=False)
    thumbnail = db.Column(db.String(512))
    used_times = db.Column(db.Integer, default=0)

    # md5_value = db.Column(db.String(128), unique=1)
    # one <-> one
    md5_id = db.Column(db.Integer, db.ForeignKey('asset_md5.id'))
    md5 = db.relationship('AssetMd5', back_populates='material')
    # many -> one (Material <-> Root)
    root_id = db.Column(db.Integer, db.ForeignKey('root.id'), default=3)
    root = db.relationship('Root', back_populates='materials')

    def setCategory(self, cat):
        """init cat_id for put this into db, Associate with MatCategory"""
        if self.cat_id is not None:
            print('there is already a cat_id')
            return
        c = cat.lower()
        q = MatCategory.query.filter_by(name=c).first()
        if q:
            self.cat_id = q.id
            db.session.commit()
            print('set {} cat_id={}'.format(self, self.cat_id))
        else:
            obj = MatCategory(name=c)
            db.session.add(obj)
            db.session.commit()
            self.cat_id = obj.id
            print('new MatCategory {} and set {} cat_id={}'.format(obj, self, self.cat_id))
        # db.session.commit()

    def setTags(self, tags):
        """init tags for put this into db, Associate with MatTag"""
        if self.tags:
            print('there are already some tags!')
            return
        tagList = [t.lower() for t in tags]
        tagSets = set()
        for tag in tagList:
            q = MatTag.query.filter_by(name=tag).first()
            if q:
                tagSets.add(q)
                db.session.commit()
            else:
                obj = MatTag(name=tag)
                db.session.add(obj)
                db.session.commit()
                tagSets.add(obj)
        if tagSets:
            self.tags = list(tagSets)
            db.session.commit()

    def setMD5(self, md5):
        """init md5_id for put this into db, Associate with AssetMd5"""
        if self.md5_id is not None:
            print('already has md5_id:{}'.format(self.md5_id))
            return
        q = AssetMd5.query.filter_by(md5=md5).first()
        if q:
            self.md5_id = q.id
            print('set {} md5_id={}'.format(self, self.md5_id))
            db.session.commit()
        else:
            obj = AssetMd5(md5=md5)
            db.session.add(obj)
            db.session.commit()
            self.md5_id = obj.id
            print('new AssetMd5 {} and set {} md5_id={}'.format(obj, self, self.md5_id))
        # db.session.commit()

    def __repr__(self):
        return '<Material {}>'.format(self.name)



