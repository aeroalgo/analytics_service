from django.shortcuts import render
from django.views.generic import TemplateView

from app.product_search.test_async_task import GeneratePollReport


class SearchProduct(TemplateView):
    template_name = "index.html"

    def get(self, request):
        task = GeneratePollReport()
        task.publish()
        # if request.user.id == id or request.user.has_perm("permissions.users.index"):
        #     profile_data = UserProfile.profile_information(id=id)
        return render(request, self.template_name)

    def post(self, request):
        return render(request, self.template_name)
