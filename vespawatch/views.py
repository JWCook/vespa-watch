import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.views.generic.detail import BaseDetailView, SingleObjectMixin, SingleObjectTemplateResponseMixin
from django.views.generic.edit import DeletionMixin
from django.urls import reverse_lazy


from vespawatch.utils import ajax_login_required
from .forms import ManagementActionForm, IndividualForm, IndividualPictureForm, \
    NestForm, NestPictureForm, ProfileForm
from .models import Individual, Nest, ManagementAction, IdentificationCard, \
    get_observations, get_individuals, get_nests, IndividualPicture, NestPicture, Profile


class CustomBaseDetailView(SingleObjectMixin, View):
    """Subclassing this one to pass the request parameters to the kwargs of get_context_data"""
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object, **request.GET)
        return self.render_to_response(context)


class CustomBaseDeleteView(DeletionMixin, BaseDetailView):
    """Overriding the BaseDeleteView to add the redirect_to param from the request to the View object"""
    def delete(self, request, *args, **kwargs):
        r = request.GET.get('redirect_to', '')
        if r:
            self.requested_success_url = r
        return super(CustomBaseDeleteView, self).delete(request, *args, **kwargs)


class CustomDeleteView(SingleObjectTemplateResponseMixin, CustomBaseDeleteView):
    """Also had to override this one for adding the redirect_to param to the View object"""
    template_name_suffix = '_confirm_delete'


def index(request):
    return render(request, 'vespawatch/index.html', {'observations': get_observations(limit=4)})


def getinvolved(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'getinvolved'})


def identification(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'identification'})


def about_links(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'about_links'})


def about_management(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'about_management'})


def about_privacypolicy(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'about_privacypolicy'})


def about_project(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'about_project'})


def about_vespavelutina(request):
    return render(request, 'vespawatch/simple_page_fragment.html', {'fragment_id': 'about_vespavelutina'})


def latest_observations(request):
    return render(request, 'vespawatch/obs.html', {'observations': get_observations(limit=40)})


# CREATE UPDATE INDIVIDUAL OBSERVATIONS

def create_individual(request):
    if request.method == 'POST':
        redirect_to = request.POST.get('redirect_to')
        card_id = request.POST.get('card_id')
        identif_card = IdentificationCard.objects.get(pk=card_id)
        form = IndividualForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your observation was successfully created. Thanks for your contribution!"))
            return HttpResponseRedirect(reverse_lazy(f'vespawatch:{redirect_to}'))
    else:
        redirect_to = request.GET.get('redirect_to', 'index')
        identif_card_id = request.GET.get('card_id')
        identif_card = IdentificationCard.objects.get(pk=identif_card_id)
        image_ids = request.GET.get('image_ids', '')
        taxon = identif_card.represented_taxon
        form = IndividualForm(initial={
            'redirect_to': redirect_to,
            'card_id': identif_card_id,
            'image_ids': image_ids,
            'taxon': taxon})
    return render(request, 'vespawatch/individual_create.html',
                  {'form': form, 'type': 'individual', 'identif_card': identif_card})


# CREATE UPDATE NEST OBSERVATIONS

def create_nest(request):
    if request.method == 'POST':
        redirect_to = request.POST.get('redirect_to')
        card_id = request.POST.get('card_id')
        identif_card = IdentificationCard.objects.get(pk=card_id)
        form = NestForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Your observation was successfully created. Thanks for your contribution!"))
            return HttpResponseRedirect(reverse_lazy(f'vespawatch:{redirect_to}'))
    else:
        redirect_to = request.GET.get('redirect_to', 'index')
        identif_card_id = request.GET.get('card_id')
        image_ids = request.GET.get('image_ids', '')
        identif_card = IdentificationCard.objects.get(pk=identif_card_id)
        taxon = identif_card.represented_taxon
        form = NestForm(initial={
            'redirect_to': redirect_to,
            'card_id': identif_card_id,
            'image_ids': image_ids,
            'taxon': taxon
        })
    return render(request, 'vespawatch/nest_create.html',
                  {'form': form, 'type': 'nest', 'identif_card': identif_card})


@login_required
def profile(request):
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
    else:
        profile = Profile(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Your profile was successfully updated.'))
            return HttpResponseRedirect(reverse_lazy(f'vespawatch:index'))
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'vespawatch/profile.html', {'form': form, 'username': request.user.username})


