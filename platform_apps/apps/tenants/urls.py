from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    path("system/bank_xref/", views.system_bank_xref, name="bank_xref"),  # 963 Bank Account Cross Reference
    path("system/hst_parameters/", views.system_hst_parameters, name="hst_parameters"),  # 971 H.S.T. parameter Maintenance
    path("system/reports/list_menu_items/", views.system_list_menu_items, name="list_menu_items"),  # 099 List Menu Items
    path("system/actions/load_invoice_macros/", views.system_load_invoice_macros, name="load_invoice_macros"),  # 962 Load Invoice Macros
    path("system/menu_maintenance/", views.system_menu_maintenance, name="menu_maintenance"),  # 091 Menu Maintenance
    path("system/parameters/", views.system_parameters, name="parameters"),  # 093 Parameters
    path("system/actions/reset_access/", views.system_reset_access, name="reset_access"),  # 095 Reset User’s Access
    path("system/user_maintenance/", views.system_user_maintenance, name="user_maintenance"),  # 092 User Maintenance
]
