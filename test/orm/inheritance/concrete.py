import testenv; testenv.configure_for_tests()
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm import exc as orm_exc
from testlib import *
from sqlalchemy.orm import attributes
from testlib.testing import eq_

class Employee(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return self.__class__.__name__ + " " + self.name

class Manager(Employee):
    def __init__(self, name, manager_data):
        self.name = name
        self.manager_data = manager_data
    def __repr__(self):
        return self.__class__.__name__ + " " + self.name + " " +  self.manager_data

class Engineer(Employee):
    def __init__(self, name, engineer_info):
        self.name = name
        self.engineer_info = engineer_info
    def __repr__(self):
        return self.__class__.__name__ + " " + self.name + " " +  self.engineer_info

class Hacker(Engineer):
    def __init__(self, name, nickname, engineer_info):
        self.name = name
        self.nickname = nickname
        self.engineer_info = engineer_info
    def __repr__(self):
        return self.__class__.__name__ + " " + self.name + " '" + \
               self.nickname + "' " +  self.engineer_info

class Company(object):
   pass


class ConcreteTest(ORMTest):
    def define_tables(self, metadata):
        global managers_table, engineers_table, hackers_table, companies, employees_table

        companies = Table('companies', metadata,
           Column('id', Integer, primary_key=True),
           Column('name', String(50)))

        employees_table = Table('employees', metadata,
            Column('employee_id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('company_id', Integer, ForeignKey('companies.id'))
        )
        
        managers_table = Table('managers', metadata,
            Column('employee_id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('manager_data', String(50)),
            Column('company_id', Integer, ForeignKey('companies.id'))
        )

        engineers_table = Table('engineers', metadata,
            Column('employee_id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('engineer_info', String(50)),
            Column('company_id', Integer, ForeignKey('companies.id'))
        )

        hackers_table = Table('hackers', metadata,
            Column('employee_id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('engineer_info', String(50)),
            Column('company_id', Integer, ForeignKey('companies.id')),
            Column('nickname', String(50))
        )

    def test_basic(self):
        pjoin = polymorphic_union({
            'manager':managers_table,
            'engineer':engineers_table
        }, 'type', 'pjoin')

        employee_mapper = mapper(Employee, pjoin, polymorphic_on=pjoin.c.type)
        manager_mapper = mapper(Manager, managers_table, inherits=employee_mapper, 
            concrete=True, polymorphic_identity='manager')
        engineer_mapper = mapper(Engineer, engineers_table, inherits=employee_mapper, 
            concrete=True, polymorphic_identity='engineer')

        session = create_session()
        session.save(Manager('Tom', 'knows how to manage things'))
        session.save(Engineer('Kurt', 'knows how to hack'))
        session.flush()
        session.clear()

        assert set([repr(x) for x in session.query(Employee)]) == set(["Engineer Kurt knows how to hack", "Manager Tom knows how to manage things"])
        assert set([repr(x) for x in session.query(Manager)]) == set(["Manager Tom knows how to manage things"])
        assert set([repr(x) for x in session.query(Engineer)]) == set(["Engineer Kurt knows how to hack"])

        manager = session.query(Manager).one()
        session.expire(manager, ['manager_data'])
        self.assertEquals(manager.manager_data, "knows how to manage things")

    def test_multi_level_no_base(self):
        pjoin = polymorphic_union({
            'manager': managers_table,
            'engineer': engineers_table,
            'hacker': hackers_table
        }, 'type', 'pjoin')

        pjoin2 = polymorphic_union({
            'engineer': engineers_table,
            'hacker': hackers_table
        }, 'type', 'pjoin2')

        employee_mapper = mapper(Employee, pjoin, polymorphic_on=pjoin.c.type)
        manager_mapper = mapper(Manager, managers_table, 
                                inherits=employee_mapper, concrete=True, 
                                polymorphic_identity='manager')
        engineer_mapper = mapper(Engineer, engineers_table, 
                                 with_polymorphic=('*', pjoin2), 
                                 polymorphic_on=pjoin2.c.type,
                                 inherits=employee_mapper, concrete=True,
                                 polymorphic_identity='engineer')
        hacker_mapper = mapper(Hacker, hackers_table, 
                               inherits=engineer_mapper,
                               concrete=True, polymorphic_identity='hacker')

        session = create_session()
        tom = Manager('Tom', 'knows how to manage things')
        jerry = Engineer('Jerry', 'knows how to program')
        hacker = Hacker('Kurt', 'Badass', 'knows how to hack')
        session.add_all((tom, jerry, hacker))
        session.flush()

        # ensure "readonly" on save logic didn't pollute the expired_attributes
        # collection
        assert 'nickname' not in attributes.instance_state(jerry).expired_attributes
        assert 'name' not in attributes.instance_state(jerry).expired_attributes
        assert 'name' not in attributes.instance_state(hacker).expired_attributes
        assert 'nickname' not in attributes.instance_state(hacker).expired_attributes
        def go():
            self.assertEquals(jerry.name, "Jerry")
            self.assertEquals(hacker.nickname, "Badass")
        self.assert_sql_count(testing.db, go, 0)
        
        session.clear()

        assert set([repr(x) for x in session.query(Employee).all()]) == set(["Engineer Jerry knows how to program", "Manager Tom knows how to manage things", "Hacker Kurt 'Badass' knows how to hack"])
        assert set([repr(x) for x in session.query(Manager).all()]) == set(["Manager Tom knows how to manage things"])
        assert set([repr(x) for x in session.query(Engineer).all()]) == set(["Engineer Jerry knows how to program", "Hacker Kurt 'Badass' knows how to hack"])
        assert set([repr(x) for x in session.query(Hacker).all()]) == set(["Hacker Kurt 'Badass' knows how to hack"])

    def test_multi_level_with_base(self):
        pjoin = polymorphic_union({
            'employee':employees_table,
            'manager': managers_table,
            'engineer': engineers_table,
            'hacker': hackers_table
        }, 'type', 'pjoin')

        pjoin2 = polymorphic_union({
            'engineer': engineers_table,
            'hacker': hackers_table
        }, 'type', 'pjoin2')

        employee_mapper = mapper(Employee, employees_table, 
                with_polymorphic=('*', pjoin), polymorphic_on=pjoin.c.type)
        manager_mapper = mapper(Manager, managers_table, 
                                inherits=employee_mapper, concrete=True, 
                                polymorphic_identity='manager')
        engineer_mapper = mapper(Engineer, engineers_table, 
                                 with_polymorphic=('*', pjoin2), 
                                 polymorphic_on=pjoin2.c.type,
                                 inherits=employee_mapper, concrete=True,
                                 polymorphic_identity='engineer')
        hacker_mapper = mapper(Hacker, hackers_table, 
                               inherits=engineer_mapper,
                               concrete=True, polymorphic_identity='hacker')

        session = create_session()
        tom = Manager('Tom', 'knows how to manage things')
        jerry = Engineer('Jerry', 'knows how to program')
        hacker = Hacker('Kurt', 'Badass', 'knows how to hack')
        session.add_all((tom, jerry, hacker))
        session.flush()

        def go():
            self.assertEquals(jerry.name, "Jerry")
            self.assertEquals(hacker.nickname, "Badass")
        self.assert_sql_count(testing.db, go, 0)

        session.clear()

        # check that we aren't getting a cartesian product in the raw SQL.
        # this requires that Engineer's polymorphic discriminator is not rendered
        # in the statement which is only against Employee's "pjoin"
        assert len(testing.db.execute(session.query(Employee).with_labels().statement).fetchall()) == 3
        
        assert set([repr(x) for x in session.query(Employee)]) == set(["Engineer Jerry knows how to program", "Manager Tom knows how to manage things", "Hacker Kurt 'Badass' knows how to hack"])
        assert set([repr(x) for x in session.query(Manager)]) == set(["Manager Tom knows how to manage things"])
        assert set([repr(x) for x in session.query(Engineer)]) == set(["Engineer Jerry knows how to program", "Hacker Kurt 'Badass' knows how to hack"])
        assert set([repr(x) for x in session.query(Hacker)]) == set(["Hacker Kurt 'Badass' knows how to hack"])

    
    def test_without_default_polymorphic(self):
        pjoin = polymorphic_union({
            'employee':employees_table,
            'manager': managers_table,
            'engineer': engineers_table,
            'hacker': hackers_table
        }, 'type', 'pjoin')

        pjoin2 = polymorphic_union({
            'engineer': engineers_table,
            'hacker': hackers_table
        }, 'type', 'pjoin2')

        employee_mapper = mapper(Employee, employees_table, 
                                polymorphic_identity='employee')
        manager_mapper = mapper(Manager, managers_table, 
                                inherits=employee_mapper, concrete=True, 
                                polymorphic_identity='manager')
        engineer_mapper = mapper(Engineer, engineers_table, 
                                 inherits=employee_mapper, concrete=True,
                                 polymorphic_identity='engineer')
        hacker_mapper = mapper(Hacker, hackers_table, 
                               inherits=engineer_mapper,
                               concrete=True, polymorphic_identity='hacker')

        session = create_session()
        jdoe = Employee('Jdoe')
        tom = Manager('Tom', 'knows how to manage things')
        jerry = Engineer('Jerry', 'knows how to program')
        hacker = Hacker('Kurt', 'Badass', 'knows how to hack')
        session.add_all((jdoe, tom, jerry, hacker))
        session.flush()

        eq_(
            len(testing.db.execute(session.query(Employee).with_polymorphic('*', pjoin, pjoin.c.type).with_labels().statement).fetchall()),
            4
        )
        
        eq_(
            session.query(Employee).get(jdoe.employee_id), jdoe
        )
        eq_(
            session.query(Engineer).get(jerry.employee_id), jerry
        )
        eq_(
            set([repr(x) for x in session.query(Employee).with_polymorphic('*', pjoin, pjoin.c.type)]),
            set(["Employee Jdoe", "Engineer Jerry knows how to program", "Manager Tom knows how to manage things", "Hacker Kurt 'Badass' knows how to hack"])
        )
        eq_(
            set([repr(x) for x in session.query(Manager)]),
            set(["Manager Tom knows how to manage things"])
        )
        eq_(
            set([repr(x) for x in session.query(Engineer).with_polymorphic('*', pjoin2, pjoin2.c.type)]),
            set(["Engineer Jerry knows how to program", "Hacker Kurt 'Badass' knows how to hack"])
        )
        eq_(
            set([repr(x) for x in session.query(Hacker)]),
            set(["Hacker Kurt 'Badass' knows how to hack"])
        )
        # test adaption of the column by wrapping the query in a subquery
        eq_(
            len(testing.db.execute(
                session.query(Engineer).with_polymorphic('*', pjoin2, pjoin2.c.type).from_self().statement
            ).fetchall()),
            2
        )
        eq_(
            set([repr(x) for x in session.query(Engineer).with_polymorphic('*', pjoin2, pjoin2.c.type).from_self()]),
            set(["Engineer Jerry knows how to program", "Hacker Kurt 'Badass' knows how to hack"])
        )
        
    def test_relation(self):
        pjoin = polymorphic_union({
            'manager':managers_table,
            'engineer':engineers_table
        }, 'type', 'pjoin')

        mapper(Company, companies, properties={
            'employees':relation(Employee, lazy=False)
        })
        employee_mapper = mapper(Employee, pjoin, polymorphic_on=pjoin.c.type)
        manager_mapper = mapper(Manager, managers_table, inherits=employee_mapper, concrete=True, polymorphic_identity='manager')
        engineer_mapper = mapper(Engineer, engineers_table, inherits=employee_mapper, concrete=True, polymorphic_identity='engineer')

        session = create_session()
        c = Company()
        c.employees.append(Manager('Tom', 'knows how to manage things'))
        c.employees.append(Engineer('Kurt', 'knows how to hack'))
        session.save(c)
        session.flush()
        session.clear()

        def go():
            c2 = session.query(Company).get(c.id)
            assert set([repr(x) for x in c2.employees]) == set(["Engineer Kurt knows how to hack", "Manager Tom knows how to manage things"])
        self.assert_sql_count(testing.db, go, 1)

class ColKeysTest(ORMTest):
    def define_tables(self, metadata):
        global offices_table, refugees_table
        refugees_table = Table('refugee', metadata,
           Column('refugee_fid', Integer, primary_key=True),
           Column('refugee_name', Unicode(30), key='name'))

        offices_table = Table('office', metadata,
           Column('office_fid', Integer, primary_key=True),
           Column('office_name', Unicode(30), key='name'))
    
    def insert_data(self):
        refugees_table.insert().execute(
            dict(refugee_fid=1, name=u"refugee1"),
            dict(refugee_fid=2, name=u"refugee2")
        )
        offices_table.insert().execute(
            dict(office_fid=1, name=u"office1"),
            dict(office_fid=2, name=u"office2")
        )
        
    def test_keys(self):
        pjoin = polymorphic_union({
           'refugee': refugees_table,
           'office': offices_table
        }, 'type', 'pjoin')
        class Location(object):
           pass

        class Refugee(Location):
           pass

        class Office(Location):
           pass

        location_mapper = mapper(Location, pjoin, polymorphic_on=pjoin.c.type,
                                polymorphic_identity='location')
        office_mapper   = mapper(Office, offices_table, inherits=location_mapper,
                                concrete=True, polymorphic_identity='office')
        refugee_mapper  = mapper(Refugee, refugees_table, inherits=location_mapper,
                                concrete=True, polymorphic_identity='refugee')

        sess = create_session()
        eq_(sess.query(Refugee).get(1).name, "refugee1")
        eq_(sess.query(Refugee).get(2).name, "refugee2")

        eq_(sess.query(Office).get(1).name, "office1")
        eq_(sess.query(Office).get(2).name, "office2")

if __name__ == '__main__':
    testenv.main()
