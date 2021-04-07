from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# from dotenv import load_dotenv
# load_dotenv()
import os
import click
from flask_migrate import Migrate
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI',
                                                  'mysql+pymysql://root:Jason.li@321@localhost/flaskdb_test')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# 用于迁移数据库(当表结构发生变更时,不破坏原有数据)
# 基本步骤:
# flask db init (创建迁移环境,只需执行一次)
# flask db migrate -m "add note timestamp" (生成迁移脚本)
# flask db upgrade (执行更新)
migrate = Migrate(app, db)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return '<Note %r>' % self.body


# 一对多示例
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    title = db.Column(db.String(50), index=1)
    body = db.Column(db.Text)
    # 第一步：定义外键
    # foreign key, 外键只能存单一数据(标量),所以在“多”的一边
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))

    # 建立关系方法2: Article.author_id = x (Author.id)

    def __repr__(self):
        return '<Article %s %s>' % (self.title, self.body)


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(70), unique=True)
    phone = db.Column(db.String(20))
    # 第二步：定义关系属性
    # 关系属性在关系的出发侧定义，即一对多关系的“一”这一边
    articles = db.relationship('Article')

    # 建立关系方法1: Author.articles.append(Article)

    def __repr__(self):
        return '<Author %s %s>' % (self.name, self.phone)


# 双向关系示例
class Writer(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(70), unique=1)
    books = db.relationship('Book', back_populates='writer')

    def __repr__(self):
        return '<Writer {}>'.format(self.name)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    title = db.Column(db.String(50), index=1)
    writer_id = db.Column(db.Integer, db.ForeignKey('writer.id'))
    writer = db.relationship('Writer', back_populates='books')

    def __repr__(self):
        return '<Book {}>'.format(self.title)


# 使用backref简化双向关系定义
class Singer(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(20), unique=1)
    # backref 会在Song中添加singer标量属性
    # 虽然只定义了一个关系函数,但跟上面定义二个关系函数并使用back_populates参数效果一样
    '''>>> type(Song.singer)
    <class 'sqlalchemy.orm.attributes.InstrumentedAttribute'>
    '''
    songs = db.relationship('Song', backref='singer')
    '''>>> type(singer.songs)
    <class 'sqlalchemy.orm.collections.InstrumentedList'>
    '''

    def __repr__(self):
        return '<Singer {}>'.format(self.name)


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    title = db.Column(db.String(20), index=1)
    singer_id = db.Column(db.Integer, db.ForeignKey('singer.id'))

    def __repr__(self):
        return '<Song {}>'.format(self.title)


# 多对一关系
class Citizen(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(20), unique=1)
    # 外键总是在“多”的一边定义
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    # 关系属性在关系模式的出发方定义 (在这即为“多”方, 所以"多对一关系"中外键与关系属性均定义在“多”的一边)
    city = db.relationship('City')

    def __repr__(self):
        return '<Citizen {}>'.format(self.name)


class City(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(30), unique=1)

    def __repr__(self):
        return '<City {}>'.format(self.name)


# 一对一关系
class Country(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(30), unique=1)
    # 通过指定uselist=False, 一对多关系被转换为一对一关系
    capital = db.relationship('Capital', uselist=False, back_populates='country')

    def __repr__(self):
        return '<Country {}>'.format(self.name)


class Capital(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(50), unique=1)
    # 假定这是“多”的一边 (一对一关系是一对多的特例)
    # 所以跟一对多或多对一定义完全一样, 不变
    # 外键在“多”的一边
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    country = db.relationship('Country', back_populates='capital')

    def __repr__(self):
        return '<Capital {}>'.format(self.name)


# 多对多关系
# 多对多需要借助一个关联表，作为中间人，将多对多转化为二个一对多关系（一为模型，多为中间人，即关联表中对应列）
# 外键定义在中间表，注意：模型二边都需要定义外键
association_table = db.Table('association',
                             db.Column('student_id', db.Integer, db.ForeignKey('student.id')),
                             db.Column('teacher_id', db.Integer, db.ForeignKey('teacher.id'))
                             )


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(30), unique=1)
    grade = db.Column(db.String(20))
    # 定义关系
    # 多对多定义关系需要secondary指定关联表
    teachers = db.relationship('Teacher', secondary=association_table, back_populates='students')

    def __repr__(self):
        return '<Student {}>'.format(self.name)


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    name = db.Column(db.String(30), unique=1)
    office = db.Column(db.String(20))
    # 建立双向关系
    students = db.relationship('Student', secondary=association_table, back_populates='teachers')

    def __repr__(self):
        return '<Teacher {}>'.format(self.name)


# 级联操作cascade
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    title = db.Column(db.String(50), unique=1)
    body = db.Column(db.Text)
    # 设置了cascade的一侧将被视为父对象, 对应的则为子对象(即:Comment)
    # cascade默认行为是:save-update, merge (即没有指定cascade时)
    # 常用组合:
    # save-update,merge     (default，默认父对象删除时，子对象数据不会清除，但没了联系(外键值设置为空))
    # save-update,merge,delete
    # all (save-update,merge,delete,refresh-expire,expunge)
    # all,delete-orphan (关系解除时子对象变成了孤立对象，则自动删除)
    # 当需要删除子对象时可用all或save-update,merge,delete;
    # 包括delete的话，父对象删除时子对象数据自动删除
    comments = db.relationship('Comment', back_populates='post', cascade='all')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=1)
    body = db.Column(db.Text)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    post = db.relationship('Post', back_populates='comments')


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.cli.command()
def initDB():
    db.create_all()
    click.echo('init db (create all)')


@app.cli.command()
def renewDB():
    db.drop_all()
    db.create_all()
    click.echo('renew db (drop all & create all)')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Note=Note, Author=Author, Article=Article, Writer=Writer, Book=Book, Singer=Singer, Song=Song,
                Citizen=Citizen, City=City, Country=Country, Capital=Capital, Teacher=Teacher, Student=Student,
                Post=Post, Comment=Comment)


if __name__ == '__main__':
    app.run()
