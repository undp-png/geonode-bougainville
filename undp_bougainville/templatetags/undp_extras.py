# -*- coding: utf-8 -*-
"""A one line summary of the module or program, terminated by a period.

Leave one blank line.  The rest of this docstring should contain an
overall description of the module or program.  Optionally, it may also
contain a brief description of exported classes and functions and/or usage
examples.

@Date : 2022-01-03
@Author : CPoole
"""
import re

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.simple_tag
def regex_replace(value, pattern, replace, *args, **kwargs):
    return re.sub(pattern, replace, value)
