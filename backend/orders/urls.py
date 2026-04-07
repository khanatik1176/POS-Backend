from django.urls import path
from .views import (
    MasterDataView,
    ReferenceSearchView,
    OrderCreateView,
    OrderListView,
    VerifyOrderView,
    CompleteOrderView,
)

urlpatterns = [
    path("master-data/", MasterDataView.as_view(), name="master-data"),
    path("references/search/", ReferenceSearchView.as_view(), name="reference-search"),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/create/", OrderCreateView.as_view(), name="order-create"),
    path("orders/<int:order_id>/verify/", VerifyOrderView.as_view(), name="order-verify"),
    path("orders/<int:order_id>/complete/", CompleteOrderView.as_view(), name="order-complete"),
]