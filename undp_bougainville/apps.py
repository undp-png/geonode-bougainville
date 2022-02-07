# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2018 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
from django.apps import AppConfig as BaseAppConfig
from django.forms import model_to_dict, HiddenInput
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.staticfiles.templatetags import staticfiles


def run_setup_hooks(*args, **kwargs):
    from django.conf import settings
    from .celeryapp import app as celeryapp
    if celeryapp not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS += (celeryapp,)


class AppConfig(BaseAppConfig):
    name = "undp_bougainville"
    label = "undp_bougainville"

    def _get_logger(self):
        import logging
        return logging.getLogger(self.__class__.__module__)

    def hidden_metadata_fields(self):
        """A list of metadata fields to hide """
        return (
            "data_quality_statement",
            "restriction_code_type",
            "doi",
            "edition"
        )

    def ready(self):
        super(AppConfig, self).ready()
        run_setup_hooks()
        # from geonode.base.models import CuratedThumbnail
        #
        # try:
        #     self.patch_thumbnail(CuratedThumbnail)
        # except ImportError as exc:
        #     print(f"Patching model {exc}")
        #     pass
        from geonode.documents.forms import DocumentForm
        from geonode.geoapps.forms import GeoAppForm
        from geonode.layers.forms import LayerForm
        from geonode.maps.forms import MapForm

        from geonode.base.api.serializers import ThumbnailUrlField
        from geonode.api.resourcebase_api import CommonModelApi, LayerResource, MapResource, GeoAppResource, DocumentResource
        from geonode.groups.models import GroupProfile
        from geonode.invitations.views import GeoNodeSendInvite

        for app_form in [DocumentForm, GeoAppForm, LayerForm, MapForm]:
            self.patch_resource_base(app_form)
        self.patch_resourcemodel_api(CommonModelApi)
        self.patch_document_resource_model_api(DocumentResource)
        self.patch_layer_resource_model_api(LayerResource)
        self.patch_geoapps_resource_model_api(GeoAppResource)
        self.patch_map_resource_model_api(MapResource)
        self.patch_thumb_serializer(ThumbnailUrlField)
        self.patch_invite_function(GeoNodeSendInvite)

    def patch_resource_base(self, form):
        self._get_logger().info("Patching Resource Base")

        form.Meta.exclude = [*form.Meta.exclude, *self.hidden_metadata_fields()]

        def __init__(kls, *args, **kwargs):

            super(form, kls).__init__(*args, **kwargs)
            cols_to_exclude = [f for f in kls.fields.keys() if f in kls.Meta.exclude]
            [kls.fields.pop(_) for _ in cols_to_exclude]
            abstract = kls.fields.get("abstract")
            if abstract:
                abstract.label = _('Description')

            attribution = kls.fields.get("attribution")
            attribution_help_text = _('Who created the dataset?')
            if attribution:
                attribution.label = _('Source')
                attribution.help_text = attribution_help_text
            for field in self.hidden_metadata_fields():
                hide_field = kls.fields.get(field)
                if hide_field:
                    hide_field.hidden = True
                    hide_field.widget = HiddenInput()

            group_help_text = _('Who should have access to the data?')
            group = kls.fields.get("group")
            if group:
                group.help_text = group_help_text
            constraints_other = kls.fields.get("constraints_other")
            if constraints_other:
                constraints_other.label = _('Constraints / Caveats')

            for field in kls.fields:
                help_text = kls.fields[field].help_text
                if help_text != '':
                    kls.fields[field].widget.attrs.update(
                        {
                            'class': 'has-external-popover',
                            'data-content': help_text,
                            'data-placement': 'right',
                            'data-container': 'body',
                            'data-html': 'true'})

        form.__init__ = __init__

    def patch_thumbnail(self, thumbnail_class):
        """Attempt to patch geonode default thumbnail sizing

        https://github.com/GeoNode/geonode/blob/3fd76478bb6200d837a648ce2b1207b435efc509/geonode/base/views.py
        https://github.com/GeoNode/geonode/blob/master/geonode/thumbs/utils.py
        https://github.com/GeoNode/geonode/blob/42f5405bb1839910a6800ece8d31028049f90296/geonode/base/models.py#L1984

        """
        from imagekit.models import ImageSpecField
        from imagekit import ImageSpec, register
        from imagekit.exceptions import AlreadyRegistered
        from imagekit.processors import ResizeToFill
        from imagekit.cachefiles.backends import Simple
        from django.core.files.storage import default_storage as storage
        import os

        class LargeThumbnail(ImageSpec):
            processors = [ResizeToFill(420, 350)]
            format = 'JPEG'
            options = {'quality': 60}

        try:
            register.generator('base:curatedthumbnail:img_thumbnail_2', LargeThumbnail)
        except AlreadyRegistered as exc:
            pass
        except Exception as exc:
            self._get_logger().exception(exc)
            pass

        img_thumbnail = ImageSpecField(source='img',
                                       processors=[ResizeToFill(420, 350)],
                                       format='PNG',
                                       options={'quality': 60})
        self._get_logger().info("Patching Thumbnail")

        @property
        def thumbnail_url(kls):
            try:
                if not Simple()._exists(kls.img_thumbnail):
                    Simple().generate(kls.img_thumbnail, force=True)
                upload_path = storage.path(kls.img_thumbnail.name)
                actual_name = os.path.basename(storage.url(upload_path))
                _upload_path = os.path.join(os.path.dirname(upload_path), actual_name)
                if not os.path.exists(_upload_path):
                    os.rename(upload_path, _upload_path)
                return kls.img_thumbnail.url
            except Exception as e:
                print(e)
            return ''

        thumbnail_class.add_to_class("img_thumbnail", img_thumbnail)
        thumbnail_class.add_to_class("thumbnail_url", thumbnail_url)

    def patch_resourcemodel_api(self, commonmodel):

        def format_objects(kls, objects):
            """
            Format the objects for output in a response.
            """
            for key in ('site_url', 'has_time'):
                if key in kls.VALUES:
                    idx = kls.VALUES.index(key)
                    del kls.VALUES[idx]

            # hack needed because dehydrate does not seem to work in CommonModelApi
            formatted_objects = []
            for obj in objects:
                formatted_obj = model_to_dict(obj, fields=kls.VALUES)
                if 'site_url' not in formatted_obj or len(formatted_obj['site_url']) == 0:
                    formatted_obj['site_url'] = settings.SITEURL

                if formatted_obj['thumbnail_url'] and len(formatted_obj['thumbnail_url']) == 0:
                    formatted_obj['thumbnail_url'] = staticfiles.static(settings.MISSING_THUMBNAIL)

                formatted_obj['owner__username'] = obj.owner.username
                formatted_obj['owner_name'] = obj.owner.get_full_name() or obj.owner.username

                if hasattr(obj, 'curatedthumbnail'):
                    try:
                        if hasattr(obj.curatedthumbnail.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnail.thumbnail_url
                        # Overwrite with large thumb instead
                    except Exception as e:
                        self._get_logger().exception(e)
                # replace thumbnail_url with curated_thumbs
                if hasattr(obj, 'curatedthumbnaillarge'):
                    try:
                        # Overwrite with large thumb instead
                        if hasattr(obj.curatedthumbnaillarge.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnaillarge.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)

                formatted_objects.append(formatted_obj)

            return formatted_objects

        commonmodel.format_objects = format_objects

    def patch_geoapps_resource_model_api(self, geoappsmodel):
        from geonode.groups.models import GroupProfile
        def format_objects(kls, objects):
            """
            Formats the objects and provides reference to list of layers in GeoApp
            resources.

            :param objects: GeoApp objects
            """
            formatted_objects = []
            for obj in objects:
                # convert the object to a dict using the standard values.
                formatted_obj = model_to_dict(obj, fields=kls.VALUES)
                username = obj.owner.get_username()
                full_name = (obj.owner.get_full_name() or username)
                formatted_obj['owner__username'] = username
                formatted_obj['owner_name'] = full_name
                if obj.category:
                    formatted_obj['category__gn_description'] = obj.category.gn_description
                if obj.group:
                    formatted_obj['group'] = obj.group
                    try:
                        formatted_obj['group_name'] = GroupProfile.objects.get(slug=obj.group.name)
                    except GroupProfile.DoesNotExist:
                        formatted_obj['group_name'] = obj.group

                formatted_obj['keywords'] = [k.name for k in obj.keywords.all()] if obj.keywords else []
                formatted_obj['regions'] = [r.name for r in obj.regions.all()] if obj.regions else []

                if 'site_url' not in formatted_obj or len(formatted_obj['site_url']) == 0:
                    formatted_obj['site_url'] = settings.SITEURL

                # Probe Remote Services
                formatted_obj['store_type'] = 'geoapp'
                formatted_obj['online'] = True

                # replace thumbnail_url with curated_thumbs
                if hasattr(obj, 'curatedthumbnail'):
                    try:
                        if hasattr(obj.curatedthumbnail.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnail.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)
                        # replace thumbnail_url with curated_thumbs
                if hasattr(obj, 'curatedthumbnaillarge'):
                    try:
                        # Overwrite with large thumb instead
                        if hasattr(obj.curatedthumbnaillarge.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnaillarge.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)

                formatted_objects.append(formatted_obj)
            return formatted_objects

        geoappsmodel.format_objects = format_objects

    def patch_document_resource_model_api(self, document_model):
        from geonode.groups.models import GroupProfile
        def format_objects(kls, objects):
            """
            Formats the objects and provides reference to list of layers in map
            resources.

            :param objects: Map objects
            """
            formatted_objects = []
            for obj in objects:
                # convert the object to a dict using the standard values.
                formatted_obj = model_to_dict(obj, fields=kls.VALUES)
                username = obj.owner.get_username()
                full_name = (obj.owner.get_full_name() or username)
                formatted_obj['owner__username'] = username
                formatted_obj['owner_name'] = full_name
                if obj.category:
                    formatted_obj['category__gn_description'] = _(obj.category.gn_description)
                if obj.group:
                    formatted_obj['group'] = obj.group
                    try:
                        formatted_obj['group_name'] = GroupProfile.objects.get(slug=obj.group.name)
                    except GroupProfile.DoesNotExist:
                        formatted_obj['group_name'] = obj.group

                formatted_obj['keywords'] = [k.name for k in obj.keywords.all()] if obj.keywords else []
                formatted_obj['regions'] = [r.name for r in obj.regions.all()] if obj.regions else []

                if 'site_url' not in formatted_obj or len(formatted_obj['site_url']) == 0:
                    formatted_obj['site_url'] = settings.SITEURL

                # Probe Remote Services
                formatted_obj['store_type'] = 'dataset'
                formatted_obj['online'] = True

                # replace thumbnail_url with curated_thumbs
                if hasattr(obj, 'curatedthumbnail'):
                    try:
                        if hasattr(obj.curatedthumbnail.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnail.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)
                if hasattr(obj, 'curatedthumbnaillarge'):
                    try:
                        # Overwrite with large thumb instead
                        if hasattr(obj.curatedthumbnaillarge.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnaillarge.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)

                formatted_objects.append(formatted_obj)
            return formatted_objects

        document_model.format_objects = format_objects

    def patch_layer_resource_model_api(self, layer_model):
        from geonode.groups.models import GroupProfile
        def format_objects(kls, objects):
            """
            Formats the object.
            """
            formatted_objects = []
            for obj in objects:
                # convert the object to a dict using the standard values.
                # includes other values
                values = kls.VALUES + [
                    'alternate',
                    'name'
                ]
                formatted_obj = model_to_dict(obj, fields=values)
                username = obj.owner.get_username()
                full_name = (obj.owner.get_full_name() or username)
                formatted_obj['owner__username'] = username
                formatted_obj['owner_name'] = full_name
                if obj.category:
                    formatted_obj['category__gn_description'] = _(obj.category.gn_description)
                if obj.group:
                    formatted_obj['group'] = obj.group
                    try:
                        formatted_obj['group_name'] = GroupProfile.objects.get(slug=obj.group.name)
                    except GroupProfile.DoesNotExist:
                        formatted_obj['group_name'] = obj.group

                formatted_obj['keywords'] = [k.name for k in obj.keywords.all()] if obj.keywords else []
                formatted_obj['regions'] = [r.name for r in obj.regions.all()] if obj.regions else []

                # provide style information
                bundle = kls.build_bundle(obj=obj)
                formatted_obj['default_style'] = kls.default_style.dehydrate(
                    bundle, for_list=True)

                # Add resource uri
                formatted_obj['resource_uri'] = kls.get_resource_uri(bundle)

                formatted_obj['links'] = kls.dehydrate_ogc_links(bundle)

                if 'site_url' not in formatted_obj or len(formatted_obj['site_url']) == 0:
                    formatted_obj['site_url'] = settings.SITEURL

                # Probe Remote Services
                formatted_obj['store_type'] = 'dataset'
                formatted_obj['online'] = True
                if hasattr(obj, 'storeType'):
                    formatted_obj['store_type'] = obj.storeType
                    if obj.storeType == 'remoteStore' and hasattr(obj, 'remote_service'):
                        if obj.remote_service:
                            formatted_obj['online'] = (obj.remote_service.probe == 200)
                        else:
                            formatted_obj['online'] = False

                formatted_obj['gtype'] = kls.dehydrate_gtype(bundle)

                # replace thumbnail_url with curated_thumbs
                if hasattr(obj, 'curatedthumbnail'):
                    try:
                        if hasattr(obj.curatedthumbnail.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnail.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)
                if hasattr(obj, 'curatedthumbnaillarge'):
                    try:
                        # Overwrite with large thumb instead
                        if hasattr(obj.curatedthumbnaillarge.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnaillarge.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)

                formatted_obj['processed'] = obj.instance_is_processed
                # put the object on the response stack
                formatted_objects.append(formatted_obj)
            return formatted_objects

        layer_model.format_objects = format_objects

    def patch_map_resource_model_api(self, map_model):
        from geonode.groups.models import GroupProfile
        def format_objects(kls, objects):
            """
            Formats the objects and provides reference to list of layers in map
            resources.

            :param objects: Map objects
            """
            formatted_objects = []
            for obj in objects:
                # convert the object to a dict using the standard values.
                formatted_obj = model_to_dict(obj, fields=kls.VALUES)
                username = obj.owner.get_username()
                full_name = (obj.owner.get_full_name() or username)
                formatted_obj['owner__username'] = username
                formatted_obj['owner_name'] = full_name
                if obj.category:
                    formatted_obj['category__gn_description'] = _(obj.category.gn_description)
                if obj.group:
                    formatted_obj['group'] = obj.group
                    try:
                        formatted_obj['group_name'] = GroupProfile.objects.get(slug=obj.group.name)
                    except GroupProfile.DoesNotExist:
                        formatted_obj['group_name'] = obj.group

                formatted_obj['keywords'] = [k.name for k in obj.keywords.all()] if obj.keywords else []
                formatted_obj['regions'] = [r.name for r in obj.regions.all()] if obj.regions else []

                if 'site_url' not in formatted_obj or len(formatted_obj['site_url']) == 0:
                    formatted_obj['site_url'] = settings.SITEURL

                # Probe Remote Services
                formatted_obj['store_type'] = 'map'
                formatted_obj['online'] = True

                # get map layers
                map_layers = obj.layers
                formatted_layers = []
                map_layer_fields = [
                    'id',
                    'stack_order',
                    'format',
                    'name',
                    'opacity',
                    'group',
                    'visibility',
                    'transparent',
                    'ows_url',
                    'layer_params',
                    'source_params',
                    'local'
                ]
                for layer in map_layers:
                    formatted_map_layer = model_to_dict(
                        layer, fields=map_layer_fields)
                    formatted_layers.append(formatted_map_layer)
                formatted_obj['layers'] = formatted_layers

                # replace thumbnail_url with curated_thumbs
                if hasattr(obj, 'curatedthumbnail'):
                    try:
                        if hasattr(obj.curatedthumbnail.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnail.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)
                if hasattr(obj, 'curatedthumbnaillarge'):
                    try:
                        # Overwrite with large thumb instead
                        if hasattr(obj.curatedthumbnaillarge.img_thumbnail, 'url'):
                            formatted_obj['thumbnail_url'] = obj.curatedthumbnaillarge.thumbnail_url
                    except Exception as e:
                        self._get_logger().exception(e)

                formatted_objects.append(formatted_obj)
            return formatted_objects

        map_model.format_objects = format_objects


    def patch_thumb_serializer(self, thumbnailserializer):
        from geonode.base.utils import build_absolute_uri
        def get_attribute(kls, instance):
            thumbnail_url = instance.thumbnail_url
            if hasattr(instance, 'curatedthumbnail'):
                try:
                    if hasattr(instance.curatedthumbnail.img_thumbnail, 'url'):
                        thumbnail_url = instance.curatedthumbnail.thumbnail_url
                except Exception as e:
                    self._get_logger().exception(e)
            # curated thumbnail large overwrites
            if hasattr(instance, 'curatedthumbnaillarge'):
                try:
                    if hasattr(instance.curatedthumbnaillarge.img_thumbnail, 'url'):
                        thumbnail_url = instance.curatedthumbnaillarge.thumbnail_url
                except Exception as e:
                    self._get_logger().exception(e)

            return build_absolute_uri(thumbnail_url)
        thumbnailserializer.get_attribute = get_attribute

    def patch_invite_function(self, invite_view):

        def geonode_invite_form_invalid(kls, form, emails=None, e=None):
            if e:
                return kls.render_to_response(
                    kls.get_context_data(
                        error_message=_("Sorry, it was not possible to invite '%(email)s'"
                                        " due to the following issue: %(error)s (%(type)s)") % {
                                          "email": emails, "error": str(e), "type": type(e)}))
            else:
                return kls.render_to_response(
                    kls.get_context_data(form=form))

        def geonode_invite_form_valid(kls, form):
            emails = form.cleaned_data["email"]
            invited = []

            invite = None
            try:
                invites = form.save(emails)
                for invite_obj in invites:
                    invite = invite_obj
                    invite.inviter = kls.request.user
                    invite.save()
                    # invite.send_invitation(self.request)
                    kls.send_invitation(invite, kls.request)
                    invited.append(invite_obj.email)
            except Exception as e:
                if invite:
                    invite.delete()
                return kls.form_invalid(form, emails, e)

            return kls.render_to_response(
                kls.get_context_data(
                    success_message=_("Invitation successfully sent to '%(email)s'") % {
                        "email": ', '.join(invited)}))
        invite_view.form_valid = geonode_invite_form_valid
        invite_view.form_invalid = geonode_invite_form_invalid
