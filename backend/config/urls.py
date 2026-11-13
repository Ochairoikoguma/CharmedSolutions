"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from accounting.views import (home,client_page,sample_remittance_download,remittance_download,saved_remittance_download,)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    # download the report containing fictional sample data
    path("reports/sample/download/",sample_remittance_download,name="sample_remittance_download",),

    #generate,save, and download a selected clients monthly report
    path(
        "reports/clients/<int:client_id>/download/",remittance_download,name="remittance_download",),

        #download an existing PDF from report history
    path("reports/history/<int:report_id>/download/",saved_remittance_download,name="saved_remittance_download",),
]


from accounting.views import (
    home, client_page,
    sample_remittance_download, remittance_download, saved_remittance_download,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("client/", client_page, name="client_page"),
    # ...your existing reports/ routes
]