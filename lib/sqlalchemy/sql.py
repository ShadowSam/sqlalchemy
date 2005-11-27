# sql.py
# Copyright (C) 2005 Michael Bayer mike_mp@zzzcomputing.com
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.


"""defines the base components of SQL expression trees."""

import sqlalchemy.schema as schema
import sqlalchemy.util as util
import sqlalchemy.types as types
import string

__ALL__ = ['textclause', 'select', 'join', 'and_', 'or_', 'not_', 'union', 'unionall', 'desc', 'asc', 'outerjoin', 'alias', 'subquery', 'bindparam', 'sequence']

def desc(column):
    """returns a descending ORDER BY clause element, e.g.:
    
    order_by = [desc(table1.mycol)]
    """    
    return CompoundClause(None, column, "DESC")

def asc(column):
    """returns an ascending ORDER BY clause element, e.g.:
    
    order_by = [asc(table1.mycol)]
    """
    return CompoundClause(None, column, "ASC")

def outerjoin(left, right, onclause, **kwargs):
    """returns an OUTER JOIN clause element, given the left and right hand expressions,
    as well as the ON condition's expression.  To chain joins together, use the resulting
    Join object's "join()" or "outerjoin()" methods."""
    return Join(left, right, onclause, isouter = True, **kwargs)

def join(left, right, onclause, **kwargs):
    """returns a JOIN clause element (regular inner join), given the left and right 
    hand expressions, as well as the ON condition's expression.  To chain joins 
    together, use the resulting Join object's "join()" or "outerjoin()" methods."""
    return Join(left, right, onclause, **kwargs)

def select(columns, whereclause = None, from_obj = [], **kwargs):
    """returns a SELECT clause element.
    
    'columns' is a list of columns and/or selectable items to select columns from
    'whereclause' is a text or ClauseElement expression which will form the WHERE clause
    'from_obj' is an list of additional "FROM" objects, such as Join objects, which will 
    extend or override the default "from" objects created from the column list and the 
    whereclause.
    **kwargs - additional parameters for the Select object.
    """
    return Select(columns, whereclause = whereclause, from_obj = from_obj, **kwargs)

def insert(table, values = None, **kwargs):
    """returns an INSERT clause element.
    
    'table' is the table to be inserted into.
    'values' is a dictionary which specifies the column specifications of the INSERT, 
    and is optional.  If left as None, the column specifications are determined from the 
    bind parameters used during the compile phase of the INSERT statement.  If the 
    bind parameters also are None during the compile phase, then the column
    specifications will be generated from the full list of table columns.

    If both 'values' and compile-time bind parameters are present, the compile-time 
    bind parameters override the information specified within 'values' on a per-key basis.

    The keys within 'values' can be either Column objects or their string identifiers.  
    Each key may reference one of: a literal data value (i.e. string, number, etc.), a Column object,
    or a SELECT statement.  If a SELECT statement is specified which references this INSERT 
    statement's table, the statement will be correlated against the INSERT statement.  
    """
    return Insert(table, values, **kwargs)

def update(table, whereclause = None, values = None, **kwargs):
    """returns an UPDATE clause element.  
    
    'table' is the table to be updated.
    'whereclause' is a ClauseElement describing the WHERE condition of the UPDATE statement.
    'values' is a dictionary which specifies the SET conditions of the UPDATE, and is
    optional. If left as None, the SET conditions are determined from the bind parameters
    used during the compile phase of the UPDATE statement.  If the bind parameters also are
    None during the compile phase, then the SET conditions will be generated from the full
    list of table columns.

    If both 'values' and compile-time bind parameters are present, the compile-time bind
    parameters override the information specified within 'values' on a per-key basis.

    The keys within 'values' can be either Column objects or their string identifiers. Each
    key may reference one of: a literal data value (i.e. string, number, etc.), a Column
    object, or a SELECT statement.  If a SELECT statement is specified which references this
    UPDATE statement's table, the statement will be correlated against the UPDATE statement.
    """
    return Update(table, whereclause, values, **kwargs)

