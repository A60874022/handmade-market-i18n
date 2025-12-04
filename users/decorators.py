from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def master_required(view_func=None):
    """
    Декоратор для проверки, что пользователь - мастер
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_master,
        login_url="login",
        redirect_field_name=None,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


def customer_required(view_func=None):
    """
    Декоратор для проверки, что пользователь - покупатель (не мастер)
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and not u.is_master,
        login_url="login",
        redirect_field_name=None,
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator


from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class MasterRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки, что пользователь - мастер"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_master

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("This page is for masters only.")
        return super().handle_no_permission()


class CustomerRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки, что пользователь - покупатель"""

    def test_func(self):
        return self.request.user.is_authenticated and not self.request.user.is_master

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("This page is for customers only.")
        return super().handle_no_permission()
