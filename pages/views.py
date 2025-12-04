from django.shortcuts import render
from django.views.generic import TemplateView


class PrivacyPolicyView(TemplateView):
    template_name = "pages/privacy_policy.html"


class TermsOfUseView(TemplateView):
    template_name = "pages/terms_of_use.html"


class ContactsView(TemplateView):
    template_name = "pages/contacts.html"


class FAQView(TemplateView):
    template_name = "pages/faq.html"


class ShippingView(TemplateView):
    template_name = "pages/shipping.html"


class ReturnsView(TemplateView):
    template_name = "pages/returns.html"