def delete(table, whereclause = None, **kwargs):
    """returns a DELETE clause element.  
    
    'table' is the table to be updated.
    'whereclause' is a ClauseElement describing the WHERE condition of the UPDATE statement.
    """
    return Delete(table, whereclause, **kwargs)

def and_(*clauses):
    return _compound_clause('AND', *clauses)

def or_(*clauses):
    clause = _compound_clause('OR', *clauses)
    return clause

def not_(clause):
    clause.parens=True
    return BinaryClause(TextClause("NOT"), clause, None)
    
def exists(*args, **params):
    s = select(*args, **params)
    return BinaryClause(TextClause("EXISTS"), s, None)

def union(*selects, **params):
    return _compound_select('UNION', *selects, **params)

def union_all(*selects, **params):
    return _compound_select('UNION ALL', *selects, **params)

def alias(*args, **params):
    return Alias(*args, **params)

def subquery(alias, *args, **params):
    return Alias(Select(*args, **params), alias)

def bindparam(key, value = None, type=None):
    if isinstance(key, schema.Column):
        return BindParamClause(key.name, value, type=key.type)
    else:
        return BindParamClause(key, value, type=type)

def text(text, engine=None):
    return TextClause(text, engine=engine)

def null():
    return Null()
    
def sequence():
    return Sequence()

def _compound_clause(keyword, *clauses):
    return CompoundClause(keyword, *clauses)

def _compound_select(keyword, *selects, **params):
    if len(selects) == 0:
        return None
    s = selects[0]
    for n in selects[1:]:
        s.append_clause(keyword, n)

    if params.get('order_by', None) is not None:
        s.order_by(*params['order_by'])

    return s

def _is_literal(element):
    return not isinstance(element, ClauseElement) and not isinstance(element, schema.SchemaItem)


class ClauseVisitor(schema.SchemaVisitor):
    """builds upon SchemaVisitor to define the visiting of SQL statement elements in 
    addition to Schema elements."""
    def visit_columnclause(self, column):pass
    def visit_fromclause(self, fromclause):pass
    def visit_bindparam(self, bindparam):pass
    def visit_textclause(self, textclause):pass
    def visit_compound(self, compound):pass
    def visit_binary(self, binary):pass
    def visit_alias(self, alias):pass
    def visit_select(self, select):pass
    def visit_join(self, join):pass
    def visit_null(self, null):pass
    def visit_clauselist(self, list):pass
    
class Compiled(ClauseVisitor):
    """represents a compiled SQL expression.  the __str__ method of the Compiled object
    should produce the actual text of the statement.  Compiled objects are specific to the
    database library that created them, and also may or may not be specific to the columns
    referenced within a particular set of bind parameters.  In no case should the Compiled
    object be dependent on the actual values of those bind parameters, even though it may
    reference those values as defaults."""

    def __init__(self, engine, statement, bindparams):
        self.engine = engine
        self.bindparams = bindparams
        self.statement = statement

    def __str__(self):
        """returns the string text of the generated SQL statement."""
        raise NotImplementedError()
    def get_params(self, **params):
        """returns the bind params for this compiled object, with values overridden by 
        those given in the **params dictionary"""
        raise NotImplementedError()

    def execute(self, *multiparams, **params):
        """executes this compiled object using the underlying SQLEngine"""
        if len(multiparams):
            params = [self.get_params(**m) for m in multiparams]
        else:
            params = self.get_params(**params)
        return self.engine.execute(str(self), params, compiled = self, typemap = self.typemap)

    def scalar(self, *multiparams, **params):
        """executes this compiled object via the execute() method, then 
        returns the first column of the first row.  Useful for executing functions,
        sequences, rowcounts, etc."""
        return self.execute(*multiparams, **params).fetchone()[0]
        
