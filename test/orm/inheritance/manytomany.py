import testenv; testenv.configure_for_tests()
from sqlalchemy import *
from sqlalchemy.orm import *
from testlib import *


class InheritTest(ORMTest):
    """deals with inheritance and many-to-many relationships"""
    def define_tables(self, metadata):
        global principals
        global users
        global groups
        global user_group_map

        principals = Table('principals', metadata,
            Column('principal_id', Integer,
                   Sequence('principal_id_seq', optional=False),
                   primary_key=True),
            Column('name', String(50), nullable=False))

        users = Table('prin_users', metadata,
            Column('principal_id', Integer,
                   ForeignKey('principals.principal_id'), primary_key=True),
            Column('password', String(50), nullable=False),
            Column('email', String(50), nullable=False),
            Column('login_id', String(50), nullable=False))

        groups = Table('prin_groups', metadata,
            Column('principal_id', Integer,
                   ForeignKey('principals.principal_id'), primary_key=True))

        user_group_map = Table('prin_user_group_map', metadata,
            Column('user_id', Integer, ForeignKey( "prin_users.principal_id"),
                   primary_key=True ),
            Column('group_id', Integer, ForeignKey( "prin_groups.principal_id"),
                   primary_key=True ),
            )

    def testbasic(self):
        class Principal(object):
            def __init__(self, **kwargs):
                for key, value in kwargs.iteritems():
                    setattr(self, key, value)

        class User(Principal):
            pass

        class Group(Principal):
            pass

        mapper(Principal, principals)
        mapper(User, users, inherits=Principal)

        mapper(Group, groups, inherits=Principal, properties={
            'users': relation(User, secondary=user_group_map,
                              lazy=True, backref="groups")
            })

        g = Group(name="group1")
        g.users.append(User(name="user1", password="pw", email="foo@bar.com", login_id="lg1"))
        sess = create_session()
        sess.save(g)
        sess.flush()
        # TODO: put an assertion

class InheritTest2(ORMTest):
    """deals with inheritance and many-to-many relationships"""
    def define_tables(self, metadata):
        global foo, bar, foo_bar
        foo = Table('foo', metadata,
            Column('id', Integer, Sequence('foo_id_seq', optional=True),
                   primary_key=True),
            Column('data', String(20)),
            )

        bar = Table('bar', metadata,
            Column('bid', Integer, ForeignKey('foo.id'), primary_key=True),
            #Column('fid', Integer, ForeignKey('foo.id'), )
            )

        foo_bar = Table('foo_bar', metadata,
            Column('foo_id', Integer, ForeignKey('foo.id')),
            Column('bar_id', Integer, ForeignKey('bar.bid')))

    def testget(self):
        class Foo(object):
            def __init__(self, data=None):
                self.data = data
        class Bar(Foo):pass

        mapper(Foo, foo)
        mapper(Bar, bar, inherits=Foo)
        print foo.join(bar).primary_key
        print class_mapper(Bar).primary_key
        b = Bar('somedata')
        sess = create_session()
        sess.save(b)
        sess.flush()
        sess.clear()

        # test that "bar.bid" does not need to be referenced in a get
        # (ticket 185)
        assert sess.query(Bar).get(b.id).id == b.id

    def testbasic(self):
        class Foo(object):
            def __init__(self, data=None):
                self.data = data

        mapper(Foo, foo)
        class Bar(Foo):
            pass

        mapper(Bar, bar, inherits=Foo, properties={
            'foos': relation(Foo, secondary=foo_bar, lazy=False)
        })

        sess = create_session()
        b = Bar('barfoo')
        sess.save(b)
        sess.flush()

        f1 = Foo('subfoo1')
        f2 = Foo('subfoo2')
        b.foos.append(f1)
        b.foos.append(f2)

        sess.flush()
        sess.clear()

        l = sess.query(Bar).all()
        print l[0]
        print l[0].foos
        self.assert_unordered_result(l, Bar,
#            {'id':1, 'data':'barfoo', 'bid':1, 'foos':(Foo, [{'id':2,'data':'subfoo1'}, {'id':3,'data':'subfoo2'}])},
            {'id':b.id, 'data':'barfoo', 'foos':(Foo, [{'id':f1.id,'data':'subfoo1'}, {'id':f2.id,'data':'subfoo2'}])},
            )

