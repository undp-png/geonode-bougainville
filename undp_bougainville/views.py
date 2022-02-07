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

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import CuratedThumbnailForm
from geonode.base.models import (
    ResourceBase
)
from geonode.utils import resolve_object
logger = logging.getLogger(__name__)


def thumbnail_upload(
        request,
        res_id,
        template='base/thumbnail_upload.html'):
    try:
        res = resolve_object(
            request, ResourceBase, {
                'id': res_id}, 'base.change_resourcebase')
    except PermissionDenied:
        return HttpResponse(
            'You are not allowed to change permissions for this resource',
            status=401,
            content_type='text/plain')

    form = CuratedThumbnailForm()

    if request.method == 'POST':
        if 'remove-thumb' in request.POST:
            if hasattr(res, 'curatedthumbnaillarge'):
                logger.info(f"Calling delete on {res.curatedthumbnaillarge}")
                res.curatedthumbnaillarge.delete()
        else:
            form = CuratedThumbnailForm(request.POST, request.FILES)
            if form.is_valid():
                ct = form.save(commit=False)
                # if hasattr(res, 'curatedthumbnail'):
                #     res.curatedthumbnail.delete()
                # remove existing thumbnail if any
                if hasattr(res, 'curatedthumbnaillarge'):
                    res.curatedthumbnaillarge.delete()
                else:
                    logger.error(f"{res} has no attribute curatedthumbnailarge.")
                ct.resource = res
                ct.save()
        return HttpResponseRedirect(request.path_info)

    return render(request, template, context={
        'resource': res,
        'form': form
    })