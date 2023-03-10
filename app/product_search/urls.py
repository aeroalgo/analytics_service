"""procurement URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from django.contrib.auth.views import LogoutView

from app.product_search.views import SearchProduct, CreateAssembly, ViewTableSkus, UpdateTable, EditTable, Charts, \
    DownloadReport

urlpatterns = [
    path('create/', CreateAssembly.as_view(), name="create_assembly"),
    path('create/<int:id>/', SearchProduct.as_view(), name="product_search"),
    path('view/<int:id>/', ViewTableSkus.as_view(), name="product_view"),
    path('view/<int:id>/update/', UpdateTable.as_view(), name="update_table"),
    path('view/<int:id>/edit/', EditTable.as_view(), name="edit_table"),
    path('view/<int:id>/charts/', Charts.as_view(), name="charts"),
    path('view/<int:id>/download/', DownloadReport.as_view(), name="download")

]
