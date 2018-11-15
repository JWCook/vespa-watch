import os
from datetime import datetime

import dateparser
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import defaultfilters
from django.urls import reverse
from django.utils.timezone import is_naive, make_aware
from pyinaturalist.node_api import get_observation
from pyinaturalist.rest_api import create_observations, update_observation

from vespawatch.utils import make_unique_filename


def get_species_from_inat_taxon_id(inaturalist_taxon_id):
    """ Raises Species.DoesNotExists().

    Raises Species.MultipleObjectsReturned() if several matches, which shouldn't happen."""
    return Species.objects.get(inaturalist_pull_taxon_ids__contains=[inaturalist_taxon_id])


class Species(models.Model):
    name = models.CharField(max_length=100)

    vernacular_name = models.CharField(max_length=100, blank=True)

    inaturalist_push_taxon_id = models.BigIntegerField(null=True, blank=True,
                                                       help_text="When pushing an observation to iNaturalist, we'll "
                                                                 "use this taxon_id")
    inaturalist_pull_taxon_ids = ArrayField(models.BigIntegerField(), blank=True, null=True,
                                            help_text="When pulling observations from iNaturalist, reconcile according "
                                                      "to those IDs.")

    def __str__(self):
        return  self.name

    class Meta:
        verbose_name_plural = "species"



class InatCreatedObservationsManager(models.Manager):
    """The queryset only contains observations that originates from iNaturalist (NOT Vespa-Watch)"""
    def get_queryset(self):
        return super().get_queryset().filter(originates_in_vespawatch=False)


class VespawatchCreatedObservationsManager(models.Manager):
    """The queryset only contains observations that originates from Vespa-Watch"""
    def get_queryset(self):
        return super().get_queryset().filter(originates_in_vespawatch=True)


class SpeciesMatchError(Exception):
    """Unable to match this (iNaturalist) taxon id to our Species table"""

class ParseDateError(Exception):
    """Cannot parse this date"""

def create_observation_from_inat_data(inaturalist_data):
    """Creates an observation in our local database according to the data from iNaturalist API.

    :returns: the observation (instance of Nest or Individual) created.

    Raises:
        SpeciesMatchError
    """
    observation_time = dateparser.parse(inaturalist_data['observed_on_string'],
                                        settings={'TIMEZONE': inaturalist_data['observed_time_zone']})
    if observation_time is None:
        # Sometimes, dateparser doesn't understand the string but we have the bits and pieces in
        # inaturalist_data['observed_on_details']
        details = inaturalist_data['observed_on_details']
        observation_time = datetime(year=details['year'],
                                    month=details['month'],
                                    day=details['day'],
                                    hour=details['hour'])  # in the observed cases, we had nothing more precise than the
                                                           # hour

    # Sometimes, the time is naive (even when specifying it to dateparser), because (for the detected cases, at least)
    # The time is 00:00:00. In that case we make it aware to avoid Django warnings (in the local time zone since all
    # observations occur in Belgium
    if is_naive(observation_time):
        # Some dates (apparently)
        observation_time = make_aware(observation_time)

    if observation_time:
        # Reconcile the species
        try:
            species = get_species_from_inat_taxon_id(inaturalist_data['taxon']['id'])
        except Species.DoesNotExist:
            raise SpeciesMatchError

        # Check if it has the vespawatch_evidence observation field value and if it's set to "nest"
        is_nest_ofv = next((item for item in inaturalist_data['ofvs'] if item["field_id"] == settings.VESPAWATCH_EVIDENCE_OBS_FIELD_ID), None)
        if is_nest_ofv and is_nest_ofv['value'] == "nest":
            return Nest.objects.create(
                originates_in_vespawatch=False,
                inaturalist_id=inaturalist_data['id'],
                species=species,
                latitude=inaturalist_data['geojson']['coordinates'][1],
                longitude=inaturalist_data['geojson']['coordinates'][0],
                observation_time=observation_time)  # TODO: What to do with iNat observations without (parsable) time?
        else:  # Default is specimen
            return Individual.objects.create(
                originates_in_vespawatch=False,
                inaturalist_id=inaturalist_data['id'],
                species=species,
                latitude=inaturalist_data['geojson']['coordinates'][1],
                longitude=inaturalist_data['geojson']['coordinates'][0],
                observation_time=observation_time)  # TODO: What to do with iNat observations without (parsable) time?
    else:
        raise ParseDateError

