import functools
import pickle
import marshal
from fabric.api import run


def rpc(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        command = ('python -c '
                   '"'
                   'from __future__ import print_function;'
                   'import marshal, pickle, types;'
                   'types.FunctionType(marshal.loads(%r), globals(), %r)'
                   '(*pickle.loads(%r), **pickle.loads(%r))'
                   '"')
        command = command % (marshal.dumps(f.func_code), f.func_name, pickle.dumps(args),
                             pickle.dumps(kwargs))
        run(command)
    return decorated