class ClauseElement(object):
    """base class for elements of a programmatically constructed SQL expression.
    
    includes a list of 'from objects' which collects items to be placed
    in the FROM clause of a SQL statement.
    
    when many ClauseElements are attached together, the from objects and bind
    parameters are scooped up into the enclosing-most ClauseElement.
    """

    def hash_key(self):
        """returns a string that uniquely identifies the concept this ClauseElement
        represents.

        two ClauseElements can have the same value for hash_key() iff they both correspond to
        the exact same generated SQL.  This allows the hash_key() values of a collection of
        ClauseElements to be constructed into a larger identifying string for the purpose of
        caching a SQL expression.

        Note that since ClauseElements may be mutable, the hash_key() value is subject to
        change if the underlying structure of the ClauseElement changes.""" 
	raise NotImplementedError(repr(self))
    def _get_from_objects(self):
        raise NotImplementedError(repr(self))
    def _process_from_dict(self, data, asfrom):
        for f in self._get_from_objects():
            data.setdefault(f.id, f)
        if asfrom:
            data[self.id] = self
    def accept_visitor(self, visitor):
        raise NotImplementedError(repr(self))

    def copy_container(self):
        """should return a copy of this ClauseElement, iff this ClauseElement contains other
        ClauseElements.  Otherwise, it should be left alone to return self.  This is used to
        create copies of expression trees that still reference the same "leaf nodes".  The
        new structure can then be restructured without affecting the original."""
        return self


    def compile(self, engine = None, bindparams = None, typemap=None):
        """compiles this SQL expression using its underlying SQLEngine to produce
        a Compiled object.  If no engine can be found, an ansisql engine is used.
        bindparams is a dictionary representing the default bind parameters to be used with 
        the statement.  """
        if engine is None:
            for f in self._get_from_objects():
                engine = f.engine
                if engine is not None: break
            else:
                import sqlalchemy.ansisql as ansisql
                engine = ansisql.engine()
                #raise "no engine supplied, and no engine could be located within the clauses!"

        return engine.compile(self, bindparams = bindparams, typemap=typemap)

    def __str__(self):
        return str(self.compile())
        
    def execute(self, *multiparams, **params):
        """compiles and executes this SQL expression using its underlying SQLEngine. the
        given **params are used as bind parameters when compiling and executing the
        expression. the DBAPI cursor object is returned."""
        e = self.engine
        if len(multiparams):
            bindparams = multiparams[0]
        else:
            bindparams = params
        c = self.compile(e, bindparams = bindparams)
        return c.execute(*multiparams, **params)

    def scalar(self, *multiparams, **params):
        """executes this SQL expression via the execute() method, then 
        returns the first column of the first row.  Useful for executing functions,
        sequences, rowcounts, etc."""
        return self.execute(*multiparams, **params).fetchone()[0]

class CompareMixin(object):
    def __lt__(self, other):
        return self._compare('<', other)
        
    def __le__(self, other):
        return self._compare('<=', other)

    def __eq__(self, other):
        return self._compare('=', other)

    def __ne__(self, other):
        return self._compare('!=', other)

    def __gt__(self, other):
        return self._compare('>', other)

    def __ge__(self, other):
        return self._compare('>=', other)

    def like(self, other):
        return self._compare('LIKE', other)

    def in_(self, *other):
        if len(other) == 0:
            return self.__eq__(None)
        elif len(other) == 1 and not isinstance(other[0], Selectable):
            return self.__eq__(other[0])
        elif _is_literal(other[0]):
            return self._compare('IN', CompoundClause(',', spaces=False, parens=True, *other))
        else:
            return self._compare('IN', union(*other))

    def startswith(self, other):
        return self._compare('LIKE', str(other) + "%")
    
    def endswith(self, other):
        return self._compare('LIKE', "%" + str(other))

        
