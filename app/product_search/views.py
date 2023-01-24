from django.shortcuts import render
from django.views.generic import TemplateView

from app.product_search.generate_polls_reports import GeneratePollReport


class SearchProduct(TemplateView):
    template_name = "index.html"

    def get(self, request):
        # if request.user.id == id or request.user.has_perm("permissions.users.index"):
        #     profile_data = UserProfile.profile_information(id=id)
        return render(request, self.template_name)

    def post(self, request):
        task = GeneratePollReport()
        task.publish()
        return render(request, self.template_name)
