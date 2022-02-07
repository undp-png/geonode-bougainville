# -*- coding: utf-8 -*-
"""A one line summary of the module or program, terminated by a period.

Leave one blank line.  The rest of this docstring should contain an
overall description of the module or program.  Optionally, it may also
contain a brief description of exported classes and functions and/or usage
examples.

@Date : 2022-01-15
@Author : CPoole
"""
import logging

from django.forms import ModelForm

from .models import CuratedThumbnailLarge

logger = logging.getLogger(__name__)


class CuratedThumbnailForm(ModelForm):
    class Meta:
        model = CuratedThumbnailLarge
        fields = ['img']
