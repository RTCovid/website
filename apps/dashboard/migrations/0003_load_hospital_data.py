# Generated by Django 3.0.5 on 2020-04-02 14:34

from django.db import migrations
from django.conf import settings

import csv, logging, os

logging.basicConfig(level=logging.INFO)

def get_hospital_county(County, row, state):
    # Set county - requires some mucking
    logging.debug("Matching: {} ({})".format(row["County Name"], state.code))
    try:
        county = County.objects.get(state=state, name__iexact=row["County Name"])
    except County.DoesNotExist as e:
        try:
            logging.debug(" + County")
            county = County.objects.get(state=state, name__iexact=row["County Name"]+" County")
        except County.DoesNotExist as e:
            try:
                # This works if there's only one
                logging.debug(" + Startswith")
                county = County.objects.get(state=state, name__istartswith=row["County Name"])
            except County.MultipleObjectsReturned as e:
                # Tricky ones. Maybe see if only one is input + "county"?
                try:
                    logging.debug(" + County")
                    county = County.objects.get(state=state, name__istartswith=row["County Name"]+" County")
                except County.DoesNotExist as e:
                    #or Parish for Louisiana?
                    logging.debug(" + Parish")
                    county = County.objects.get(state=state, name__istartswith=row["County Name"]+" Parish")
    return county       

def load_facilities(apps, schema_editor):
    State = apps.get_model('dashboard', 'State')
    County = apps.get_model('dashboard', 'County')
    Facility = apps.get_model('dashboard', 'Facility')

    with open(
        os.path.join(settings.BASE_DIR, 'apps', 'dashboard', 'data', 'hospitals.csv'),
        encoding='utf-8-sig',
    ) as hospital_csv:
        reader = csv.DictReader(hospital_csv)
        for row in reader:
            if row['State'] in ['PR', 'VI', 'AS', 'GU', 'MP']:
                # TODO: Support Territories
                continue

            # Set state - should be reliable
            state = State.objects.get(code=row['State'])
            
            # Set county - see method
            county = get_hospital_county(County, row, state)

            # Digits only for phone number
            phone = row["Phone Number"].replace("(", "").replace("-","").replace(" ", "").replace(")","")
            logging.debug("Phone: {}".format(phone))

            # Save new Facility
            facility = Facility.objects.create(
                name=row['Facility ID'],
                cms_id=row['CMS ID'],
                county=county,
                address=row['Address'],
                city=row['City'],
                postal_code=row['ZIP Code'],
                phone=phone,
                emergency_services=True if row["Emergency Services"] == "Yes" else False,
            )

def delete_facilities(apps, schema_editor):
    Facility = apps.get_model('dashboard', 'Facility')
    Facility.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_load_countystate_data'),
    ]


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0002_load_countystate_data'),
    ]

    operations = [
        migrations.RunPython(load_facilities, delete_facilities),
    ]