class ColumnClause(ClauseElement, CompareMixin):
    """represents a textual column clause in a SQL statement."""

    def __init__(self, text, selectable):
        self.text = text
        self.table = selectable
        self._impl = ColumnImpl(self)
        self.type = types.NullTypeEngine()
        
    columns = property(lambda self: [self])
    name = property(lambda self:self.text)
    key = property(lambda self:self.text)
    label = property(lambda self:self.text)
    fullname = property(lambda self:self.text)

    def accept_visitor(self, visitor): 
        visitor.visit_columnclause(self)

    def hash_key(self):
        return "ColumnClause(%s, %s)" % (self.text, self.table.hash_key())

    def _get_from_objects(self):
        return []

    def _compare(self, operator, obj):
        if _is_literal(obj):
            if obj is None:
                if operator != '=':
                    raise "Only '=' operator can be used with NULL"
                return BinaryClause(self, null(), 'IS')
            elif self.table.name is None:
                obj = BindParamClause(self.text, obj, shortname=self.text, type=self.type)
            else:
                obj = BindParamClause(self.table.name + "_" + self.text, obj, shortname = self.text, type=self.type)

        return BinaryClause(self, obj, operator)

    def _make_proxy(self, selectable, name = None):
        c = ColumnClause(self.text or name, selectable)
        selectable.columns[c.key] = c
        c._impl = ColumnImpl(c)
        return c

class FromClause(ClauseElement):
    """represents a FROM clause element in a SQL statement."""
    
    def __init__(self, from_name = None, from_key = None):
        self.from_name = from_name
        self.id = from_key or from_name
        
    def _get_from_objects(self):
        # this could also be [self], at the moment it doesnt matter to the Select object
        return []
        
    engine = property(lambda s: None)
    
    def hash_key(self):
        return "FromClause(%s, %s)" % (repr(self.id), repr(self.from_name))
            
    def accept_visitor(self, visitor): 
        visitor.visit_fromclause(self)
    
class BindParamClause(ClauseElement):
    def __init__(self, key, value, shortname = None, type = None):
        self.key = key
        self.value = value
        self.shortname = shortname
        self.type = type or types.NULLTYPE

    def accept_visitor(self, visitor):
        visitor.visit_bindparam(self)

    def _get_from_objects(self):
        return []
     
    def hash_key(self):
        return "BindParam(%s, %s, %s)" % (repr(self.key), repr(self.value), repr(self.shortname))

    def typeprocess(self, value):
        return self.type.convert_bind_param(value)
            
class TextClause(ClauseElement):
    """represents any plain text WHERE clause or full SQL statement"""
    
    def __init__(self, text = "", engine=None):
        self.text = text
        self.parens = False
        self.engine = engine
    def accept_visitor(self, visitor): 
        visitor.visit_textclause(self)
    def hash_key(self):
        return "TextClause(%s)" % repr(self.text)
    def _get_from_objects(self):
        return []

class Null(ClauseElement):
    def accept_visitor(self, visitor):
        visitor.visit_null(self)
    def _get_from_objects(self):
        return []
    def hash_key(self):
        return "Null"
    
class CompoundClause(ClauseElement):
    """represents a list of clauses joined by an operator"""
    def __init__(self, operator, *clauses, **kwargs):
        self.operator = operator
        self.clauses = []
        self.parens = kwargs.pop('parens', False)
        self.spaces = kwargs.pop('spaces', False)
        for c in clauses:
            if c is None: continue
            self.append(c)
    
    def copy_container(self):
        clauses = [clause.copy_container() for clause in self.clauses]
        return CompoundClause(self.operator, *clauses)
        
    def append(self, clause):
        if _is_literal(clause):
            clause = TextClause(repr(clause))
        elif isinstance(clause, CompoundClause):
            clause.parens = True
        self.clauses.append(clause)

    def accept_visitor(self, visitor):
        for c in self.clauses:
            c.accept_visitor(visitor)
        visitor.visit_compound(self)

    def _get_from_objects(self):
        f = []
        for c in self.clauses:
            f += c._get_from_objects()
        return f
        
    def hash_key(self):
        return string.join([c.hash_key() for c in self.clauses], self.operator)
        
