import json

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()


@register.simple_tag(takes_context=True)
def js_config_object(context):
    conf = {
        'currentLanguageCode': context.request.LANGUAGE_CODE,
        'debug': settings.JS_DEBUG,
        'baseUrl': settings.VESPAWATCH_BASE_SITE_URL,
        'staticRoot': settings.STATIC_URL,
        'apis': {
            'individualsUrl': reverse('vespawatch:api_individuals'),
            'nestsUrl': reverse('vespawatch:api_nests'),
            'actionNestSitesUrl': reverse('vespawatch:api_action_nest_sites'),
            'actionNestTypesUrl': reverse('vespawatch:api_action_nest_types'),
            'actionAftercareUrl': reverse('vespawatch:api_action_aftercare'),
            'actionProblemsUrl': reverse('vespawatch:api_action_problems'),
            'actionProductsUrl': reverse('vespawatch:api_action_products'),
            'actionMethodsUrl': reverse('vespawatch:api_action_methods'),
            'actionResultsUrl': reverse('vespawatch:api_action_results'),
            'actionSaveUrl': reverse('vespawatch:api_action_save'),
            'actionLoadUrl': reverse('vespawatch:api_action_get'),
            'actionDeleteUrl': reverse('vespawatch:api_action_delete'),
        },
        'map': {
            'circle': {
                'fillOpacity': settings.MAP_CIRCLE_FILL_OPACITY,
                'strokeOpacity': settings.MAP_CIRCLE_STROKE_OPACITY,
                'strokeWidth': settings.MAP_CIRCLE_STROKE_WIDTH,
                'nestRadius': settings.MAP_CIRCLE_NEST_RADIUS,
                'individualRadius': settings.MAP_CIRCLE_INDIVIDUAL_RADIUS,
                'individualColor':settings.MAP_CIRCLE_INDIVIDUAL_COLOR,
                'nestColor': settings.MAP_CIRCLE_NEST_COLOR,
                'unknownColor': settings.MAP_CIRCLE_UNKNOWN_COLOR
            },
            'initialPosition': settings.MAP_INITIAL_POSITION,
            'initialZoom': settings.MAP_INITIAL_ZOOM,

            'tileLayerBaseUrl': settings.MAP_TILELAYER_BASE_URL,
            'tileLayerOptions': settings.MAP_TILELAYER_OPTIONS
        }
    }
    return mark_safe(json.dumps(conf))


@register.filter
def markdown(value, arg=None):
    return mark_safe(markdownify(value))


@register.filter
def boolean_to_string(value, arg=None):
    if value is True:
        return "true"
    return "false"
