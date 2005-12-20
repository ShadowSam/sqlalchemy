# types.py
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

__all__ = [ 'TypeEngine', 'TypeDecorator', 'NullTypeEngine',
            'INT', 'CHAR', 'VARCHAR', 'TEXT', 'FLOAT', 'DECIMAL', 
            'TIMESTAMP', 'DATETIME', 'CLOB', 'BLOB', 'BOOLEAN', 'String', 'Integer', 'Numeric', 'Float', 'DateTime', 'Binary', 'Boolean', 'Unicode', 'NULLTYPE'
            ]


class TypeEngine(object):
    def get_col_spec(self):
        raise NotImplementedError()
    def convert_bind_param(self, value):
        raise NotImplementedError()
    def convert_result_value(self, value):
        raise NotImplementedError()
    def adapt(self, typeobj):
        return typeobj()
    def adapt_args(self):
        return self
        
def adapt_type(typeobj, colspecs):
    """given a generic type from this package, and a dictionary of 
    "conversion" specs from a DB-specific package, adapts the type
    to a correctly-configured type instance from the DB-specific package."""
    if type(typeobj) is type:
        typeobj = typeobj()
    typeobj = typeobj.adapt_args()
    t = typeobj.__class__
    for t in t.__mro__[0:-1]:
        try:
            return typeobj.adapt(colspecs[t])
        except KeyError, e:
            pass
    return typeobj.adapt(typeobj.__class__)
    
class NullTypeEngine(TypeEngine):
    def __init__(self, *args, **kwargs):
        pass
    def get_col_spec(self):
        raise NotImplementedError()
    def convert_bind_param(self, value):
        return value
    def convert_result_value(self, value):
        return value

class TypeDecorator(object):
    def get_col_spec(self):
        return self.extended.get_col_spec()
    def adapt(self, typeobj):
        t = self.__class__.__mro__[2]
        print repr(t)
        c = self.__class__()
        c.extended = t.adapt(self, typeobj)
        return c
    
class String(NullTypeEngine):
    def __init__(self, length = None, is_unicode=False):
        self.length = length
        self.is_unicode = is_unicode
    def adapt(self, typeobj):
        return typeobj(self.length)
    def adapt_args(self):
        if self.length is None:
            return TEXT(is_unicode=self.is_unicode)
        else:
            return self

class Unicode(String):
    def __init__(self, length=None):
        String.__init__(self, length, is_unicode=True)
    def adapt(self, typeobj):
        return typeobj(self.length, is_unicode=True)
        
class Integer(NullTypeEngine):
    """integer datatype"""
    # TODO: do string bind params need int(value) performed before sending ?  
    # seems to be not needed with SQLite, Postgres
    pass

class Numeric(NullTypeEngine):
    def __init__(self, precision = 10, length = 2):
        self.precision = precision
        self.length = length
    def adapt(self, typeobj):
        return typeobj(self.precision, self.length)

class Float(NullTypeEngine):
    def __init__(self, precision = 10):
        self.precision = precision
    def adapt(self, typeobj):
        return typeobj(self.precision)

class DateTime(NullTypeEngine):
    pass

class Binary(NullTypeEngine):
    pass

class Boolean(NullTypeEngine):
    pass

class FLOAT(Float):pass
class TEXT(String):pass
class DECIMAL(Numeric):pass
class INT(Integer):pass
INTEGER = INT
class TIMESTAMP(DateTime): pass
class DATETIME(DateTime): pass
class CLOB(String): pass
class VARCHAR(String): pass
class CHAR(String):pass
class BLOB(Binary): pass
class BOOLEAN(Boolean): pass

NULLTYPE = NullTypeEngine()
