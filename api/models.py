import uuid

from django.db import models
from django.conf import settings


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    auth_version = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user.email


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


class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages', null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField()
    is_admin = models.BooleanField(default=False)
    is_ai = models.BooleanField(default=False)
    admin_name = models.CharField(max_length=200, blank=True)
    admin_avatar = models.URLField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} — {self.created_at:%Y-%m-%d %H:%M}'


class AdminPresence(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_presence')
    last_seen = models.DateTimeField(auto_now=True)
    identity_name = models.CharField(max_length=200, blank=True)
    identity_avatar = models.URLField(blank=True)
    current_page = models.CharField(max_length=255, blank=True)
    last_page = models.CharField(max_length=255, blank=True)


class AdminRecoveryCodes(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_recovery_codes')
    code_hashes = models.JSONField(default=list, blank=True)
    identity_code_hashes = models.JSONField(default=dict, blank=True)


class AdminActivity(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_activities')
    actor_username = models.CharField(max_length=150, blank=True)
    identity_name = models.CharField(max_length=200)
    action = models.CharField(max_length=200)
    page = models.CharField(max_length=255, blank=True)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BlogPost(models.Model):
    CATEGORY_CHOICES = (
        ('News', 'News'),
        ('Impact', 'Impact'),
        ('Industry', 'Industry'),
        ('Company', 'Company'),
        ('Agronomy', 'Agronomy'),
    )

    title = models.CharField(max_length=240)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='News')
    author = models.CharField(max_length=120)
    date = models.CharField(max_length=80)
    image = models.URLField(max_length=1000)
    excerpt = models.TextField()
    body = models.JSONField(default=list)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def as_payload(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'author': self.author,
            'date': self.date,
            'image': self.image,
            'excerpt': self.excerpt,
            'body': self.body,
            'is_published': self.is_published,
        }


class LeaseApplication(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    )

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    address = models.CharField(max_length=250, blank=True)
    plan = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)