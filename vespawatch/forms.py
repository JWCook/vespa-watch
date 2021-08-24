from django.forms import inlineformset_factory, ModelForm, BooleanField, ChoiceField, IntegerField, EmailField, \
    CharField
from django.utils.translation import ugettext_lazy as _
from vespawatch.fields import ISODateTimeField
from .models import ManagementAction, Nest, Individual, NestPicture, IndividualPicture, Profile

OBS_FORM_VUE_FIELDS = ({'field_name': 'observation_time', 'attribute_if_error': 'date_is_invalid'},
                       {'field_name': 'latitude', 'attribute_if_error': 'latitude_is_invalid'},
                       {'field_name': 'longitude', 'attribute_if_error': 'longitude_is_invalid'},
                       )


class ReportObservationForm(ModelForm):
    privacy_policy = BooleanField(label=_('I agree with the <a href="/about/privacy-policy/" target="_blank">privacy policy</a>'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for vue_field in OBS_FORM_VUE_FIELDS:
            setattr(self, vue_field['attribute_if_error'], False)

    def clean(self):
        cleaned_data = self.cleaned_data
        self.errors_as_json = self.errors.as_json()

        for vue_field in OBS_FORM_VUE_FIELDS:
            if vue_field['field_name'] in self.errors:
                setattr(self, vue_field['attribute_if_error'], True)

        return cleaned_data


class IndividualForm(ReportObservationForm):
    redirect_to = ChoiceField(choices=(('index', 'index'), ('management', 'management')), initial='index')
    card_id = IntegerField()
    location = CharField(max_length=255, required=False)
    image_ids = CharField(max_length=255)
    observer_email = EmailField(label=_('Email address'))

    class Meta:
        model = Individual
        fields = ['taxon', 'individual_count', 'behaviour', 'latitude', 'longitude',
                  'observation_time', 'comments',
                  'observer_name', 'observer_email', 'observer_phone'
        ]
        field_classes = {
            'observation_time': ISODateTimeField,
        }

    def clean(self):
        cleaned_data = super().clean()
        if 'image_ids' not in cleaned_data or not cleaned_data['image_ids']:
            msg = 'You must add at least one picture'
            self.add_error(None, msg)
            setattr(self, "image_is_invalid", True)

        return cleaned_data

    def save(self, *args, **kwargs):
        observation = super().save(*args, **kwargs)
        image_ids = [x for x in self.cleaned_data['image_ids'].strip().split(',') if x]
        for image_id in image_ids:
            np = IndividualPicture.objects.get(pk=image_id)
            np.observation = observation
            np.save()


class NestForm(ReportObservationForm):
    redirect_to = ChoiceField(choices=(('index', 'index'), ('management', 'management')), initial='index')
    card_id = IntegerField()
    height = ChoiceField(label=_('Nest height'), choices=[('', '--------')] + list(Nest.HEIGHT_CHOICES))
    location = CharField(max_length=255, required=False)
    image_ids = CharField(max_length=255)
    observer_name = CharField(label=_('Name'), max_length=255)
    observer_email = EmailField(label=_('Email address'))
    observer_phone = CharField(label=_('Telephone number'), max_length=20)

    class Meta:
        model = Nest
        fields = ['taxon', 'latitude', 'longitude', 'municipality',
                  'observation_time', 'size', 'height', 'comments',
                  'observer_name', 'observer_email', 'observer_phone',
                  'expert_vv_confirmed'
        ]
        field_classes = {
            'observation_time': ISODateTimeField,
        }

    def clean(self):
        cleaned_data = super().clean()

        if 'image_ids' not in cleaned_data or not cleaned_data['image_ids']:
            msg = 'You must add at least one picture'
            self.add_error(None, msg)
            setattr(self, "image_is_invalid", True)
        return cleaned_data

    def save(self, *args, **kwargs):
        observation = super().save(*args, **kwargs)
        image_ids = [x for x in self.cleaned_data['image_ids'].strip().split(',') if x]
        for image_id in image_ids:
            np = NestPicture.objects.get(pk=image_id)
            np.observation = observation
            np.save()


class IndividualPictureForm(ModelForm):
    class Meta:
        model = IndividualPicture
        fields = ['observation', 'image']


class NestPictureForm(ModelForm):
    class Meta:
        model = NestPicture
        fields = ['observation', 'image']


IndividualImageFormset = inlineformset_factory(Individual, IndividualPicture, fields=('image',), extra=2)
NestImageFormset = inlineformset_factory(Nest, NestPicture, fields=('image',), extra=2)


class ManagementActionForm(ModelForm):
    class Meta:
        model = ManagementAction
        fields = ['user', 'nest', 'outcome', 'action_time', 'duration', 'person_name', 'comments', 'number_of_persons',
                  'site', 'nest_type', 'aftercare', 'problems', 'product', 'method']

        field_classes = {
            'action_time': ISODateTimeField,
        }


class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['organization', 'description', 'phone', 'email_notification']