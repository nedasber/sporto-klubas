from django.contrib import admin
from .models import MembershipPlan, Membership, Training, Reservation, MembershipPurchase

admin.site.register(MembershipPlan)
admin.site.register(Membership)
admin.site.register(Training)
admin.site.register(Reservation)
admin.site.register(MembershipPurchase)