def get_local_obs_matching_inat_id(inat_id):
    """Returns a Nest or an Individual, raise ObjectDoesNotExist if nothing is found."""
    models_to_search = [Nest, Individual]
    for model in models_to_search:
        try:
            return model.objects.get(inaturalist_id=inat_id)
        except model.DoesNotExist:
            pass

    raise ObjectDoesNotExist

def update_loc_obs_taxon_according_to_inat(inaturalist_data):
    """Takes data coming from iNaturalist about one of our local observation, and update the taxon of said local obs,
    if necessary.

    :returns: either
        - 'no_community_id' (we have no community id, so we didn't change)
        - 'matching_community_id' (the community id is agreement with our local database, we didn't change it
        - 'updated' (we updated to match the community!)

    :raises
        - SpeciesMatchError: if we don't know this inaturalist taxon id (so nothing was updated)
        - ObjectDoesNotExist: we can't find the local observation that match iNaturalist data
    """
    community_taxon_id = inaturalist_data['community_taxon_id']

    # TODO: test this more (new code, some path are not frequently used)
    if community_taxon_id is not None:
        local_obs = get_local_obs_matching_inat_id(inaturalist_data['id'])
        if community_taxon_id not in local_obs.species.inaturalist_pull_taxon_ids:
            # we have to update our observation to follow the community identification
            try:
                local_obs.species = get_species_from_inat_taxon_id(community_taxon_id)
                local_obs.save()
                return 'updated'
            except Species.DoesNotExist:
                raise SpeciesMatchError
        else:
            return 'matching_community_id'

    return 'no_community_id'

def inat_observation_comes_from_vespawatch(inat_observation_id):
    """ Takes an observation_id from iNat API and returns True if this observation was first created from the
    VespaWatch website.

    Slow, since we need an API call to retrieve the observation_field_values
    """
    obs_data = get_observation(observation_id=inat_observation_id)

    # We simply check if there's a vespawatch_id observation field on this observation
    for ofv in obs_data['ofvs']:
        if ofv['field_id'] == settings.VESPAWATCH_ID_OBS_FIELD_ID:
            return True

    return False


class FirefightersZone(models.Model):
    name = models.CharField(max_length=100)
    mpolygon = models.MultiPolygonField(null=True)

    def __str__(self):
        return self.name


def get_zone_for_coordinates(lat, lon):
    """Returns the Firefighters zone instance given (point) coordinates. lat/lon in EPSG4326.

    :raises FirefightersZone.DoesNotExist:
    """
    point = Point(x=lon, y=lat)
    return FirefightersZone.objects.get(mpolygon__intersects=point)


