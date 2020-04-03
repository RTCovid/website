import csv, os, datetime, copy

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point

import pysftp

from apps.dashboard import models

class Command(BaseCommand):
    timestamp = None

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
    
    def get_timestamp_from_filename(self, filename):
        self.timestamp = datetime.datetime( 
            int(filename.split('.')[0].split('_')[2].split('-')[0]),  # year 
            int(filename.split('.')[0].split('_')[2].split('-')[1]),  # month 
            int(filename.split('.')[0].split('_')[2].split('-')[2]),  # day 
            int(filename.split('.')[0].split('_')[3].split('-')[0]),  # hour 
            int(filename.split('.')[0].split('_')[3].split('-')[1]),  # minute
            tzinfo=datetime.timezone.utc,
        )

    def process_hospital(self):
        print("Starting load of hospital data")
        # The name of the file you created the layer service with.
        original_data_file_name = "processed_HOS.csv"
        found, not_found = (0, 0)
        data_dir, latest_filename = self.get_latest_file()
        self.get_timestamp_from_filename(latest_filename)

        state = models.State.objects.get(code='PA')
        with open(os.path.join(data_dir, latest_filename)) as report_csv:
            reader = csv.DictReader(report_csv)
            for row in reader:
                if row["HospitalName"] == "2Memorial Child/Adolescent Partial Hospital Program":
                    continue
                facility = self.find_facility(row)
                if facility:
                    self.record_facility_update(facility, row)
                    found += 1
                else:
                    not_found += 1

        print("Finished load of hospital data – Found: {}, Not Found: {}".format(found, not_found))
        return processed_dir, processed_filename

    def record_facility_update(self, facility, row):
        # Make sure this facility doesn't already have this update:
        if models.FacilityMetrics.objects.filter(facility=facility, timestamp=self.timestamp).count():
            return
        
        NON_ADDITIONAL_DATA_FIELDS = [
            "HospitalName",
            "HospitalStreetAddress",
            "HospitalCity",
            "HospitalState",
            "HospitalZip",
            "HospitalLatitude",
            "HospitalLongitude",
            "Available Beds-Medical and Surgical (Med/Surg) Staffed Beds",
            "Available Beds-Medical and Surgical (Med/Surg) Current Available",
            "Available Beds-Adult Intensive Care Unit (ICU) Staffed Beds",
            "Available Beds-Adult Intensive Care Unit (ICU) Current Available",
            "Ventilator Counts-Ventilators Number of ventilators",
            "Ventilator Counts-Ventilators Number of ventilators in use",
            "At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-3 or less days Response ?",
            "At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-4-7 days Response ?",
            "At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-8-14 days Response ?",
            "At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-15-28 days Response ?",
            "At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-29 or more days Response ?",
            "At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-3 or less days Response ?",
            "At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-4-7 days Response ?",
            "At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-8-14 days Response ?",
            "At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-15-28 days Response ?",
            "At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-29 or more days Response ?",
        ]

        n95 = None
        if row["At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-3 or less days Response ?"] == 'Y':
            n95 = 2
        elif row["At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-4-7 days Response ?"] == 'Y':
            n95 = 2
        elif row["At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-8-14 days Response ?"] == 'Y':
            n95 = 1
        elif row["At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-15-28 days Response ?"] == 'Y':
            n95 = 1
        elif row["At current utilization rates how long do you expect your current supply of N95 respirators to last at your facility?-29 or more days Response ?"] == 'Y':
            n95 = 0
        
        ppe = None
        if row["At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-3 or less days Response ?"] == "Y":
            ppe = 2
        elif row["At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-4-7 days Response ?"] == "Y":
            ppe = 2
        elif row["At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-8-14 days Response ?"] == "Y":
            ppe = 1
        elif row["At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-15-28 days Response ?"] == "Y":
            ppe = 1
        elif row["At current utilization rates how long do you expect your current supply of other PPE (gowns gloves etc) to last at your facility?-29 or more days Response ?"] == "Y":
            ppe = 0

        additional_data = copy.deepcopy(row)
        for key in NON_ADDITIONAL_DATA_FIELDS:
            del additional_data[key]

        med_beds_capacity = row["Available Beds-Medical and Surgical (Med/Surg) Staffed Beds"]
        med_beds_capacity = int(med_beds_capacity) if med_beds_capacity else None

        med_beds_used = row["Available Beds-Medical and Surgical (Med/Surg) Current Available"]
        med_beds_used = int(med_beds_used) if med_beds_used else None

        icu_beds_capacity = row["Available Beds-Adult Intensive Care Unit (ICU) Staffed Beds"]
        icu_beds_capacity = int(icu_beds_capacity) if icu_beds_capacity else None

        icu_beds_used = row["Available Beds-Adult Intensive Care Unit (ICU) Current Available"]
        icu_beds_used = int(icu_beds_used) if icu_beds_used else None

        ventilators_capacity = row["Ventilator Counts-Ventilators Number of ventilators"]
        ventilators_capacity = int(ventilators_capacity) if ventilators_capacity else None

        ventilators_used = row["Ventilator Counts-Ventilators Number of ventilators in use"]
        ventilators_used = int(ventilators_used) if ventilators_used else None

        c19_patients = row["COVID-19 Patient Counts-Total number of inpatients diagnosed with COVID-19: "]
        c19_patients = int(c19_patients) if c19_patients else None

        c19_vent_patients = row["COVID-19 Patient Counts-Total number of patients diagnosed with COVID-19 on ventilators: "]
        c19_vent_patients = int(c19_vent_patients) if c19_vent_patients else None

        models.FacilityMetrics.objects.create(
            facility=facility,
            timestamp=self.timestamp,

            med_beds_capacity=med_beds_capacity,
            med_beds_used=med_beds_used,
            icu_beds_capacity=icu_beds_capacity,
            icu_beds_used=icu_beds_used,
            ventilators_capacity=ventilators_capacity,
            ventilators_used=ventilators_used,

            c19_patients=c19_patients,
            c19_vent_patients=c19_vent_patients,

            supply_n95respirators=n95,
            supply_facemasks=ppe,
            supply_gloves=ppe,
            supply_faceshields=ppe,
            supply_gowns=ppe,

            additional_data=additional_data,
        )


    def find_facility(self, row):
        try:
            # Let's use the lookup table!
            facility = models.Facility.objects.get(cms_id=FACILITY_MAPPING[row["HospitalName"]])
        except KeyError:
            facility = None

        # try:
        #     facility = models.Facility.objects.get(name__iexact=row["HospitalName"], county__state__code="PA")
        #     # print("Found!", row["HospitalName"], ": ", facility.name)
        #     print("\"{}\": \"{}\",  # {}".format(
        #                 row["HospitalName"],
        #                 facility.cms_id,
        #                 facility.name
        #             ))
        # except models.Facility.DoesNotExist:
        #     try:
                
        #     except KeyError:
        #         # Let's try pegging against location
        #         try:
        #             p = Point(float(row["HospitalLongitude"]), float(row["HospitalLatitude"]))
        #             facility = models.Facility.objects.get(location__distance_lte=(
        #                 p,
        #                 D(m=250), # 250-meter slush for geocoding differences
        #             ), location__distance_gte=(
        #                 p,
        #                 D(m=49), # 250-meter slush for geocoding differences                        
        #             ))
                    
        #             return None
        #         except models.Facility.DoesNotExist:
        #             # print("Not Found: {} ({})".format(row["HospitalName"], row["HospitalZip"].rstrip()))
        #             return None
        #         except models.Facility.MultipleObjectsReturned:
        #             # print("Choose more", row["HospitalName"])
        #             return None

            # try:
            #     facility = models.Facility.objects.get(
            #         county__state__code="PA",
            #         postal_code__iexact=row["HospitalZip"].rstrip(),
            #     )
            #     print("Found?", row["HospitalName"], ": ", facility.name)
            # except models.Facility.DoesNotExist:
            #     print("Not Found: {} ({})".format(row["HospitalName"], row["HospitalZip"].rstrip()))
            #     return None
            # except models.Facility.MultipleObjectsReturned:
            #     print("Choose more", row["HospitalName"])
            #     return None
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