@login_required
def management(request):
    return render(request, 'vespawatch/management.html')


@login_required
def nest_detail(request, pk=None):
    nest = get_object_or_404(Nest, pk=pk)
    action = nest.managementaction if nest.controlled else None
    return render(request, 'vespawatch/nest_detail.html', {'nest': nest, 'action': action,
                                                           'editable': nest.editable_by_user(request.user)})


def obs_create(request):
    # This is the step where the user select the species and type (nest/individual)
    cards = IdentificationCard.objects.all()

    return render(request, 'vespawatch/obs_create.html', {'identification_cards': cards})

# ==============
# API methods
# ==============
def individuals_json(request):
    """
    Return all individuals as JSON data.
    """
    limit = request.GET.get('limit', None)
    limit = int(limit) if limit is not None else None

    light = request.GET.get('light', None)
    vv_only = request.GET.get('vvOnly', None)
    flanders_only = request.GET.get('flOnly', 'false') == 'true'

    obs = get_individuals(limit=limit, vv_only=vv_only, flanders_only=flanders_only)

    if light:
        response = JsonResponse({
            'individuals': [model_to_dict(x) for x in obs]
        })
    else:
        response = JsonResponse({
            'individuals': [x.as_dict() for x in obs]
        })

    return response


def single_individual_json(request, pk=None):
    """
    Get a single individual and return it as JSON
    """
    return JsonResponse(get_object_or_404(Individual, pk=pk).as_dict())


def single_nest_json(request, pk=None):
    """
    Get a single nest and return it as JSON
    """
    return JsonResponse(get_object_or_404(Nest, pk=pk).as_dict())


def nests_json(request):
    """
    Return all nests as JSON data.
    """
    limit = request.GET.get('limit', None)
    limit = int(limit) if limit is not None else None

    light = request.GET.get('light', None)
    vv_only = request.GET.get('vvOnly', False) == 'true'
    confirmed_only = request.GET.get('confirmedOnly', False) == 'true'
    include_pictures = request.GET.get('includePictures', 'true') == 'true'
    flanders_only = request.GET.get('flOnly', 'false') == 'true'

    obs = get_nests(limit=limit, vv_only=vv_only, confirmed_only=confirmed_only, flanders_only=flanders_only)

    if light:
        response = JsonResponse({
            'nests': [model_to_dict(x) for x in obs]
        })
    else:
        response = JsonResponse({
            'nests': [x.as_dict(request_user=request.user, include_pictures=include_pictures) for x in obs]
        })

    return response


def management_actions_outcomes_json(request):
    #TODO: Implements sorting?
    #TODO: Implements i18n?
    outcomes = ManagementAction.OUTCOME_CHOICE
    return JsonResponse([{'value': outcome[0], 'label': outcome[1]} for outcome in outcomes], safe=False)


@ajax_login_required
@csrf_exempt
def delete_management_action(request):
    if request.method == 'DELETE':
        action = get_object_or_404(ManagementAction, pk=request.GET.get('action_id'))
        if request.user.is_staff or request.user is action.user:
            action.delete()
        else:
            return HttpResponseForbidden('Unauthorized')
        return JsonResponse({'result': 'OK'})


@ajax_login_required
@csrf_exempt
def save_management_action(request):
    if request.method == 'POST':
        existing_action_id = request.POST.get('action_id', None)

        if existing_action_id:  # We want to update an existing action
            action = get_object_or_404(ManagementAction, pk=existing_action_id)
            if request.user.is_staff or request.user is action.user:

                form = ManagementActionForm(request.POST, instance=action)
            else:
                return HttpResponseForbidden('Unauthorized')
        else:  # We want to create a new action
            form = ManagementActionForm(request.POST)

        try:
            form_data_copy = form.data.copy()
            form_data_copy['user'] = request.user.id
            form.data = form_data_copy
            action = form.save()
            return JsonResponse({'result': 'OK', 'actionId': action.pk}, status=201)
        except ValueError:
            return JsonResponse({'result': 'NOTOK', 'errors': form.errors}, status=422)


@ajax_login_required
def get_management_action(request):
    if request.method == 'GET':
        action_id = request.GET.get('action_id')
        action = get_object_or_404(ManagementAction, pk=action_id)

        return JsonResponse({'action_time': action.action_time,
                             'comments': action.comments,
                             'outcome':action.outcome,
                             'outcome_display':action.get_outcome_display(),
                             'duration': action.duration_in_seconds,
                             'number_of_persons': action.number_of_persons,
                             'person_name': action.person_name})