class AbstractObservation(models.Model):
    originates_in_vespawatch = models.BooleanField(default=True, help_text="The observation was first created in VespaWatch, not iNaturalist")
    species = models.ForeignKey(Species, on_delete=models.PROTECT, blank=True, null=True)  # Blank allows because some nests can't be easily identified
    location = models.CharField(max_length=255, blank=True)
    observation_time = models.DateTimeField()
    comments = models.TextField(blank=True)

    latitude = models.FloatField()
    longitude = models.FloatField()
    zone = models.ForeignKey(FirefightersZone, blank=True, null=True, on_delete=models.PROTECT)

    inaturalist_id = models.BigIntegerField(blank=True, null=True)
    inaturalist_species = models.CharField(max_length=100, blank=True, null=True)

    # Observer info
    observer_title = models.CharField(max_length=50, blank=True, null=True)
    observer_last_name = models.CharField(max_length=255, blank=True, null=True)
    observer_first_name = models.CharField(max_length=255, blank=True, null=True)
    observer_email = models.EmailField(blank=True, null=True)
    observer_phone = models.CharField(max_length=20, blank=True, null=True)
    observer_is_beekeeper = models.NullBooleanField()

    # Managers
    objects = models.Manager()  # The default manager.
    from_inat_objects = InatCreatedObservationsManager()
    from_vespawatch_objects = VespawatchCreatedObservationsManager()

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(AbstractObservation, self).__init__(*args, **kwargs)
        self.__original_species = self.species

    def auto_assign_zone(self):
        """Sets the zone attribute, according to the latitude/longitude. You'll need to manually save the model instance.

        !! overwrite existing values !!
        """
        if self.latitude and self.longitude:
            try:
                self.zone = get_zone_for_coordinates(self.latitude, self.longitude)
            except FirefightersZone.DoesNotExist:
                pass

    @property
    def can_be_edited_or_deleted(self):
        """Return True if this observation can be edited in Vespa-Watch (admin, ...)"""
        return self.originates_in_vespawatch  # We can't edit obs that comes from iNaturalist (they're never pushed).

    @property
    def species_can_be_locally_changed(self):
        if self.originates_in_vespawatch and self.exists_in_inaturalist:
            return False  # Because we rely on community: info is always pulled and never pushed

        return True

    @property
    def exists_in_inaturalist(self):
        return self.inaturalist_id is not None

    def _params_for_inat(self):
        """(Create/update): Common ground for the pushed data to iNaturalist.

        taxon_id is not part of it because we rely on iNaturalist to correct the identification, if necessary.
        All the rest is pushed.
        """

        vespawatch_evidence_value = 'nest' if self.__class__ == Nest else 'individual'

        return {'observed_on_string': self.observation_time.isoformat(),
                'time_zone': 'Brussels',
                'description': self.comments,
                'latitude': self.latitude,
                'longitude': self.longitude,
                'place_guess': self.location,

                # sets vespawatch_id (an observation field whose ID is 9613)
                'observation_field_values_attributes':
                    [{'observation_field_id': settings.VESPAWATCH_ID_OBS_FIELD_ID, 'value': self.pk},
                    {'observation_field_id': settings.VESPAWATCH_EVIDENCE_OBS_FIELD_ID, 'value': vespawatch_evidence_value}]
                }

    def update_at_inaturalist(self, access_token):
        """Update the iNaturalist observation for this obs

        :param access_token:
        :return:
        """
        p = { 'ignore_photos': 1,  # TODO: change that later if we decide to repush pictures in each time...
                'observation': self._params_for_inat()
            }

        return update_observation(observation_id=self.inaturalist_id, params=p, access_token=access_token)

    def create_at_inaturalist(self, access_token):
        """Creates a new observation at iNaturalist for this observation

        It will update the current object so self.inaturalist_id is properly set.
        On the other side, it will also set the vespawatch_id observation field so the observation can be found from
        the iNaturalist record.

        :param access_token: as returned by pyinaturalist.rest_api.get_access_token(
        """

        # TODO: push more fields
        # TODO: check the push works when optional fields are missing
        params_only_for_create = {'taxon_id': self.species.inaturalist_push_taxon_id}

        params = {
            'observation': {**params_only_for_create, **self._params_for_inat()}
        }

        r = create_observations(params=params, access_token=access_token)
        self.inaturalist_id = r[0]['id']
        self.save()


    def get_species_name(self):
        if self.species:
            return self.species.name
        else:
            return ''

    @property
    def formatted_observation_date(self):
        # We need to be aware of the timezone, hence the defaultfilter trick
        return defaultfilters.date(self.observation_time, 'Y-m-d')

    def clean(self):
        if self.species != self.__original_species and not self.species_can_be_locally_changed:
            raise ValidationError("Observation already pushed, species can't be changed anymore!")

    def save(self, *args, **kwargs):
        # Let's make sure model.clean() is called on each save(), for validation
        self.full_clean()
        self.__original_species = self.species

        if not self.zone:  # Automatically sets a zone if we don't have one.
            self.auto_assign_zone()

        return super(AbstractObservation, self).save(*args, **kwargs)


