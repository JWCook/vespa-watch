import datetime
import logging
import time
from json import JSONDecodeError

from constance import config
from django.conf import settings
import pyinaturalist
from django.core.mail import send_mail
from html2text import html2text
from pyinaturalist.exceptions import ObservationNotFound
from pyinaturalist.node_api import get_all_observations, get_observation
from pyinaturalist.rest_api import get_access_token, delete_observation
from requests import HTTPError, ReadTimeout

from vespawatch.management.commands._utils import VespaWatchCommand
from vespawatch.models import Individual, Nest, InatObsToDelete, get_local_observation_with_inaturalist_id, \
    create_observation_from_inat_data, get_missing_at_inat_observations, TaxonMatchError

OBSERVATION_MODELS = [Individual, Nest]

USER_AGENT = f'VespaWatch (using Pyinaturalist {pyinaturalist.__version__})'


def send_email_to_reporter(obs):
    to_email = obs.observer_email
    subject = settings.EMAIL_TO_REPORTER_SUBJECT
    body = settings.EMAIL_TO_REPORTER_BODY.format(
        observer_name=' ' + obs.observer_name if type(obs.observer_name) is str else '',
        inat_id=obs.inaturalist_id
    )

    send_mail(subject=subject, message=html2text(body), from_email=settings.EMAIL_TO_REPORTER_SENDER,
              recipient_list=[to_email], fail_silently=True, html_message=body)