FACILITY_MAPPING = {
    "Abington Memorial Hospital": "390231",  # Abington Memorial Hospital
    "Albert Einstein Medical Center": "390142",  # Albert Einstein Medical Center
    "Barix Clinics of Pennsylvania": "390302",  # Barix Clinics Of Pennsylvania
    "Berwick Hospital Center": "390072",  # Berwick Hospital Center
    "Brooke Glen Behavioral Hospital": "394049",  # Brooke Glen Behavioral Hospital
    "Bucktail Medical Center": "391304",  # Bucktail Medical Center
    "Butler Memorial Hospital": "390168",  # Butler Memorial Hospital
    "Cancer Treatment Centers of America": "390312",  # Cancer Treatment Centers Of America
    "Chambersburg Hospital": "390151",  # Chambersburg Hospital
    "Chester County Hospital": "390179",  # Chester County Hospital
    "Chestnut Hill Hospital": "390026",  # Chestnut Hill Hospital
    "Children's Hospital of Philadelphia": "393303",  # Children'S Hospital Of Philadelphia
    "Clarion Hospital": "390093",  # Clarion Hospital
    "Clarion Psychiatric Center": "394043",  # Clarion Psychiatric Center
    "Clarks Summit State Hospital": "394012",  # Clarks Summit State Hospital
    "Conemaugh Memorial Medical Center": "390110",  # Conemaugh Memorial Medical Center
    "Danville State Hospital": "394004",  # Danville State Hospital
    "Delaware County Memorial Hospital": "390081",  # Delaware County Memorial Hospital
    "Doylestown Hospital": "390203",  # Doylestown Hospital
    "Eagleville Hospital": "390278",  # Eagleville Hospital
    "Easton Hospital": "390162",  # Easton Hospital
    "Edgewood Surgical Hospital": "390307",  # Edgewood Surgical Hospital
    "Evangelical Community Hospital": "390013",  # Evangelical Community Hospital
    "Fairmount Behavioral Health System": "394027",  # Fairmount Behavioral Health System
    "First Hospital of Wyoming Valley": "394039",  # First Hospital Of Wyoming Valley
    "Foundations Behavioral Health": "394038",  # Foundations Behavioral Health
    "Friends Hospital": "394008",  # Friends Hospital
    "Fulton County Medical Center": "391303",  # Fulton County Medical Center
    "Geisinger Medical Center": "390006",  # Geisinger Medical Center
    "Geisinger Wyoming Valley Medical Center": "390270",  # Geisinger Wyoming Valley Medical Center
    "Gettysburg Hospital": "390065",  # Gettysburg Hospital
    "Grand View Hospital": "390057",  # Grand View Hospital
    "Grove City Medical Center": "390266",  # Grove City Medical Center
    "Lehigh Valley Hospital - Hazleton": "390185",  # Lehigh Valley Hospital - Hazleton
    "Highlands Hospital": "390184",  # Highlands Hospital
    "Horsham Clinic": "394034",  # Horsham Clinic
    "UPMC Jameson": "390016",  # Upmc Jameson
    "Jeanes Hospital": "390080",  # Jeanes Hospital
    "Kensington Hospital": "390025",  # Kensington Hospital
    "Lancaster General Hospital": "390100",  # Lancaster General Hospital
    "Lansdale Hospital": "390012",  # Lansdale Hospital
    "Geisinger-Lewistown Hospital": "390048",  # Geisinger-Lewistown Hospital
    "Lower Bucks Hospital": "390070",  # Lower Bucks Hospital
    "Meadows Psychiatric Center": "394040",  # Meadows Psychiatric Center
    "Meadville Medical Center": "390113",  # Meadville Medical Center
    "Millcreek Community Hospital": "390198",  # Millcreek Community Hospital
    "Milton S Hershey Medical Center": "390256",  # Milton S Hershey Medical Center
    "Moses Taylor Hospital": "390119",  # Moses Taylor Hospital
    "Mount Nittany Medical Center": "390268",  # Mount Nittany Medical Center
    "Conemaugh Nason Medical Center": "390062",  # Conemaugh Nason Medical Center
    "Nazareth Hospital": "390204",  # Nazareth Hospital
    "Norristown State Hospital": "394001",  # Norristown State Hospital
    "Pennsylvania Hospital": "390226",  # Pennsylvania Hospital
    "Pennsylvania Psychiatric Institute": "394051",  # Pennsylvania Psychiatric Institute
    "Phoenixville Hospital": "390127",  # Phoenixville Hospital
    "Regional Hospital of Scranton": "390237",  # Regional Hospital Of Scranton
    "Riddle Memorial Hospital": "390222",  # Riddle Memorial Hospital
    "Roxbury Treatment Center": "394050",  # Roxbury Treatment Center
    "Sacred Heart Hospital": "390197",  # Sacred Heart Hospital
    "Roxborough Memorial Hospital": "390304",  # Roxborough Memorial Hospital
    "UPMC Somerset": "390039",  # Upmc Somerset
    "Surgical Institute of Reading": "390316",  # Surgical Institute Of Reading
    "Temple University Hospital": "390027",  # Temple University Hospital
    "Thomas Jefferson University Hospital": "390174",  # Thomas Jefferson University Hospital
    "Torrance State Hospital": "394026",  # Torrance State Hospital
    "Tyler Memorial Hospital": "390192",  # Tyler Memorial Hospital
    "UPMC Hamot": "390063",  # Upmc Hamot
    "Warren General Hospital": "390146",  # Warren General Hospital
    "Warren State Hospital": "394016",  # Warren State Hospital
    "Wayne Memorial Hospital": "390125",  # Wayne Memorial Hospital
    "Waynesboro Hospital": "390138",  # Waynesboro Hospital
    "Wernersville State Hospital": "394014",  # Wernersville State Hospital
    "Wilkes-Barre General Hospital": "390137",  # Wilkes-Barre General Hospital
    "Wills Eye Hospital": "390331",  # Wills Eye Hospital
    "York Hospital": "390046",  # York Hospital

    "Blue Mountain Hospital-Gnaden Huetten Campus (L)": "390194",  # St Luke'S Hospital-Gnaden Huetten Campus
    "UPMC Pinnacle Carlisle": "390058",  # Carlisle Regional Medical Center
    "UPMC Cole Memorial Hospital": "391313",  # Upmc Cole
    "Geisinger Community Medical Center": "390001",  # Geisinger-Community Medical Center
    "Pennhighlands Dubois": "390086",  # Penn Highlands Dubois
    "UPMC-Pinnacle-Hanover": "390233",  # Upmc Pinnacle Hanover
    "Geisinger-Holy Spirit Hospital": "390004",  # Holy Spirit Hospital
    "UPMC-Kane": "390104",  # Upmc Kane
    "Pottstown Memorial Medical Center": "390123",  # Pottstown Hospital
    "AHN-Saint Vincent Hospital": "390009",  # Saint Vincent Hospital
    "LVHN-Schuylkill Medical Center-South Jackson": "390030",  # Lehigh Valley Hospital-Schuylkill S. Jackson Stree
    "Sharon Regional Medical Center": "390211",  # Sharon Regional Health System
    "Shriners Hospital For Children Philadelphia": "393309",  # Shriners Hospitals For Children - Philadelphia
    "St. Luke's - Monroe Campus": "390330",  # St Luke'S Hospital - Monroe Campus
    "St. Luke's Quakertown Campus": "390035",  # St Luke'S Quakertown Hospital
    "UPMC-Mercy": "390028",  # Upmc Mercy
    "UPMC-Pinnacle-Hanover": "390233",  # Upmc Pinnacle Hanover
    "UPMC-Presbyterian": "390164",  # Upmc Presbyterian Shadyside
    "Washington Hospital": "390042",  # Washington Hospital, The
    "AHN-West Penn Hospital": "390090",  # West Penn Hospital
    "Westmoreland Hospital": "390145",  # Excela Health Westmoreland Hospital
    "UPMC Susquehanna Williamsport Hospital": "390045",  # Williamsport Regional Medical Center
    "AHN-Allegheny General Hospital": "390050",  # Allegheny General Hospital
    "AHN-Allegheny Valley Hospital": "390032",  # Allegheny Valley Hospital
    "UPMC-Altoona": "390073",  # Upmc Altoona
    "Jefferson - Torresdale Hospital": "390115",  # Aria Health
    "Armstrong County Memorial": "390163",  # Acmh Hospital
    "Geisinger Bloomsburg Hospital": "390003",  # Geisinger-Bloomsburg Hospital
    "Pennhighlands Brookville": "391312",  # Penn Highlands Brookville
    "Children's Hospital of Pittsburgh of UPMC": "393302",  # Upmc Children'S Hospital Of Pittsburgh
    "Pennhighlands Clearfield": "390052",  # Penn Highlands Clearfield
    "Coordinated Health Orthopedic Hospital LLC": "390314",  # Coordinated Health Orthopedic Hospital
    "Crozer-Chester Medical Center": "390180",  # Crozer Chester Medical Center
    "Einstein Medical Center-Montgomery Hospital": "390329",  # Einstein Medical Center Montgomery
    "Wellspan Ephrata Hospital": "390225",  # Wellspan Ephrata Community Hospital
    "Washington Health System - Greene": "390150",  # Washington Health System Greene
    "Frick Hospital": "390217",  # Excela Health Frick Hospital
    "Haven Behavioral Hospital Reading": "394052",  # Haven Behavioral Hospital Of Eastern Pennsylvania
    "UPMC-Pinnacle Lititz": "390068",  # Upmc Lititz
    "Heritage Valley Med Cntr Sewickley": "390037",  # Heritage Valley Sewickley
    "Indiana Hospital": "390173",  # Indiana Regional Medical Center
    "Jennersville Hospital West Grove": "390220",  # Jennersville Hospital
    " Geisinger Jersey Shore Hospital": "391300",  # Geisinger Jersey Shore Hospital
    "Latrobe Hospital": "390219",  # Excela Health Latrobe Hospital
    "Lifecare Behavioral Health Pittsburgh": "394054",  # Lifecare Behavioral Health Hospital
    "UPMC Susquehanna Lock Haven Hospital": "390071",  # Lock Haven Hospital
    "Magee-Womens Hospital UPMC": "390114",  # Magee Womens Hospital Of Upmc Health System
    "Main Line-Bryn Mawr Hospital": "390139",  # Main Line Hospital Bryn Mawr Campus
    "Guthrie Towanda Memorial Hospital ": "390236",  # Guthrie Towanda Memorial Hospital
    "Suburban Community Hospital-Norristown": "390116",  # Suburban Community Hospital
    "Milton S Hershey Medical Center-Transplant Center": "390256",  # Milton S Hershey Medical Center
    "Miners Hospital": "390130",  # Conemaugh Miners Medical Center
    "UPMC Susquehanna Muncy Valley Hospital": "391301",  # Upmc Susquehanna Muncy
    "Ohio Valley": "390157",  # Ohio Valley General Hospital
    "Physicians Care Surgical Hospital ": "390324",  # Physician'S Care Surgical Hospital
    "Lehigh Valley Hospital-Pocono (L)": "390201",  # Lehigh Valley Hospital - Pocono
    "Presbyterian Med Center-Univ of Pa Hlth Sys": "390223",  # Penn Presbyterian Medical Center
    "Punxsutawney Area Hospital Inc": "390199",  # Punxsutawney Area Hospital
    "Guthrie Robert Packer Hospital": "390079",  # Robert Packer Hospital
    "St. Christophers Hospital for Children": "393307",  # St Christopher'S Hospital For Children
    "St. Clair Memorial": "390228",  # St Clair Hospital
    "St. Lukes Hospital-Bethlehem": "390049",  # St Luke'S Hospital Bethlehem
    "St. Lukes-Miners": "390183",  # St Luke'S Miners Memorial Hospital
    "Titusville Area Hospital": "391314",  # Titusville Hospital
    "Triumph Hospital Easton": "390162",  # Easton Hospital
    "Tyrone Hospital": "391307",  # Tyrone Regional Health Network
    "Uniontown": "390041",  # Uniontown Hospital
    "UPMC-East": "390328",  # Upmc East
    "UPMC-Horizon Shenango Valley": "390178",  # Upmc Horizon
    "UPMC-McKeesport": "390002",  # Upmc Mckeesport
    "UPMC-Western Psych": "390164",  # Upmc Presbyterian Shadyside
    "Windber Hospital": "390112",  # Chan Soon- Shiong Medical Center At Windber
}

