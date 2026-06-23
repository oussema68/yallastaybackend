from django.db import migrations


def seed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.update_or_create(
        key="listing_broker_assigned",
        defaults={
            "name": "Broker assigned to landlord listing",
            "description": "Placeholders: {first_name}, {landlord_name}, {listing_title}, {listing_url}, {workspace_url}",
            "subject": "You were assigned to “{listing_title}” on Yallastay",
            "body_text": (
                "Hi {first_name},\n\n"
                "{landlord_name} assigned you as their broker on “{listing_title}”.\n\n"
                "Open the listing to add the Trakheesi permit and review owner documents:\n"
                "{listing_url}\n\n"
                "Your broker workspace:\n{workspace_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p><strong>{landlord_name}</strong> assigned you as their broker on "
                "“{listing_title}”.</p>"
                '<p><a href="{listing_url}">Open listing</a> · '
                '<a href="{workspace_url}">Broker workspace</a></p>'
                "<p>Add the Trakheesi permit when ready and review owner documents when requested.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )
    EmailTemplate.objects.update_or_create(
        key="listing_owner_linked",
        defaults={
            "name": "Landlord linked as property owner",
            "description": "Placeholders: {first_name}, {realtor_name}, {listing_title}, {listing_url}, {profile_url}",
            "subject": "You are linked as owner of “{listing_title}”",
            "body_text": (
                "Hi {first_name},\n\n"
                "{realtor_name} linked you as the property owner for “{listing_title}” on Yallastay.\n\n"
                "View the listing and upload your title deed:\n{listing_url}\n\n"
                "Your user ID is on Profile:\n{profile_url}\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi {first_name},</p>"
                "<p><strong>{realtor_name}</strong> linked you as the property owner for "
                "“{listing_title}”.</p>"
                '<p><a href="{listing_url}">View listing</a> · '
                '<a href="{profile_url}">Your Profile</a></p>'
                "<p>Upload your title deed on the listing page when you are ready.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )
    EmailTemplate.objects.update_or_create(
        key="listing_owner_invite",
        defaults={
            "name": "Realtor invites property owner",
            "description": "Placeholders: {listing_title}, {realtor_name}, {listing_url}, {signup_url}, {accept_url}",
            "subject": "{realtor_name} invited you as owner - {listing_title}",
            "body_text": (
                "Hi,\n\n"
                "{realtor_name} listed “{listing_title}” for you on Yallastay.\n\n"
                "Create a landlord account (or sign in) using the link below. "
                "We link you automatically as the property owner when you register.\n\n"
                "Register: {signup_url}\n"
                "View listing: {listing_url}\n\n"
                "Already have an account? Open the listing and tap Accept owner link.\n\n"
                " -  Yallastay"
            ),
            "body_html": (
                "<p>Hi,</p>"
                "<p><strong>{realtor_name}</strong> listed “{listing_title}” for you on Yallastay.</p>"
                '<p><a href="{signup_url}">Create landlord account</a></p>'
                '<p><a href="{listing_url}">View listing</a></p>'
                "<p>Already registered? Sign in and accept the owner link on the listing page.</p>"
                "<p> -  Yallastay</p>"
            ),
            "is_active": True,
        },
    )


def unseed_templates(apps, schema_editor):
    EmailTemplate = apps.get_model("emails", "EmailTemplate")
    EmailTemplate.objects.filter(
        key__in=[
            "listing_broker_assigned",
            "listing_owner_linked",
            "listing_owner_invite",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0011_seed_landlord_approved_template"),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed_templates),
    ]
