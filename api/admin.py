from django.contrib import admin
from .models import (
    BlogPost,
    ChatMessage,
    ContactMessage,
    FarmerAdvice,
    FarmerAgronomyTask,
    FarmerCoffeePrice,
    FarmerCoffeeSale,
    FarmerFarm,
    FarmerHarvestEstimate,
    FarmerLoanApplication,
    FarmerOpportunity,
    FarmerPortalSettings,
    FarmerProfile,
    FarmerRewardBalance,
    FarmerRewardRule,
    FarmerYieldRecord,
    Lease,
    LeaseApplication,
    NewsletterSubscriber,
    Order,
)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'date', 'is_published', 'updated_at')
    list_filter = ('category', 'is_published')
    search_fields = ('title', 'excerpt', 'author')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    readonly_fields = ('email', 'subscribed_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)


@admin.register(LeaseApplication)
class LeaseApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'plan', 'status', 'created_at')
    list_filter = ('status', 'plan', 'created_at')
    search_fields = ('full_name', 'email', 'phone', 'country', 'plan')
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'product', 'quantity', 'location', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'phone', 'product', 'location')
    readonly_fields = ('created_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('acres', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('created_at',)


@admin.register(FarmerFarm)
class FarmerFarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'farmer', 'district', 'acres', 'tree_count', 'is_active')
    list_filter = ('is_active', 'district')
    search_fields = ('name', 'farmer__user__email', 'farmer__user__first_name', 'district')


@admin.register(FarmerPortalSettings)
class FarmerPortalSettingsAdmin(admin.ModelAdmin):
    list_display = ('interest_rate', 'weather_temperature', 'weather_summary', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not FarmerPortalSettings.objects.exists() and super().has_add_permission(request)


@admin.register(FarmerAdvice)
class FarmerAdviceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'display_order', 'updated_at')
    list_filter = ('category', 'is_published')
    search_fields = ('title', 'summary', 'lead')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('updated_at',)


@admin.register(FarmerCoffeePrice)
class FarmerCoffeePriceAdmin(admin.ModelAdmin):
    list_display = ('grade', 'coffee_type', 'price_per_kg', 'change_30d_percent', 'is_active', 'updated_at')
    list_filter = ('coffee_type', 'is_active')
    search_fields = ('grade',)
    readonly_fields = ('updated_at',)


@admin.register(FarmerYieldRecord)
class FarmerYieldRecordAdmin(admin.ModelAdmin):
    list_display = ('farm', 'season', 'yield_tonnes', 'productivity_kg_per_acre', 'crop_health_score')
    list_filter = ('season',)
    search_fields = ('farm__name', 'farm__farmer__user__email', 'season')


@admin.register(FarmerAgronomyTask)
class FarmerAgronomyTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'farm', 'due_date', 'is_urgent', 'status')
    list_filter = ('status', 'is_urgent', 'due_date')
    search_fields = ('title', 'farm__name', 'farm__farmer__user__email')


@admin.register(FarmerHarvestEstimate)
class FarmerHarvestEstimateAdmin(admin.ModelAdmin):
    list_display = ('farm', 'season', 'coffee_type', 'expected_quantity_kg', 'updated_at')
    list_filter = ('season', 'coffee_type')
    search_fields = ('farm__name', 'farm__farmer__user__email')
    readonly_fields = ('submitted_at', 'updated_at')


@admin.register(FarmerCoffeeSale)
class FarmerCoffeeSaleAdmin(admin.ModelAdmin):
    list_display = ('farm', 'delivery_date', 'grade', 'quantity_kg', 'payment_status')
    list_filter = ('payment_status', 'delivery_date')
    search_fields = ('farm__name', 'farm__farmer__user__email', 'grade', 'buyer')
    readonly_fields = ('submitted_at',)


@admin.register(FarmerOpportunity)
class FarmerOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'opportunity_type', 'closes_at', 'is_published', 'display_order')
    list_filter = ('opportunity_type', 'is_published')
    search_fields = ('title', 'detail', 'location')


@admin.register(FarmerRewardRule)
class FarmerRewardRuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'points_required', 'is_published', 'display_order')
    list_filter = ('is_published',)
    search_fields = ('title', 'description')


@admin.register(FarmerRewardBalance)
class FarmerRewardBalanceAdmin(admin.ModelAdmin):
    list_display = ('farm', 'points', 'quality_score', 'sustainability_score', 'updated_at')
    search_fields = ('farm__name', 'farm__farmer__user__email')
    readonly_fields = ('updated_at',)


@admin.register(FarmerLoanApplication)
class FarmerLoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('farm', 'loan_type', 'amount_requested', 'status', 'submitted_at')
    list_filter = ('loan_type', 'status', 'submitted_at')
    search_fields = ('farm__name', 'farm__farmer__user__email', 'coffee_grade')
    readonly_fields = (
        'farm', 'loan_type', 'amount_requested', 'coffee_grade', 'coffee_price_per_kg',
        'interest_rate', 'repayment_amount', 'repayment_coffee_kg', 'harvest_season',
        'application_date', 'submitted_at',
    )