class Nest(AbstractObservation):
    duplicate_of = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('vespawatch:nest-update', kwargs={'pk': self.pk})

    def get_management_action_display(self):
        action = self.managementaction_set.first()
        return action.get_outcome_display() if action else ''

    def get_management_action(self):
        action = self.managementaction_set.first()
        return action.outcome if action else None

    def as_dict(self):
        return {
            'id': self.pk,
            'species': self.inaturalist_species if self.inaturalist_species else self.species.name,
            'subject': 'nest',
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'inaturalist_id': self.inaturalist_id,
            'observation_time': self.observation_time.timestamp() * 1000,
            'comments': self.comments,
            'imageUrls': [x.image.url for x in self.nestpicture_set.all()],
            'action': self.get_management_action_display(),
            'actionCode': self.get_management_action(),
        }

    def __str__(self):
        return f'Nest of {self.get_species_name()}, {self.formatted_observation_date}'


class Individual(AbstractObservation):
    FOURAGING = 'FO'
    HUNTING = 'HU'
    FLOWER = 'FL'
    OTHER = 'OT'
    BEHAVIOUR_CHOICES = (
        (FOURAGING, 'Fouraging'),
        (HUNTING, 'Hunting at hive'),
        (FLOWER, 'At flower'),
        (OTHER, 'Other')
    )

    # Fields
    individual_count = models.IntegerField(blank=True, null=True)
    behaviour = models.CharField(max_length=2, choices=BEHAVIOUR_CHOICES, blank=True, null=True)
    nest = models.ForeignKey(Nest, on_delete=models.CASCADE, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('vespawatch:individual-update', kwargs={'pk': self.pk})

    def as_dict(self):
        return {
            'id': self.pk,
            'species': self.inaturalist_species if self.inaturalist_species else self.species.name,
            'subject': 'individual',
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'inaturalist_id': self.inaturalist_id,
            'observation_time': self.observation_time.timestamp() * 1000,
            'comments': self.comments,
            'imageUrls': [x.image.url for x in self.individualpicture_set.all()]
        }

    def __str__(self):
        return f'Individual of {self.get_species_name()}, {self.formatted_observation_date}'


class IndividualPicture(models.Model):
    def get_file_path(instance, filename):
        return os.path.join('individual_pictures/', make_unique_filename(filename))

    observation = models.ForeignKey(Individual, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=get_file_path)


class NestPicture(models.Model):
    def get_file_path(instance, filename):
        return os.path.join('nest_pictures/', make_unique_filename(filename))

    observation = models.ForeignKey(Nest, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=get_file_path)



class ManagementAction(models.Model):
    FULL_DESTRUCTION_NO_DEBRIS = 'FD'
    PARTIAL_DESTRUCTION_DEBRIS_LEFT = 'PD'
    EMPTY_NEST_NOTHING_DONE = 'ND'

    OUTCOME_CHOICE = (
        (FULL_DESTRUCTION_NO_DEBRIS, 'Full destruction, no debris'),
        (PARTIAL_DESTRUCTION_DEBRIS_LEFT, 'Partial destruction/debris left'),
        (EMPTY_NEST_NOTHING_DONE, 'Empty nest, nothing done'),
    )

    nest = models.ForeignKey(Nest, on_delete=models.CASCADE)
    outcome = models.CharField(max_length=2, choices=OUTCOME_CHOICE)
    action_time = models.DateTimeField()
    person_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.action_time.strftime("%Y-%m-%d")} {self.get_outcome_display()} on {self.nest}'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Firefighters have a zone, other users (Admin, ...) don't.
    zone = models.ForeignKey(FirefightersZone, on_delete=models.PROTECT, null=True, blank=True)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()