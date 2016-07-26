#!/usr/bin/env python
# encoding: utf-8
import jinja2

def include_file_contents(name):
    return jinja2.Markup(loader.get_source(env, name)[0])

loader = jinja2.PackageLoader(__name__, './')
env = jinja2.Environment(loader=loader)
env.globals['include_file_contents'] = include_file_contents

def render():
    return env.get_template('fabfile_pre.py').render()

if __name__ == '__main__':
    print render()
