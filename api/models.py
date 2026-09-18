from django.db import models


class Lease(models.Model):
    acres = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    email = models.EmailField()
    product = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    location = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ContactMessage(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)