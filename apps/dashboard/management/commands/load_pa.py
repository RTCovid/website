import csv, os

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import pysftp

from apps.dashboard import models

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        print("Started ingestion processing run")
        processed_dir, processed_filename = self.process_hospital()
        # process_supplies(creds, processed_dir, processed_filename)
        print("Finished ingestion processing run")

    def get_latest_file(self, target_dir="/tmp", prefix="HOS_ResourceCapacity"):
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys.load(os.path.join(settings.BASE_DIR, 'config', 'states', 'copaftp.pub'))
        username = os.environ.get('PA_SFTP_USER')
        password = os.environ.get('PA_SFTP_PASS')
        host = os.environ.get('PA_SFTP_HOST')
        latest_filename = ""
        with pysftp.Connection(host, username=username, password=password, cnopts=cnopts) as sftp:
            files = sftp.listdir()
            files = [f for f in files if f.startswith("HOS_ResourceCapacity")]
            # the files are sorted by the pysftp library, and the last element of the list is the latest file
            # Filenames look like HOS_ResourceCapacity_2020-03-30_00-00.csv
            # And timestamps are in UTC
            latest_filename = files[-1]
            print(f"The latest file is: {latest_filename}")
            sftp.get(latest_filename, f'{target_dir}/{latest_filename}')
            print(f"Finished downloading {target_dir}/{latest_filename}")
        return (target_dir, latest_filename)

    def process_hospital(self):
        print("Starting load of hospital data")
        # The name of the file you created the layer service with.
        original_data_file_name = "processed_HOS.csv"
        found, not_found = (0, 0)
        data_dir, latest_filename = self.get_latest_file()

        state = models.State.objects.get(code='PA')
        with open(os.path.join(data_dir, latest_filename)) as report_csv:
            reader = csv.DictReader(report_csv)
            for row in reader:
                if row["HospitalName"] == "2Memorial Child/Adolescent Partial Hospital Program":
                    continue
                facility = self.find_facility(row)
                if facility:
                    found += 1
                else:
                    not_found += 1

        print("Finished load of hospital data – Found: {}, Not Found: {}".format(found, not_found))
        return processed_dir, processed_filename

    def find_facility(self, row):
        try:
            facility = models.Facility.objects.get(name__iexact=row["HospitalName"], county__state__code="PA")
        except models.Facility.DoesNotExist:
            try:
                facility = models.Facility.objects.get(
                    county__state__code="PA",
                    postal_code__iexact=row["HospitalZip"].rstrip(),
                )
                print("Found?", row["HospitalName"], ": ", facility.name)
            except models.Facility.DoesNotExist:
                print("Not Found: {} ({})".format(row["HospitalName"], row["HospitalZip"].rstrip()))
                return None
            except models.Facility.MultipleObjectsReturned:
                print("Choose more", row["HospitalName"])
                return None
        return facility

    def process_supplies(self, processed_dir, processed_filename):
        print("Starting load of supplies data")
        original_data_file_name = "supplies.csv"
        arcgis_supplies_item_id = "8fad710d5df6434f8567373979dd9dbe"
        supplies_filename = "supplies.csv"

        df = load_csv_to_df(os.path.join(processed_dir, processed_filename))
        supplies = create_supplies_table(df)

        supplies.to_csv(os.path.join(processed_dir, supplies_filename), index=False)

        status = upload_to_arcgis(creds, processed_dir, supplies_filename, 
                                original_data_file_name, arcgis_supplies_item_id)
        print(status)
        print("Finished load of supplies data")
