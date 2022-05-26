from django.db import models
from django.contrib.auth.models import User
from files.models import Kostenstelle

class FeUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    kostenstellen = models.ManyToManyField(Kostenstelle)
    class Meta:
        verbose_name = "Berechtigungen"