class ClauseList(ClauseElement):
    def __init__(self, *clauses):
        self.clauses = clauses
        
    def accept_visitor(self, visitor):
        for c in self.clauses:
            c.accept_visitor(visitor)
        visitor.visit_clauselist(self)
    
    def _get_from_objects(self):
        return []
        
class BinaryClause(ClauseElement):
    """represents two clauses with an operator in between"""
    
    def __init__(self, left, right, operator):
        self.left = left
        self.right = right
        self.operator = operator
        self.parens = False

    def copy_container(self):
        return BinaryClause(self.left.copy_container(), self.right.copy_container(), self.operator)
        
    def _get_from_objects(self):
        return self.left._get_from_objects() + self.right._get_from_objects()

    def hash_key(self):
        return self.left.hash_key() + self.operator + self.right.hash_key()
        
    def accept_visitor(self, visitor):
        self.left.accept_visitor(visitor)
        self.right.accept_visitor(visitor)
        visitor.visit_binary(self)

    def swap(self):
        c = self.left
        self.left = self.right
        self.right = c
        
class Selectable(FromClause):
    """represents a column list-holding object, like a table, alias or subquery.  can be used anywhere a Table is used."""
    
    c = property(lambda self: self.columns)

    def accept_visitor(self, visitor):
        raise NotImplementedError()
    
    def select(self, whereclauses = None, **params):
        return select([self], whereclauses, **params)

    def join(self, right, *args, **kwargs):
        return Join(self, right, *args, **kwargs)

    def outerjoin(self, right, *args, **kwargs):
        return Join(self, right, isouter = True, *args, **kwargs)

    def alias(self, name):
        return Alias(self, name)
    def union(self, other, **kwargs):
        return union(self, other, **kwargs)
    def union_all(self, other, **kwargs):
        return union_all(self, other, **kwargs)
    def group_parenthesized(self):
        """indicates if this Selectable requires parenthesis when grouped into a compound
        statement"""
        return True
        
class Join(Selectable):
    # TODO: put "using" + "natural" concepts in here and make "onclause" optional
    def __init__(self, left, right, onclause, isouter = False, allcols = True):
        self.left = left
        self.right = right
        self.id = self.left.id + "_" + self.right.id
        self.allcols = allcols
        if allcols:
            self.columns = [c for c in self.left.columns] + [c for c in self.right.columns]
        else:
            self.columns = self.right.columns

        # TODO: if no onclause, do NATURAL JOIN
        self.onclause = onclause
        self.isouter = isouter
        self.rowid_column = self.left.rowid_column
        
    primary_keys = property (lambda self: [c for c in self.left.columns if c.primary_key] + [c for c in self.right.columns if c.primary_key])

    def group_parenthesized(self):
        """indicates if this Selectable requires parenthesis when grouped into a compound
        statement"""
        return True

    def hash_key(self):
        return "Join(%s, %s, %s, %s)" % (repr(self.left.hash_key()), repr(self.right.hash_key()), repr(self.onclause.hash_key()), repr(self.isouter))

    def select(self, whereclauses = None, **params):
        return select([self.left, self.right], and_(self.onclause, whereclauses), **params)

    def accept_visitor(self, visitor):
        self.left.accept_visitor(visitor)
        self.right.accept_visitor(visitor)
        self.onclause.accept_visitor(visitor)
        visitor.visit_join(self)

    engine = property(lambda s:s.left.engine or s.right.engine)

    class JoinMarker(FromClause):
        def __init__(self, id, join):
            FromClause.__init__(self, from_key=id)
            self.join = join
            
    def _process_from_dict(self, data, asfrom):
        for f in self.onclause._get_from_objects():
            data[f.id] = f
        for f in self.left._get_from_objects() + self.right._get_from_objects():
            # mark the object as a "blank" "from" that wont be printed
            data[f.id] = Join.JoinMarker(f.id, self)
        # a JOIN always impacts the final FROM list of a select statement
        data[self.id] = self
        
    def _get_from_objects(self):
        return [self] + self.onclause._get_from_objects() + self.left._get_from_objects() + self.right._get_from_objects()
        