UNKNOWNS = {
    "Child/Adolescent IP Service Lines": "394051",  # Pennsylvania Psychiatric Institute
    "Children's Hospital of Pittsburgh-Transplant Center": "390164",  # Upmc Presbyterian Shadyside
    "Corry Memorial Hospital": "390184",  # Highlands Hospital
    "Encompass Rehab Hospital of Erie": "390063",  # Upmc Hamot
    "Geisinger Encompass Health Rehabilitation Hospital": "390006",  # Geisinger Medical Center
    "Geisinger Medical Center-Transplant Center": "390006",  # Geisinger Medical Center
    "Hahnemann University Hospital-Transplant Center": "390290",  # Hahnemann University Hospital
    "Indiana Ambulatory Surgical Associates": "390173",  # Indiana Regional Medical Center
    "Kindred Hospital-Delaware County": "390156",  # Mercy Catholic Medical Center- Mercy Fitzgerald
    "Kindred Hospital-Wyoming Valley": "390137",  # Wilkes-Barre General Hospital
    "Magee Rehabilitation Hospital": "390290",  # Hahnemann University Hospital
    "Adult IP Service Lines ": "394051",  # Pennsylvania Psychiatric Institute
    "UPMC Pinnacle-Transplant Center": "390067",  # Pinnacle Health Hospitals
    "Select Medical Harrisburg": "394051",  # Pennsylvania Psychiatric Institute
    "Select Specialty Hospital Laurel Highlands Inc": "390219",  # Excela Health Latrobe Hospital
    "Select Specialty Hospital-Camp Hill": "390004",  # Holy Spirit Hospital
    "Select Specialty Hospital-Danville": "390006",  # Geisinger Medical Center
    "Select Specialty Hospital-York": "390046",  # York Hospital
    "Temple University Hospital-Transplant Center": "390027",  # Temple University Hospital
    "Penn State Hershey Rehabilitation LLC": "394051",  # Pennsylvania Psychiatric Institute
    "Montgomery County MH/MR Emergency Services Inc.": "390329",  # Einstein Medical Center Montgomery
    "Moss Rehabilitation Hospital": "390142",  # Albert Einstein Medical Center
    "Northwestern Institute of Psychiatry": "394049",  # Brooke Glen Behavioral Hospital
}