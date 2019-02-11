# Generated by Django 2.1.5 on 2019-02-01 11:58

from django.db import migrations, models


def transform_required_permission_to_see_field(apps, schema_editor):
    """
    Sets new access_level of states to EXTENDED_MANAGERS_AND_SUBMITTER
    if required_permission_to_see is given
    """
    # We get the model from the versioned app registry;
    # if we directly import it, it will be the wrong version.
    State = apps.get_model("motions", "State")
    for state in State.objects.all():
        if state.required_permission_to_see:
            state.access_level = 1
            state.save(skip_autoupdate=True)


class Migration(migrations.Migration):

    dependencies = [("motions", "0020_auto_20190119_1425")]

    operations = [
        migrations.AddField(
            model_name="state",
            name="access_level",
            field=models.IntegerField(
                choices=[
                    (0, "All users with permission to see motions"),
                    (
                        1,
                        "Submitters, managers and users with permission to manage metadata",
                    ),
                    (2, "Only managers and users with permission to manage metadata"),
                    (3, "Only managers"),
                ],
                default=0,
            ),
        ),
        migrations.RunPython(transform_required_permission_to_see_field),
        migrations.RemoveField(model_name="state", name="required_permission_to_see"),
    ]