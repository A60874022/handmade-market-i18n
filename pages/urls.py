from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("privacy-policy/", views.PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("terms-of-use/", views.TermsOfUseView.as_view(), name="terms_of_use"),
    path("contacts/", views.ContactsView.as_view(), name="contacts"),
    path("faq/", views.FAQView.as_view(), name="faq"),
    path("shipping-info/", views.ShippingView.as_view(), name="shipping"),
    path("return-policy/", views.ReturnsView.as_view(), name="returns"),
]
