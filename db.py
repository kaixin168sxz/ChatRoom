import os
import sqlite3
from datetime import datetime
from dbutils.pooled_db import PooledDB
import hashlib
import random
import string
from settings import *

def get_md5(data):
    md5 = hashlib.md5()
    md5.update(data.encode('utf-8'))
    return md5.hexdigest()

def md5_encrypt(data):
    for i in range(10):
        md5 = hashlib.md5()
        md5.update(data.encode('utf-8'))
        md5_output = md5.hexdigest()
        data = md5_output.replace('2', '016ajkif').replace('1', '6bga08j1a').replace('6', 'a').replace('bg', 'k').replace('1a', 'bg').replace('a', '1a')
    return ''.join(random.sample(string.digits + string.ascii_lowercase, 16)) + data + ''.join(random.sample(string.digits + string.ascii_lowercase, 10))

class Sqlite3DB:  # sqlite3 模块操作
    """
    1-inquiry_form() -- 查询多少张表单的方法\n
    2-create_a_table() -- 创建表单的方法\n
    3-insert_data() -- 插入数据的方法\n
    4-look_for_data() -- 查找数据的方法\n
    5-query_column_name() -- 查询表单中有多少列与列内数据的信息\n
    6-modify_data() -- 修改指定的数据\n
    7-deletion_data() -- 删除指定的数据\n
    """

    def __init__(self, path) -> None:  # 初始化数据库连接池
        self.connection, self.cur = None, None  # 获取数据库连接的初始对象   创建游标对象的初始对象
        self.pool = PooledDB(creator=sqlite3, mincached=5, maxcached=10, database=path)
        # creator：指定创建数据库连接的方式，这里使用了sqlite3；database：指定要连接的数据库文件路径。
        # mincached：指定连接池中最小的连接数，即连接池中始终保持的最少连接数。
        # maxcached：指定连接池中最大的连接数，即连接池中最多可以有多少个连接。

    def create_a_connection(self) -> None:  # 创建数据连接
        """
        创建数据库连接
        :return:不返回
        """
        self.connection = self.pool.connection()  # 这行代码是使用数据库连接池pool中的connection()方法来获取一个数据库连接。
        # 通过self.pool.connection()方法，会从连接池中获取一个可用的数据库连接，并将其赋值给实例变量self.connection，以便在后续操作中使用这个连接与数据库进行通信。
        self.cur = self.connection.cursor()
        # 创建了一个游标对象 cur，该游标对象用于执行 SQLite 查询并处理查询结果。通过游标对象，您可以执行 SQL 查询语句并对返回的结果进行操作。

    def close_the_connection(self) -> None:  # 关闭数据库连接
        """
        :return:
        """
        self.cur.close()  # 关闭游标
        self.connection.close()  # 关闭连接

    def connection_pools(self):  # 查看连接池数据
        """
        查看连接池数据
        :return:
        """
        print('[db]', self.pool.connections, '连接池的当前连接数量')  # 个人判断可能连接池的当前连接数量
        print('[db]', self.pool.idle_cache, '连接池的空闲数量')  # 源码里面有介绍连接池的空闲数量

    def run_sql(self, sql):
        self.create_a_connection()  # 创建数据连接
        self.cur.execute(sql)
        self.close_the_connection()  # 关闭数据库连接

    def inquiry_form(self) -> list:  # 查询数据中有多少表单
        """
        查询数据中有多少表单,返回多少张表。显示这个效果[('abc',), ……] 查询成功
        :return:返回多少张表 ，显示这个效果[('abc',), (……)]
        """
        self.create_a_connection()  # 创建数据连接
        self.cur.execute("SELECT name FROM sqlite_master WHERE type='table';")  # 1查询数据库里面有多少表格
        tables = self.cur.fetchall()  # 2  并且
        # print(tables, '查询成功')  # 3  打印出表的名字
        self.close_the_connection()  # 关闭数据库连接
        return tables  # 返回多少张表  ，显示这个效果[('users',……)……]

    def create_a_table(self, name: str, table_cols: str) -> tuple:  # 创建表单的方法  name是表单的名字  调用这个函数创建表单 create_a_table('ppp')
        """
        创建表格的方法,默认创建了8列。数据类型分为INTEGER整数 REAL浮点数 TEXT文本 BLOB二进制 NULL空 KEY是主键，TEXT NOT NULL 而如果
        你指定某列为TEXT NOT NULL，则在插入数据时必须为这一列提供一个非NULL的值，否则插入操作会失败。这样的设置可以确保表中的特定列不会包含
        空值。这一列传入None类型的数据就会报错，把NOT NULL删除就不报了。\n
        数据类型有如下几种--'''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY,text1 INTEGER,text2 REAL,
        text3 TEXT, text4 BLOB,   text5 TEXT NOT NULL   )'''
        如果有需要请手动修改。
        :param name: 参数name是表格的名字，表格名字必须是字符串，而且名字第一位不能是数字
        :return: 返回是否创建成功，格式：(str, bool)
        """
        number_of_forms = self.inquiry_form()  # 获取数据库里面一共有多少表单
        the_form_exists = any(name in i for i in number_of_forms)  # 如果name表格存在于数据库中，就返回Ture
        self.create_a_connection()  # 创建数据连接
        # 使用了any()函数和一个简洁的生成器表达式，它会遍历number_of_forms列表中的元素，检查每个元素中是否包含name，如果找到匹配的元素，the_form_exists将被设置为True
        if isinstance(name, str) and not name[0].isdigit() and not the_form_exists:
            # 判段表格的名字是字符串 并且 表格的第一位不能为数字，如果为数字就不创建表格
            create_table_query = table_cols
            self.cur.execute(f"CREATE TABLE {name} " + create_table_query)  # 使用游标对象 cursor 执行 SQL 查询语句的代码。在这里，cursor.execute() 方法用于执行
            forms_1 = (f'{name}表格创建成功', True)
            # create_table_query 中存储的 CREATE TABLE 查询语句。通过调用 cursor.execute() 方法，您可以向数据库发送和执行 SQL 查询语句。
        else:  # create_table_query 变量是创建SQL表格语句的字符串变量
            forms_1 = ('无法创建数据表，表格第一位不能为数字或者表格重复', False)
        self.close_the_connection()  # 关闭数据库连接
        return forms_1

    def insert_data(self, table: str, col: tuple, data: tuple) -> tuple:  # 插入数据的方法
        """
        往数据库中指定表单内插入数据的方法
        :param col: 表中要创建的列
        :param table: 数据库中表单的名字
        :param data: 元祖的方式插入数据，如(?, ?, ?, ?)
        :return: 返回一个元组，元组第二个元素为True表示插入成功
        """
        self.create_a_connection()  # 连接数据库
        if len(data) != len(col):
            raise IndexError('insert data: data and col must have same length.')
        self.cur.execute(f"INSERT INTO {table} ({', '.join(col)}) "
                         f"VALUES (?, ?, ?, ?)", data)
        self.connection.commit()  # 提交数据
        self.close_the_connection()  # 关闭数据库连接
        return f'{data}插入到表{table}中', True

    def look_for_data(self, table: str, mode: tuple) -> list:  # 查找数据的方法
        """
        查找表中指定数据，目前有5种方式。具体怎么传参数看注释\n
        1.查询指定表单内的全部数据 look_for_data('abc', ('table',)) abc为表单名，table为查询方式-查表单\n
        2.查询指定表单内有多少行数据 look_for_data('abc', ('lines',)) abc为表单名，lines为查询方式-查表单内行数\n
        3.查询指定主键id的整行数据  look_for_data('abc', ('id', '2')) abc为表单名 id为查询方式  '2'为主键id编号\n
        4.根据名字模糊查找 look_for_data('abc', ('m_name', 'col6', '好')) abc为表单 m_name为模糊查询 col6指定列名 '好'是模糊查询的关键字\n
        5.根据名字精确搜索 look_for_data('abc', ('name', 'col7', 'hello'))  abc为表单 name为精确查询 col7指定列名 'hello'是精确查询的关键字\n
        :param table: 要查找的表的名称
        :param mode: mode是一个元组，mode[0]是查询方式，mode[1]是指定的列名(具体在那一列搜索)，mode[2]是需要搜索的关键字
        :return:
        """
        self.create_a_connection()  # 连接数据库
        if mode[0] == 'table':   # 查询指定表单，返回该表单的所以数据。look_for_data('abc', ('table','*')) abc为表单名，table为查询方式-查表单 '*'为查询所有
            self.cur.execute(f"SELECT {mode[1]} FROM {table}")  # look_for_data('abc', ('table','*'))，返回abc表单的所有数据
        elif mode[0] == 'lines':  # 查询指定表单内有多少行数据。look_for_data('abc', ('lines',)) abc为表单名，lines为查询方式-查表单内行数
            self.cur.execute(f"SELECT COUNT(*) FROM {table}")  # look_for_data('abc', ('table',))，返回abc表单内行数
        elif mode[0] == 'id':  # 根据主键id查询，在传入id数字编号，返回该id数字编号的整行数据 look_for_data('abc', ('id', '2'))
            self.cur.execute(f"SELECT * FROM {table} WHERE id=?", (mode[1],))  # abc为表单名 id为查询方式 2为id编号，返回该id编号的整行数据
        elif mode[0] == 'm_name':
            # 根据名字模糊查找 look_for_data('abc', ('m_name', 'col6', '好')) abc为表单 m_name为模糊查询 col6指定列名 '好'是模糊查询的关键字
            self.cur.execute(f"SELECT * FROM {table} WHERE {mode[1]} LIKE ?", ('%' + mode[2] + '%',))
        elif mode[0] == 'name':
            # 根据名字精确搜索 look_for_data('abc', ('name', 'col7', 'hello'))  abc为表单 name为精确查询 col7指定列名 'hello'是精确查询的关键字
            self.cur.execute(f"SELECT * FROM {table} WHERE {mode[1]} = ?", (mode[2],))
        ah00 = self.cur.fetchall()  # 得到结果，返回参数
        self.close_the_connection()  # 关闭数据库连接
        return ah00

    def query_column_name(self, table: str) -> list:  # 查询表单中有多少列与列的信息，里面的table参数就是表单名，输出列名和对应的数据类型
        """
        查询表单中有多少列与列的信息
        :param table: 数据库中表单的名字
        :return: 返回 [(0, 'id', 'INTEGER', 0, None, 1), (1, 'text1', 'INTEGER', 0, None, 0),..
        """
        self.create_a_connection()  # 连接数据库
        self.cur.execute(f"PRAGMA table_info({table})")  # 查询表中有多少列名，里面的table参数就是表名
        columns = self.cur.fetchall()
        # print(columns, '查询列名参数成功')  # 得到[(0, 'id', 'INTEGER', 0, None, 1), (1, 'text0', 'TEXT', 0, None, 0),]
        # 元素0：列的索引  元素1：列名  元素2：数据类型 元素3：是否允许为NULL 元素4：默认值 元素5：是否为主键
        self.close_the_connection()  # 关闭数据库连接
        return columns  # 返回 [(0, 'id', 'INTEGER', 0, None, 1), (1, 'text1', 'INTEGER', 0, None, 0),...

    def modify_data(self, table: str, column: str, idd, content: str):  # 修改指定的数据
        # 修改指定的数据 modify_data('abc', 'col1', 4,'世界world') 'abc'是表单名 'col1'是列名 '4'是主键id  '世界world'是修改内容
        self.create_a_connection()  # 连接数据库
        # ----------------------更改数据，也可以改部分列内的------------------
        # self.cur.execute("UPDATE users SET text1=?, text2=?, text3=?, text4=?, text5=? WHERE id=?",
        # (1, 2, 2, 1, 666, 6))
        # self.cur.execute("UPDATE users SET text1=? WHERE id=?", ('nnn', 1))
        # ---------------------------------------------------------------
        self.cur.execute(f"UPDATE {table} SET {column}=? WHERE {idd[0]}=?", (content, idd[1]))
        self.connection.commit()  # 提交数据
        self.close_the_connection()  # 关闭数据库连接

    def del_data(self, table: str, column: str, content):  # 删除数据
        # 删除数据 del_data('abc','col1',12) 'abc'是指定表  'col1'是指定列 '12'是col1列中的数据，假如找到就删除这一行的所有数据
        self.create_a_connection()  # 连接数据库
        self.cur.execute(f"DELETE FROM {table} WHERE {column} = ?", (content,))
        self.connection.commit()  # 提交数据
        self.close_the_connection()  # 关闭数据库连接

    def del_from(self, table: str):
        self.create_a_connection()  # 连接数据库
        self.cur.execute(f".DELETE FROM {table}")
        self.connection.commit()  # 提交数据
        self.close_the_connection()  # 关闭数据库连接