def get_nest_picture(request, pk=None):
    np = get_object_or_404(NestPicture, pk=pk)
    return JsonResponse(np.to_dict())


def get_individual_picture(request, pk=None):
    ip = get_object_or_404(IndividualPicture, pk=pk)
    return JsonResponse(ip.to_dict())


def save_nest_picture(request):
    """
    API method to save NestPictures
    To be used in the dropzone component. That component will immediately save the image and insert the image id
    in the Nest form
    """
    if request.method == 'POST':
        form = NestPictureForm(request.POST, request.FILES or None)
        if form.is_valid():
            img = form.save()
            return JsonResponse({'imageId': img.pk, 'type': 'NestPicture', 'name': img.image.name})
        else:
            return JsonResponse({'errors': form.errors}, status=400)


def save_individual_picture(request):
    """
    API method to save IndividualPictures
    To be used in the dropzone component. That component will immediately save the image and insert the image id
    in the Individual form
    """
    if request.method == 'POST':
        form = IndividualPictureForm(request.POST, request.FILES or None)
        if form.is_valid():
            img = form.save()
            return JsonResponse({'imageId': img.pk, 'type': 'IndividualPicture', 'name': img.image.name})
        else:
            return JsonResponse({'errors': form.errors}, status=400)


def _prepare_csv_response(filename):
    response = HttpResponse(
        content_type='text/csv',
    )

    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# Keys: human-readable field names. Values: model attribute OR callable (attribute gets retrieved, callable gets called)
COMMON_OBS_FIELDS_CSV = {
        'pk': 'pk',
        'Observation time': 'observation_time',
        'Species': 'taxon',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
        'Originates in Vespawatch': 'originates_in_vespawatch',
        'iNaturalist ID': 'inaturalist_id',
        'iNaturalist species': 'inaturalist_species',
        'iNaturalist vv confirmed': 'inat_vv_confirmed',
        'Created at': 'created_at',
        'comments': 'comments'
}


def _csv_export_view(filename, qs, common_fields_dict, specific_fields_dict):
    response = _prepare_csv_response(filename=filename)
    writer = csv.writer(response)

    # Write headers
    writer.writerow(list(common_fields_dict) + list(specific_fields_dict))

    # Write data
    for model_instance in qs:
        values = []
        for attr_or_callable_name in (list(common_fields_dict.values()) + list(specific_fields_dict.values())):
            attr = getattr(model_instance, attr_or_callable_name)
            if callable(attr):
                values.append(attr())
            else:
                values.append(attr)

        writer.writerow(values)

    return response


def csv_export_nests(request):
    specific_nest_fields_csv = {  # Same structure than COMMON_OBS_FIELDS_CSV
        'Height': 'get_height_display',
        'Size': 'get_size_display',
        'Expert vv confirmed': 'expert_vv_confirmed',
        'Municipality': 'municipality',
        'Controlled': 'controlled',
        'Duplicate of (pk)': 'duplicate_of'
    }

    return _csv_export_view(filename='nests.csv',
                            qs=Nest.objects.all().order_by('-observation_time'),
                            common_fields_dict=COMMON_OBS_FIELDS_CSV,
                            specific_fields_dict=specific_nest_fields_csv)


def csv_export_individuals(request):
    specific_individual_fields_csv = {  # Same structure than COMMON_OBS_FIELDS_CSV
        'Individual count': 'individual_count',
        'Behaviour': 'get_behaviour_display'
    }

    return _csv_export_view(filename='individuals.csv',
                            qs=Individual.objects.all().order_by('-observation_time'),
                            common_fields_dict=COMMON_OBS_FIELDS_CSV,
                            specific_fields_dict=specific_individual_fields_csv)


def csv_export_management_actions(request):
    return _csv_export_view(filename='management_actions.csv',
                            qs=ManagementAction.objects.all().order_by('-action_time'),
                            common_fields_dict={},
                            specific_fields_dict={
                                'Nest (pk)': 'nest_id',
                                'Date and time nest removal': 'action_time',
                                'User': 'user',
                                'Outcome': 'get_outcome_display',
                                'Time on site (in minutes)': 'duration',
                                'Number of people': 'number_of_persons',
                                'Comments': 'comments'

                            })