class Alias(Selectable):
    def __init__(self, selectable, alias = None):
        self.selectable = selectable
        self.columns = util.OrderedProperties()
        if alias is None:
            alias = id(self)
        self.name = alias
        self.id = self.name
        self.count = 0
        self.rowid_column = self.selectable.rowid_column._make_proxy(self)
        for co in selectable.columns:
            co._make_proxy(self)

    primary_keys = property (lambda self: [c for c in self.columns if c.primary_key])

    def hash_key(self):
        return "Alias(%s, %s)" % (repr(self.selectable.hash_key()), repr(self.name))

    def accept_visitor(self, visitor):
        self.selectable.accept_visitor(visitor)
        visitor.visit_alias(self)

    def _get_from_objects(self):
        return [self]

    def group_parenthesized(self):
        return False
        
    engine = property(lambda s: s.selectable.engine)




class ColumnImpl(Selectable, CompareMixin):
    """Selectable implementation that gets attached to a schema.Column object."""
    
    def __init__(self, column):
        self.column = column
        self.name = column.name
        self.columns = [self.column]
        
        if column.table.name:
            self.label = column.table.name + "_" + self.column.name
            self.fullname = column.table.name + "." + self.column.name
        else:
            self.label = self.column.name
            self.fullname = self.column.name

    engine = property(lambda s: s.column.engine)
    
    def copy_container(self):
        return self.column

    def group_parenthesized(self):
        return False
        
    def _get_from_objects(self):
        return [self.column.table]
    
    def _compare(self, operator, obj):
        if _is_literal(obj):
            if obj is None:
                if operator != '=':
                    raise "Only '=' operator can be used with NULL"
                return BinaryClause(self.column, null(), 'IS')
            elif self.column.table.name is None:
                obj = BindParamClause(self.name, obj, shortname = self.name, type = self.column.type)
            else:
                obj = BindParamClause(self.column.table.name + "_" + self.name, obj, shortname = self.name, type = self.column.type)

        return BinaryClause(self.column, obj, operator)



class TableImpl(Selectable):
    """attached to a schema.Table to provide it with a Selectable interface
    as well as other functions
    """

    def __init__(self, table):
        self.table = table
        self.id = self.table.name
        self._rowid_column = schema.Column(self.table.engine.rowid_column_name(), types.Integer, hidden=True)
        self._rowid_column._set_parent(table)
    
    rowid_column = property(lambda s: s._rowid_column)
    
    def get_from_text(self):
        return self.table.name
    
    engine = property(lambda s: s.table.engine)
    
    def group_parenthesized(self):
        return False

    def _process_from_dict(self, data, asfrom):
        for f in self._get_from_objects():
            data.setdefault(f.id, f)
        if asfrom:
            data[self.id] = self.table
    
    def join(self, right, *args, **kwargs):
        return Join(self.table, right, *args, **kwargs)
    
    def outerjoin(self, right, *args, **kwargs):
        return Join(self.table, right, isouter = True, *args, **kwargs)

    def alias(self, name):
        return Alias(self.table, name)
            
    def select(self, whereclauses = None, **params):
        return select([self.table], whereclauses, **params)

    def insert(self, values = None):
        return insert(self.table, values=values)

    def update(self, whereclause = None, values = None):
        return update(self.table, whereclause, values)

    def delete(self, whereclause = None):
        return delete(self.table, whereclause)
        
    columns = property(lambda self: self.table.columns)

    def _get_from_objects(self):
        return [self.table]

    def create(self, **params):
        self.table.engine.create(self.table)

    def drop(self, **params):
        self.table.engine.drop(self.table)
        
    
