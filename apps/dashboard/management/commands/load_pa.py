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

    def process_csv(self, source_data_dir, source_data_file, tmpdir="/tmp"):
        # data = pd.read_csv(os.path.join(source_data_dir, source_data_file), engine="python")
        output_filename = "processed_HOS.csv"
        output_dir = tmpdir
        output_path = os.path.join(output_dir, output_filename)
        rows = []
        with open (os.path.join(source_data_dir, source_data_file), newline='') as rf:
            reader = csv.reader(rf)
            header = True
            for row in reader:
                if header:
                    header_row = []
                    for c in row:
                        if "'" in c:
                            c = c.replace("'", "")
                        header_row.append(c)
                    rows.append(header_row)
                    header = False
                else:
                    rows.append(row)
        with open (output_path, 'w', newline='') as wf:
            writer = csv.writer(wf)
            writer.writerows(rows)
        return (output_dir, output_filename)

    def process_hospital(self):
        print("Starting load of hospital data")
        # The name of the file you created the layer service with.
        original_data_file_name = "processed_HOS.csv"

        data_dir, latest_filename = self.get_latest_file()
        processed_dir, processed_filename = self.process_csv(data_dir, latest_filename)
        print(f"Finished processing {data_dir}/{latest_filename}, file is {processed_dir}/{processed_filename}")

        state = models.State.objects.get(code='PA')
        

        print("Finished load of hospital data")
        return processed_dir, processed_filename

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