class Command(VespaWatchCommand):
    help = 'Synchronize VespaWatch and iNaturalist. Full description: https://github.com/inbo/vespa-watch/issues/2'
    email_client = None

    def add_arguments(self, parser):
        parser.add_argument('--pushonly', type=bool, default=False)

    def push_deletes(self, access_token):
        """
        Delete objects on iNaturalist that were deleted on vespawatch
        """
        self.w("1. Delete the nests and individuals that are deleted in VW")

        for obs in InatObsToDelete.objects.all():
            self.w(f"Deleting iNaturalist observation #{obs.inaturalist_id}...", ending='')
            try:
                delete_observation(observation_id=obs.inaturalist_id, access_token=access_token)
                obs.delete()  # Only delete locally if the API call succeeded
            except JSONDecodeError:
                # (temporary?) iNaturalist API issue. Just log a warning. We will try to delete the observation
                # at the next sync
                logging.warning(f'Delete observation {obs.inaturalist_id} raised a JSONDecodeError')
            except ObservationNotFound:
                logging.warning(f"Observation {obs.inaturalist_id} could not be deleted on iNaturalist because it doesn't exist")
                obs.delete()  # Delete it to make sure we don't try to push this delete again
            self.w("OK")

    def push_created(self, access_token):
        """
        Create objects on iNaturalist that were newly created at vespawatch
        and don't have a iNaturalist id yet
        """
        self.w("2. Push the nest and individuals that originate in VW")

        local_observations_from_vespawatch = []
        for Model in OBSERVATION_MODELS:
            local_observations_from_vespawatch = local_observations_from_vespawatch + list(Model.new_vespawatch_objects.all())
        self.w(f"2.1 We currently have {len(local_observations_from_vespawatch)} local observations that originate in VW. Push each of them")

        for obs in local_observations_from_vespawatch:
            self.w(f"... Creating {obs.subject} #{obs.pk} on iNaturalist")
            try:
                obs.create_at_inaturalist(access_token=access_token, user_agent=USER_AGENT)
                send_email_to_reporter(obs)
            except HTTPError:
                self.w('HTTP Error received, check logs.')
                logging.exception("HTTPError while pushing observation.")

    def pull(self):
        """
        Pull all observations from iNaturalist.
        If we don't have an observation with that iNaturalist ID, create one (check the vespawatch-evidence field to
        determine whether we should create a Nest or an Individual)
        If we do have an observation with that iNaturalist ID, update it.
        """
        self.w("\n3. Pull all observations from iNaturalist (based on the project)")
        observations = get_all_observations(project_id=settings.VESPAWATCH_PROJECT_ID)
        pulled_inat_ids = []
        for inat_observation_data in observations:
            pulled_inat_ids.append(inat_observation_data['id'])
            local_obs = get_local_observation_with_inaturalist_id(inat_observation_data['id'])
            if local_obs is None:
                # This is a new one. Check vespawatch-evidence and create a nest or individual
                self.w(f"iNaturalist observation with ID #{inat_observation_data['id']} is not yet known, we'll create it locally...", ending='')
                create_observation_from_inat_data(inat_observation_data)  #TODO: check all the required fields are set
                self.w("OK")
            else:
                # We already have an observation for this id. Update it
                self.w(f'updating observation {type(local_obs).__name__} {local_obs.pk}')
                local_obs.update_from_inat_data(inat_observation_data)
        return pulled_inat_ids

    def check_missing_obs(self, observation):
        """
        Get the observation data from iNaturalist and update the observation.
        If that yields an ObservationNotFound error, the observation was deleted at iNaturalist and should be
        deleted at vespawatch too. Otherwise, check which field (project id or taxon) changed that caused
        the observation to no longer match the filter criteria. Flag the observation with the appropriate warning.
        """
        try:
            self.w(f"DEBUG: will perform a get_observation() for obs #{observation.pk} (iNaturalist ID: {observation.inaturalist_id})")
            inat_obs_data = get_observation(observation.inaturalist_id)
            # Let's slow down things a bit to avoid API errors
            time.sleep(1)
            self.w(f"\n... obs {observation.pk} still exists at iNat, it's just not part of the project anymore. Flag and update it.")
            observation.flag_based_on_inat_data(inat_obs_data)
            observation.update_from_inat_data(inat_obs_data)
        except TaxonMatchError:
            self.w(f"DEBUG: we got a TaxonMatchError on observation {observation.pk}.. Why?")
        except ObservationNotFound:
            self.w(f"\n... obs {observation.pk} was not found. Deleting it.")
            observation.delete()
        except JSONDecodeError:
            self.w(f"DEBUG: iNaturalist API returned an error while getting obs {observation.pk}.. Why?")
            # TODO: what should we do now? delete also locally? or is it a transient error?
        except ReadTimeout:
            self.w(f"DEBUG: got a time out from iNaturalist API while getting obs {observation.pk}.. Why?")

    def check_all_missing(self, missing_inat_ids):
        """
        Get all observations from vespawatch that have an iNaturalist id, but are not found in the
        data of the iNaturalist pull. Check the observations one by one.
        """
        missing_obs = get_missing_at_inat_observations(missing_inat_ids)
        self.w(f"\n4. Check the observations (count: {len(missing_obs)}) that we know locally but were not returned from iNaturalist (not part of the project anymore? deleted?)")

        for obs in missing_obs:
            self.w(f'   observation {type(obs).__name__} {obs.pk} was missing')
            self.check_missing_obs(obs)

    def handle(self, *args, **options):
        pyinaturalist.user_agent = USER_AGENT

        if settings.INATURALIST_PUSH:
            token = get_access_token(username=settings.INAT_USER_USERNAME, password=settings.INAT_USER_PASSWORD,
                                     app_id=settings.INAT_APP_ID,
                                     app_secret=settings.INAT_APP_SECRET)
        else:
            token = None

        if settings.INATURALIST_PUSH:
            self.push_deletes(token)
            self.push_created(token)
        else:
            self.w("Not pushing objects because of settings.INATURALIST_PUSH")

        if not options['pushonly']:
            pulled_inat_ids = self.pull()
            self.check_all_missing(pulled_inat_ids)

            config.LAST_PULL_COMPLETED_AT = datetime.datetime.now()
        self.w("\nInaturalist sync successfully completed.\n")