class InheritTest3(ORMTest):
    """deals with inheritance and many-to-many relationships"""
    def define_tables(self, metadata):
        global foo, bar, blub, bar_foo, blub_bar, blub_foo

        # the 'data' columns are to appease SQLite which cant handle a blank INSERT
        foo = Table('foo', metadata,
            Column('id', Integer, Sequence('foo_seq', optional=True),
                   primary_key=True),
            Column('data', String(20)))

        bar = Table('bar', metadata,
            Column('id', Integer, ForeignKey('foo.id'), primary_key=True),
            Column('data', String(20)))

        blub = Table('blub', metadata,
            Column('id', Integer, ForeignKey('bar.id'), primary_key=True),
            Column('data', String(20)))

        bar_foo = Table('bar_foo', metadata,
            Column('bar_id', Integer, ForeignKey('bar.id')),
            Column('foo_id', Integer, ForeignKey('foo.id')))

        blub_bar = Table('bar_blub', metadata,
            Column('blub_id', Integer, ForeignKey('blub.id')),
            Column('bar_id', Integer, ForeignKey('bar.id')))

        blub_foo = Table('blub_foo', metadata,
            Column('blub_id', Integer, ForeignKey('blub.id')),
            Column('foo_id', Integer, ForeignKey('foo.id')))

    def testbasic(self):
        class Foo(object):
            def __init__(self, data=None):
                self.data = data
            def __repr__(self):
                return "Foo id %d, data %s" % (self.id, self.data)
        mapper(Foo, foo)

        class Bar(Foo):
            def __repr__(self):
                return "Bar id %d, data %s" % (self.id, self.data)

        mapper(Bar, bar, inherits=Foo, properties={
            'foos' :relation(Foo, secondary=bar_foo, lazy=True)
        })

        sess = create_session()
        b = Bar('bar #1')
        sess.save(b)
        b.foos.append(Foo("foo #1"))
        b.foos.append(Foo("foo #2"))
        sess.flush()
        compare = repr(b) + repr(sorted([repr(o) for o in b.foos]))
        sess.clear()
        l = sess.query(Bar).all()
        print repr(l[0]) + repr(l[0].foos)
        found = repr(l[0]) + repr(sorted([repr(o) for o in l[0].foos]))
        self.assertEqual(found, compare)

    @testing.fails_on('maxdb', 'FIXME: unknown')
    def testadvanced(self):
        class Foo(object):
            def __init__(self, data=None):
                self.data = data
            def __repr__(self):
                return "Foo id %d, data %s" % (self.id, self.data)
        mapper(Foo, foo)

        class Bar(Foo):
            def __repr__(self):
                return "Bar id %d, data %s" % (self.id, self.data)
        mapper(Bar, bar, inherits=Foo)

        class Blub(Bar):
            def __repr__(self):
                return "Blub id %d, data %s, bars %s, foos %s" % (self.id, self.data, repr([b for b in self.bars]), repr([f for f in self.foos]))

        mapper(Blub, blub, inherits=Bar, properties={
            'bars':relation(Bar, secondary=blub_bar, lazy=False),
            'foos':relation(Foo, secondary=blub_foo, lazy=False),
        })

        sess = create_session()
        f1 = Foo("foo #1")
        b1 = Bar("bar #1")
        b2 = Bar("bar #2")
        bl1 = Blub("blub #1")
        for o in (f1, b1, b2, bl1):
            sess.save(o)
        bl1.foos.append(f1)
        bl1.bars.append(b2)
        sess.flush()
        compare = repr(bl1)
        blubid = bl1.id
        sess.clear()

        l = sess.query(Blub).all()
        print l
        self.assert_(repr(l[0]) == compare)
        sess.clear()
        x = sess.query(Blub).filter_by(id=blubid).one()
        print x
        self.assert_(repr(x) == compare)


if __name__ == "__main__":
    testenv.main()
