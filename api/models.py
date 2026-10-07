import uuid

from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator


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


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email


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


class FarmerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_profile')
    phone = models.CharField(max_length=50, blank=True)
    auth_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email


class FarmerFarm(models.Model):
    farmer = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name='farms')
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    district = models.CharField(max_length=120)
    acres = models.DecimalField(max_digits=8, decimal_places=2)
    tree_count = models.PositiveIntegerField(default=0)
    coffee_types = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.farmer}'


class FarmerPortalSettings(models.Model):
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10, validators=[MinValueValidator(0), MaxValueValidator(100)])
    weather_temperature = models.DecimalField(max_digits=4, decimal_places=1, default=24)
    weather_summary = models.CharField(max_length=160, default='Partly cloudy')
    weather_guidance = models.TextField(blank=True)
    dashboard_notice = models.CharField(max_length=250, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Farmer portal settings'


class FarmerAdvice(models.Model):
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=80)
    title = models.CharField(max_length=240)
    summary = models.TextField()
    image = models.URLField(max_length=1000, blank=True)
    image_alt = models.CharField(max_length=240, blank=True)
    photo_caption = models.CharField(max_length=240, blank=True)
    lead = models.TextField()
    steps = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True)
    read_time = models.CharField(max_length=40, default='3 min read')
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title


class FarmerCoffeePrice(models.Model):
    COFFEE_TYPES = (('robusta', 'Robusta'), ('arabica', 'Arabica'))

    coffee_type = models.CharField(max_length=20, choices=COFFEE_TYPES)
    grade = models.CharField(max_length=100, unique=True)
    price_per_kg = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    change_30d_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['coffee_type', 'grade']

    def __str__(self):
        return f'{self.grade} — UGX {self.price_per_kg}/kg'


class FarmerYieldRecord(models.Model):
    farm = models.ForeignKey(FarmerFarm, on_delete=models.CASCADE, related_name='yield_records')
    season = models.CharField(max_length=40)
    yield_tonnes = models.DecimalField(max_digits=10, decimal_places=2)
    productivity_kg_per_acre = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    crop_health_score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    tree_survival_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MaxValueValidator(100)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['season']
        constraints = [models.UniqueConstraint(fields=['farm', 'season'], name='unique_farmer_farm_yield_season')]


class FarmerAgronomyTask(models.Model):
    STATUS_CHOICES = (('open', 'Open'), ('completed', 'Completed'))

    farm = models.ForeignKey(FarmerFarm, on_delete=models.CASCADE, related_name='agronomy_tasks')
    title = models.CharField(max_length=240)
    detail = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'due_date', '-is_urgent', 'title']

    def __str__(self):
        return self.title


class FarmerHarvestEstimate(models.Model):
    COFFEE_TYPES = FarmerCoffeePrice.COFFEE_TYPES

    farm = models.ForeignKey(FarmerFarm, on_delete=models.CASCADE, related_name='harvest_estimates')
    season = models.CharField(max_length=40)
    coffee_type = models.CharField(max_length=20, choices=COFFEE_TYPES)
    expected_quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [models.UniqueConstraint(fields=['farm', 'season', 'coffee_type'], name='unique_farmer_harvest_estimate')]


class FarmerCoffeeSale(models.Model):
    PAYMENT_CHOICES = (('pending', 'Pending'), ('paid', 'Paid'))

    farm = models.ForeignKey(FarmerFarm, on_delete=models.CASCADE, related_name='coffee_sales')
    delivery_date = models.DateField()
    grade = models.CharField(max_length=100)
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    buyer = models.CharField(max_length=200, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivery_date', '-id']


class FarmerOpportunity(models.Model):
    TYPES = (
        ('financing', 'Financing'), ('training', 'Training'), ('certification', 'Certification'),
        ('input_discount', 'Input discount'), ('land', 'Land'),
    )

    opportunity_type = models.CharField(max_length=30, choices=TYPES)
    title = models.CharField(max_length=240)
    detail = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    closes_at = models.DateField(null=True, blank=True)
    action_label = models.CharField(max_length=80, default='View details')
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title


class FarmerRewardRule(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    points_required = models.PositiveIntegerField()
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'points_required']

    def __str__(self):
        return self.title


class FarmerRewardBalance(models.Model):
    farm = models.OneToOneField(FarmerFarm, on_delete=models.CASCADE, related_name='reward_balance')
    points = models.PositiveIntegerField(default=0)
    quality_score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    sustainability_score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    updated_at = models.DateTimeField(auto_now=True)


class FarmerLoanApplication(models.Model):
    LOAN_TYPES = (('cash', 'Cash loan'), ('fertilizer', 'Fertilizer loan'))
    STATUS_CHOICES = (('submitted', 'Submitted'), ('reviewing', 'Reviewing'), ('approved', 'Approved'), ('declined', 'Declined'))

    farm = models.ForeignKey(FarmerFarm, on_delete=models.CASCADE, related_name='loan_applications')
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    coffee_grade = models.CharField(max_length=100)
    coffee_price_per_kg = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    repayment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    repayment_coffee_kg = models.DecimalField(max_digits=12, decimal_places=2)
    harvest_season = models.CharField(max_length=40)
    application_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    admin_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']