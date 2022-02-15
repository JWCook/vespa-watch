# Generated by Django 2.2.24 on 2021-08-24 10:54

from django.db import migrations

def populate_actions_result(apps, schema_editor):
    ManagementAction = apps.get_model('vespawatch', 'ManagementAction')
    for action in ManagementAction.objects.all():
        old_outcome = action.old_outcome

        # !! Models constants not available, so we have to copy/paste values here.
        if old_outcome == 'PP':  # PERMAS_D_PROF:
            result = 'ST'  # Successfully treated
        elif old_outcome == 'PC':  # PERMAS_D_CLASSIC
            result = 'ST'
        elif old_outcome == 'FD':  # REMOVAL_COMPLETE
            result = 'ST'
        elif old_outcome ==  'PD':  # REMOVAL_PARTIAL:
            result = 'ST'
        elif old_outcome == 'ND': # NOT_TREATED:
            result = 'UN'
        else:  # 'unknown'
            result = 'UK'

        action.result = result
        action.save(update_fields=['result'])


def do_nothing(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('vespawatch', '0053_managementaction_result'),
    ]

    operations = [
        migrations.RunPython(populate_actions_result, do_nothing),
    ]