class Select(Selectable):
    """finally, represents a SELECT statement, with appendable clauses, as well as 
    the ability to execute itself and return a result set."""
    def __init__(self, columns, whereclause = None, from_obj = [], group_by = None, order_by = None, use_labels = False, distinct=False, engine = None):
        self.columns = util.OrderedProperties()
        self._froms = util.OrderedDict()
        self.use_labels = use_labels
        self.id = "Select(%d)" % id(self)
        self.name = None
        self.whereclause = None
        self._engine = engine
        self.rowid_column = None
        
        # indicates if this select statement is a subquery inside another query
        self.issubquery = False
        # indicates if this select statement is a subquery as a criterion
        # inside of a WHERE clause
        self.is_where = False

        self.distinct = distinct
        self._text = None
        self._raw_columns = []
        self._clauses = []
        self._correlated = None
        self._correlator = Select.CorrelatedVisitor(self, False)
        self._wherecorrelator = Select.CorrelatedVisitor(self, True)
        
        for c in columns:
            self.append_column(c)
            
        if whereclause is not None:
            self.append_whereclause(whereclause)

        for f in from_obj:
            self.append_from(f)

        if group_by:
            self.append_clause("GROUP_BY", group_by)

        if order_by:
            self.order_by(*order_by)

    class CorrelatedVisitor(ClauseVisitor):
        """visits a clause, locates any Select clauses, and tells them that they should
        correlate their FROM list to that of their parent."""
        def __init__(self, select, is_where):
            self.select = select
            self.is_where = is_where
        def visit_select(self, select):
            if select is self.select:
                return
            select.is_where = self.is_where
            select.issubquery = True
            if select._correlated is None:
                select._correlated = self.select._froms

    def append_column(self, column):
        if _is_literal(column):
            column = ColumnClause(str(column), self)

        self._raw_columns.append(column)

        for f in column._get_from_objects():
            f.accept_visitor(self._correlator)
            if self.rowid_column is None and hasattr(f, 'rowid_column'):
                self.rowid_column = f.rowid_column._make_proxy(self)
        column._process_from_dict(self._froms, False)
        
        for co in column.columns:
            if self.use_labels:
                co._make_proxy(self, name = co.label)
            else:
                co._make_proxy(self)

    def append_whereclause(self, whereclause):
        if type(whereclause) == str:
            whereclause = TextClause(whereclause)

        whereclause.accept_visitor(self._wherecorrelator)
        whereclause._process_from_dict(self._froms, False)
        
        if self.whereclause is not None:
            self.whereclause = and_(self.whereclause, whereclause)
        else:
            self.whereclause = whereclause

    def clear_from(self, id):
        self.append_from(FromClause(from_name = None, from_key = id))
        
    def append_from(self, fromclause):
        if type(fromclause) == str:
            fromclause = FromClause(from_name = fromclause)

        fromclause.accept_visitor(self._correlator)
        fromclause._process_from_dict(self._froms, True)
        
    def append_clause(self, keyword, clause):
        if type(clause) == str:
            clause = TextClause(clause)
        
        self._clauses.append((keyword, clause))
        
    def compile(self, engine = None, bindparams = None):
        if engine is None:
            engine = self.engine
        if engine is None:
            raise "no engine supplied, and no engine could be located within the clauses!"

        return engine.compile(self, bindparams)

    def _get_froms(self):
        return [f for f in self._froms.values() if self._correlated is None or not self._correlated.has_key(f.id)]
    froms = property(lambda s: s._get_froms())
    
    def accept_visitor(self, visitor):
        for f in self.froms:
            f.accept_visitor(visitor)
        if self.whereclause is not None:
            self.whereclause.accept_visitor(visitor)
        for tup in self._clauses:
            tup[1].accept_visitor(visitor)
            
        visitor.visit_select(self)
    
    def order_by(self, *clauses):
        if not hasattr(self, 'order_by_clause'):
            self.order_by_clause = ClauseList(*clauses)
            self.append_clause("ORDER BY", self.order_by_clause)
        else:
            self.order_by_clause.clauses += clauses
        
    def select(self, whereclauses = None, **params):
        return select([self], whereclauses, **params)

    def _find_engine(self):
        """tries to return a SQLEngine, either explicitly set in this object, or searched
        within the from clauses for one"""
        
        if self._engine is not None:
            return self._engine
        
        for f in self._froms.values():
            e = f.engine
            if e is not None: 
                self._engine = e
                return e
            
        return None

    engine = property(lambda s: s._find_engine())
    
    def _get_from_objects(self):
        if self.is_where:
            return []
        else:
            return [self]


