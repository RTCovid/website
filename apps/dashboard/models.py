from django.contrib.gis.db import models
from django.contrib.postgres import fields as pg_fields
from django.urls import reverse
from django.utils.text import slugify


class State(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=2, db_index=True)
    population = models.IntegerField(blank=True)

    def get_absolute_url(self):
        kwargs = {
            'code': self.code,
        }
        return reverse('state', kwargs=kwargs)


class County(models.Model):
    state = models.ForeignKey('State', on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    population = models.IntegerField(blank=True)

    def save(self, *args, **kwargs):
        value = self.name
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        kwargs = {
            'state_code': self.state.code,
            'slug': self.slug,
        }
        return reverse('county', kwargs=kwargs)


class Facility(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    short_name = models.CharField(max_length=50, blank=True)
    cms_id = models.IntegerField(blank=True, db_index=True)

    address = models.CharField(max_length=200)
    city = models.CharField(max_length=50)
    county = models.ForeignKey('County', on_delete=models.PROTECT)
    postal_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=10)

    location = models.PointField(geography=True)

    emergency_services = models.BooleanField()

    def save(self, *args, **kwargs):
        value = self.short_name if self.short_name else self.name
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        kwargs = {
            'state_code': self.county.state.code,
            'county_slug': self.county.slug,
            'cms_id': self.cms_id,
            'slug': self.slug,
        }
        return reverse('facility', kwargs=kwargs)



class FacilityMetrics(models.Model):
    COVERED = 0
    CONCERNED = 1
    CRITICAL = 2
    SEVERITY_CHOICES = [
        (COVERED, 'Covered'),
        (CONCERNED, 'Concerned'),
        (CRITICAL, 'Critical'),
    ]

    facility = models.ForeignKey('Facility', on_delete=models.CASCADE)
    timestamp = models.DateTimeField()

    med_beds_capacity = models.IntegerField(blank=True)
    med_beds_used = models.IntegerField(blank=True)
    icu_beds_capacity = models.IntegerField(blank=True)
    icu_beds_used = models.IntegerField(blank=True)
    ventilators_capacity = models.IntegerField(blank=True)
    ventilators_used = models.IntegerField(blank=True)

    c19_patients = models.IntegerField(blank=True)
    c19_vent_patients = models.IntegerField(blank=True)
    c19_hospital_onset_patients = models.IntegerField(blank=True)
    c19_awaiting_bed = models.IntegerField(blank=True)
    c19_vent_awaiting_bed = models.IntegerField(blank=True)
    c19_deaths = models.IntegerField(blank=True)

    supply_n95respirators = models.IntegerField(choices=SEVERITY_CHOICES)
    supply_facemasks = models.IntegerField(choices=SEVERITY_CHOICES)
    supply_gloves = models.IntegerField(choices=SEVERITY_CHOICES)
    supply_faceshields = models.IntegerField(choices=SEVERITY_CHOICES)
    supply_gowns = models.IntegerField(choices=SEVERITY_CHOICES)

    staffing_physicians = models.IntegerField(choices=SEVERITY_CHOICES)
    staffing_nurses = models.IntegerField(choices=SEVERITY_CHOICES)
    staffing_ancillady = models.IntegerField(choices=SEVERITY_CHOICES)

    additional_data = pg_fields.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