class ChatRoomDB(Sqlite3DB):
    def __init__(self, db_file: str) -> None:
        if not os.path.exists(db_file):
            raise FileNotFoundError(db_file)

        super().__init__(db_file)
        self.user_table = 'users'
        self.messages_table = 'messages'
        self.create_a_table(self.messages_table, f"(id INTEGER PRIMARY KEY, user TEXT,message TEXT,time TEXT,file TEXT)")
        self.create_a_table(self.user_table, f"(id INTEGER PRIMARY KEY, user TEXT UNIQUE,passwd TEXT,email TEXT, note TEXT)")
        self.messages_cols = ('user', 'message', 'time', 'file')
        self.user_cols = ('user', 'passwd', 'email', 'note')

    def new_message(self, user: str, message: str, send_time: str='Auto', file_url: str='NoFiles'):
        now = datetime.now()
        if send_time == 'Auto':
            send_time = now.strftime('%Y/%m/%d %H:%M:%S')
        self.insert_data(self.messages_table, self.messages_cols, (user, message, send_time, file_url))
        return OK

    def sign_up(self, user: str, password: str, email: str, note: str=''):
        password = md5_encrypt(password)
        try:
            self.insert_data(self.user_table, self.user_cols, (user, password, email, note))
        except sqlite3.IntegrityError:
            print(f'[user] user {user} already exists.')
            return EXISTS
        else:
            print(f'[user] {user} has signed up. email: {email}, note: {note}, password: {password}')
            return OK

    def get_user_data(self, user: str) -> list | str:
        data = self.look_for_data(self.user_table, ('name', self.user_cols[0], user))
        data = NO_EXISTS if not data else data[0]
        return data

    def get_all_users(self) -> list | str:
        table = self.look_for_data(self.user_table, ('table','*'))
        data = []
        for i in table:
            data.append(i[1])
        data = NO_EXISTS if not data else data
        return data

    def get_all_emails(self) -> list | str:
        users = self.look_for_data(self.user_table, ('table','*'))
        data = []
        for i in users:
            if i[-1] == 'EmailSend':
                data.append(i)
        data = NO_EXISTS if not data else data
        return data
    
    def del_user(self, user: str) -> tuple:
        """
        删除用户
        :param user: 用户名
        :return: 返回一个元组，元组第二个元素为True表示删除成功
        """
        self.del_data(self.user_table, self.user_cols[1], user)
        return user, True
    
    def change_username(self, old_user: str, new_user: str) -> tuple:
        """
        修改用户名
        :param old_user: 旧用户名
        :param new_user: 新用户名
        :return: 返回一个元组，元组第二个元素为True表示修改成功
        """
        print(f'[user] Changing username from {old_user} to {new_user}...')
        try:
            self.modify_data(self.user_table, self.user_cols[0], (self.user_cols[0], old_user), new_user)
            print(f'[user] {old_user} has changed to {new_user}.')
            return NO_EXISTS
        except sqlite3.IntegrityError:
            print(f'[user] user {new_user} already exists.')
            return EXISTS