class UpdateBase(ClauseElement):
    """forms the base for INSERT, UPDATE, and DELETE statements.  
    Deals with the special needs of INSERT and UPDATE parameter lists -  
    these statements have two separate lists of parameters, those
    defined when the statement is constructed, and those specified at compile time."""
    
    def _process_colparams(self, parameters):
        if parameters is None:
            return None

        if isinstance(parameters, list) or isinstance(parameters, tuple):
            pp = {}
            i = 0
            for c in self.table.c:
                pp[c.key] = parameters[i]
                i +=1
            parameters = pp
            
        for key in parameters.keys():
            value = parameters[key]
            if isinstance(value, Select):
                value.clear_from(self.table.id)
            elif _is_literal(value):
                if _is_literal(key):
                    col = self.table.c[key]
                else:
                    col = key
                try:
                    parameters[key] = bindparam(col, value)
                except KeyError:
                    del parameters[key]
        return parameters
        
    def get_colparams(self, parameters):
        # case one: no parameters in the statement, no parameters in the 
        # compiled params - just return binds for all the table columns
        if parameters is None and self.parameters is None:
            return [(c, bindparam(c.name, type=c.type)) for c in self.table.columns]

        # if we have statement parameters - set defaults in the 
        # compiled params
        if parameters is None:
            parameters = {}
        else:
            parameters = parameters.copy()
            
        if self.parameters is not None:
            for k, v in self.parameters.iteritems():
                parameters.setdefault(k, v)

        # now go thru compiled params, get the Column object for each key
        d = {}
        for key, value in parameters.iteritems():
            if isinstance(key, schema.Column):
                d[key] = value
            else:
                try:
                    d[self.table.columns[str(key)]] = value
                except AttributeError:
                    pass

        # create a list of column assignment clauses as tuples
        values = []
        for c in self.table.columns:
            if d.has_key(c):
                value = d[c]
                if _is_literal(value):
                    value = bindparam(c.name, value, type=c.type)
                values.append((c, value))
        return values

    def compile(self, engine = None, bindparams = None):
        if engine is None:
            engine = self.engine
            
        if engine is None:
            raise "no engine supplied, and no engine could be located within the clauses!"

        return engine.compile(self, bindparams)

class Insert(UpdateBase):
    def __init__(self, table, values=None, **params):
        self.table = table
        self.select = None
        self.parameters = self._process_colparams(values)
        self.engine = self.table.engine
        
    def accept_visitor(self, visitor):
        if self.select is not None:
            self.select.accept_visitor(visitor)

        visitor.visit_insert(self)

class Update(UpdateBase):
    def __init__(self, table, whereclause, values=None, **params):
        self.table = table
        self.whereclause = whereclause
        self.parameters = self._process_colparams(values)
        self.engine = self.table.engine

    def accept_visitor(self, visitor):
        if self.whereclause is not None:
            self.whereclause.accept_visitor(visitor)
        visitor.visit_update(self)

class Delete(UpdateBase):
    def __init__(self, table, whereclause, **params):
        self.table = table
        self.whereclause = whereclause
        self.engine = self.table.engine

    def accept_visitor(self, visitor):
        if self.whereclause is not None:
            self.whereclause.accept_visitor(visitor)
        visitor.visit_delete(self)

class Sequence(BindParamClause):
    def __init__(self):
        BindParamClause.__init__(self, 'sequence')

    def accept_visitor(self, visitor):
        visitor.visit_sequence(self)

        
